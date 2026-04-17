"""Paper-trading (dry-run) execution.

Mirrors the live interface exactly — strategies shouldn't know whether they're
paper or live. Fills use the exchange's last price with simulator-style slippage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from ..exchanges.base import Order, OrderSide, OrderType
from ..utils.logger import logger


@dataclass
class PaperAccount:
    cash_krw: Decimal = Decimal("10000000")
    positions: dict[str, Decimal] = field(default_factory=dict)  # symbol -> amount
    avg_entry: dict[str, Decimal] = field(default_factory=dict)
    trade_log: list[dict] = field(default_factory=list)


class PaperExecutor:
    def __init__(self, account: PaperAccount | None = None, fee_rate: Decimal = Decimal("0.0005")):
        self.account = account or PaperAccount()
        self.fee_rate = fee_rate
        self._order_id_seq = 0

    def _next_id(self) -> str:
        self._order_id_seq += 1
        return f"paper-{self._order_id_seq}"

    async def create_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        amount: Decimal,
        reference_price: Decimal,
        strategy: str = "",
        reasoning: str = "",
    ) -> Order:
        """Paper fill at reference price + 5bps slippage."""
        slip = Decimal("0.0005")
        fill_price = (
            reference_price * (Decimal("1") + slip)
            if side == "buy"
            else reference_price * (Decimal("1") - slip)
        )
        if side == "buy":
            notional = amount  # market buy: amount is KRW
            if notional > self.account.cash_krw:
                raise ValueError(f"Paper: insufficient cash ({self.account.cash_krw} KRW)")
            qty = notional / fill_price
            fee = notional * self.fee_rate
            self.account.cash_krw -= notional + fee
            prev_qty = self.account.positions.get(symbol, Decimal("0"))
            prev_avg = self.account.avg_entry.get(symbol, Decimal("0"))
            new_qty = prev_qty + qty
            new_avg = (prev_qty * prev_avg + qty * fill_price) / new_qty if new_qty > 0 else Decimal("0")
            self.account.positions[symbol] = new_qty
            self.account.avg_entry[symbol] = new_avg
        else:
            qty = amount
            held = self.account.positions.get(symbol, Decimal("0"))
            if qty > held:
                raise ValueError(f"Paper: insufficient {symbol} ({held})")
            notional = qty * fill_price
            fee = notional * self.fee_rate
            self.account.cash_krw += notional - fee
            self.account.positions[symbol] = held - qty
            if self.account.positions[symbol] == 0:
                self.account.avg_entry.pop(symbol, None)

        order_id = self._next_id()
        order = Order(
            id=order_id,
            symbol=symbol,
            side=side,
            type=order_type,
            price=fill_price,
            amount=qty,
            filled=qty,
            status="filled",
            timestamp=int(__import__("time").time() * 1000),
        )
        self.account.trade_log.append(
            {
                "order_id": order_id,
                "symbol": symbol,
                "side": side,
                "qty": str(qty),
                "price": str(fill_price),
                "strategy": strategy,
                "reasoning": reasoning,
            }
        )
        logger.info(
            f"[PAPER] {side.upper()} {symbol} qty={qty:.8f} @ {fill_price:.2f} "
            f"({strategy}: {reasoning[:80]})"
        )
        return order

    def equity_krw(self, marks: dict[str, Decimal]) -> Decimal:
        positions_value = sum(
            qty * marks.get(sym, self.account.avg_entry.get(sym, Decimal("0")))
            for sym, qty in self.account.positions.items()
        )
        return self.account.cash_krw + positions_value
