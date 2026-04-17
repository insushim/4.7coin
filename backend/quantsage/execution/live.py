"""Live executor — thin, defensive wrapper around the exchange adapter.

Guarantees:
  - Refuses to send an order unless `settings.is_live` is true
  - Routes every proposal through the 8-layer risk aggregator before it touches
    the exchange
  - Splits oversized orders into TWAP slices (configurable count/interval)
  - Persists every submission + fill to `orders` (DB) and mirrors into the
    paper ledger so the dashboard shows a unified view
  - Reconciles remote position state every `reconcile_interval`; any drift
    triggers an alert but NEVER silent correction
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select

from ..config import settings
from ..db.models import OrderRecord
from ..db.session import get_session
from ..exceptions import KillSwitchActive, RiskBlockedError
from ..exchanges.base import AbstractExchange, Order, OrderSide
from ..notifications.telegram import telegram
from ..risk.aggregator import OrderProposal, RiskAggregator, RiskContext, RiskDecision
from ..risk.kill_switch import kill_switch
from ..utils.logger import logger
from .dry_run import PaperExecutor


@dataclass
class ExecutionConfig:
    twap_threshold_krw: Decimal = Decimal("3000000")  # slice anything above 3M KRW
    twap_slices: int = 5
    twap_interval_seconds: int = 60
    reconcile_interval_seconds: int = 300


@dataclass
class ExecutionResult:
    accepted: bool
    orders: list[Order]
    risk_decision: RiskDecision
    reason: str


class LiveExecutor:
    def __init__(
        self,
        exchange: AbstractExchange,
        risk: RiskAggregator,
        paper_mirror: PaperExecutor | None = None,
        config: ExecutionConfig | None = None,
    ):
        self.exchange = exchange
        self.risk = risk
        self.paper_mirror = paper_mirror
        self.cfg = config or ExecutionConfig()
        self._reconcile_task: asyncio.Task | None = None

    async def submit(
        self,
        proposal: OrderProposal,
        build_context: Callable[[], Awaitable[RiskContext]],
        reference_price: Decimal,
    ) -> ExecutionResult:
        if kill_switch.is_active:
            raise KillSwitchActive(kill_switch.message)
        if not settings.is_live:
            return ExecutionResult(
                accepted=False,
                orders=[],
                risk_decision=None,  # type: ignore[arg-type]
                reason="TRADING_MODE or ENABLE_LIVE_TRADING disables live",
            )

        ctx = await build_context()
        decision = await self.risk.evaluate(proposal, ctx)
        if not decision.allowed:
            logger.warning(
                f"Live blocked at {decision.blocked_layer}: {decision.reason}"
            )
            return ExecutionResult(False, [], decision, decision.reason)

        notional = decision.sizing.notional_krw  # type: ignore[union-attr]
        side: OrderSide = "buy" if proposal.direction == "BUY" else "sell"
        orders = await self._route_order(
            symbol=proposal.symbol,
            side=side,
            notional_krw=notional,
            reference_price=reference_price,
            strategy=proposal.strategy,
            reasoning=proposal.reasoning,
        )
        # mirror to paper ledger for unified dashboard
        if self.paper_mirror and orders:
            try:
                amount = (
                    notional
                    if side == "buy"
                    else sum((o.filled for o in orders), Decimal("0"))
                )
                await self.paper_mirror.create_order(
                    symbol=proposal.symbol,
                    side=side,
                    order_type="market",
                    amount=amount,
                    reference_price=reference_price,
                    strategy=proposal.strategy,
                    reasoning=f"[LIVE-MIRROR] {proposal.reasoning}",
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"Paper mirror failed (non-fatal): {exc}")

        return ExecutionResult(True, orders, decision, "submitted")

    async def _route_order(
        self,
        *,
        symbol: str,
        side: OrderSide,
        notional_krw: Decimal,
        reference_price: Decimal,
        strategy: str,
        reasoning: str,
    ) -> list[Order]:
        """TWAP-slice large orders; otherwise single market fill."""
        if notional_krw <= self.cfg.twap_threshold_krw:
            o = await self._single_order(symbol, side, notional_krw, reference_price, strategy, reasoning)
            return [o] if o else []
        slice_notional = notional_krw / self.cfg.twap_slices
        placed: list[Order] = []
        for i in range(self.cfg.twap_slices):
            o = await self._single_order(
                symbol, side, slice_notional, reference_price, strategy,
                f"{reasoning} [TWAP {i+1}/{self.cfg.twap_slices}]",
            )
            if o:
                placed.append(o)
            if i < self.cfg.twap_slices - 1:
                await asyncio.sleep(self.cfg.twap_interval_seconds)
            if kill_switch.is_active:
                logger.warning("Kill-switch fired mid-TWAP; aborting remaining slices")
                break
        return placed

    async def _single_order(
        self,
        symbol: str,
        side: OrderSide,
        notional_krw: Decimal,
        reference_price: Decimal,
        strategy: str,
        reasoning: str,
    ) -> Order | None:
        try:
            if side == "buy":
                order = await self.exchange.create_order(
                    symbol=symbol,
                    side="buy",
                    order_type="market",
                    amount=notional_krw,  # upbit market-buy takes KRW
                )
            else:
                # need qty — convert by reference_price, round down to 8dp
                qty = (notional_krw / reference_price).quantize(Decimal("0.00000001"))
                order = await self.exchange.create_order(
                    symbol=symbol,
                    side="sell",
                    order_type="market",
                    amount=qty,
                )
        except RiskBlockedError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception(f"Live order failed {symbol} {side}: {exc}")
            await telegram.send(f"⚠️ Live order FAILED {symbol} {side}: {exc}")
            return None

        await self._persist(order, strategy, reasoning)
        await telegram.send(
            f"✅ LIVE {side.upper()} {symbol} "
            f"amount={order.amount} price≈{reference_price} "
            f"id={order.id[:8]}...\n_{strategy}: {reasoning[:120]}_"
        )
        return order

    @staticmethod
    async def _persist(order: Order, strategy: str, reasoning: str) -> None:
        async with get_session() as s:
            rec = OrderRecord(
                exchange_order_id=order.id,
                exchange="upbit",
                symbol=order.symbol,
                side=order.side,
                order_type=order.type,
                amount=order.amount,
                price=order.price,
                filled=order.filled,
                status=order.status,
                strategy=strategy,
                reasoning=reasoning[:2000],
            )
            s.add(rec)

    async def reconcile(self) -> dict:
        """Compare local open orders vs exchange; report drift only (no auto-fix)."""
        remote = {o.id for o in await self.exchange.fetch_open_orders()}
        async with get_session() as s:
            q = select(OrderRecord).where(OrderRecord.status.in_(["wait", "partial"]))
            local = {r.exchange_order_id for r in (await s.execute(q)).scalars().all()}
        missing_remote = local - remote  # we thought open, exchange doesn't
        missing_local = remote - local   # exchange has orders we didn't log
        report = {
            "time": datetime.now(UTC).isoformat(),
            "drift": bool(missing_remote or missing_local),
            "missing_remote": sorted(missing_remote),
            "missing_local": sorted(missing_local),
        }
        if report["drift"]:
            await telegram.send(
                f"⚠️ Position reconcile drift: "
                f"missing_remote={len(missing_remote)}, missing_local={len(missing_local)}"
            )
            logger.warning(f"Reconcile drift: {report}")
        return report

    async def start_reconciler(self) -> None:
        async def _loop() -> None:
            while not kill_switch.is_active:
                try:
                    await self.reconcile()
                except Exception as exc:  # noqa: BLE001
                    logger.exception(f"reconcile error: {exc}")
                await asyncio.sleep(self.cfg.reconcile_interval_seconds)

        if self._reconcile_task is None or self._reconcile_task.done():
            self._reconcile_task = asyncio.create_task(_loop())

    async def stop_reconciler(self) -> None:
        if self._reconcile_task and not self._reconcile_task.done():
            self._reconcile_task.cancel()
            try:
                await self._reconcile_task
            except asyncio.CancelledError:
                pass
