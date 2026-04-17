"""Export trade log to a tax-ready CSV (Korean 2027 virtual-asset tax).

Columns: datetime (KST), exchange, symbol, side, quantity, price_krw,
notional_krw, fee_krw, order_id. Aggregated per calendar year.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import asyncio

from sqlalchemy import select

from quantsage.db.models import OrderRecord
from quantsage.db.session import get_session
from quantsage.utils.timez import to_kst


async def export(year: int, outfile: Path) -> None:
    async with get_session() as s:
        q = select(OrderRecord).where(
            OrderRecord.created_at >= __import__("datetime").datetime(year, 1, 1),
            OrderRecord.created_at < __import__("datetime").datetime(year + 1, 1, 1),
        )
        rows = (await s.execute(q)).scalars().all()
    outfile.parent.mkdir(parents=True, exist_ok=True)
    with outfile.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "datetime_kst",
                "exchange",
                "symbol",
                "side",
                "quantity",
                "price_krw",
                "notional_krw",
                "status",
                "order_id",
                "strategy",
            ]
        )
        for r in rows:
            notional = (r.price or 0) * r.amount
            w.writerow(
                [
                    to_kst(r.created_at).isoformat(),
                    r.exchange,
                    r.symbol,
                    r.side,
                    str(r.amount),
                    str(r.price or ""),
                    str(notional),
                    r.status,
                    r.exchange_order_id,
                    r.strategy,
                ]
            )
    print(f"Wrote {len(rows)} rows to {outfile}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2026)
    ap.add_argument("--out", default="data/reports/trades_{year}.csv")
    args = ap.parse_args()
    path = Path(args.out.format(year=args.year))
    asyncio.run(export(args.year, path))


if __name__ == "__main__":
    main()
