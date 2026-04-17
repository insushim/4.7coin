"""initial schema + timescaledb hypertables

Revision ID: 0001
Revises:
Create Date: 2026-04-17

TimescaleDB conversion is *best-effort*. If the extension is missing the
migration still succeeds (plain Postgres). A later migration or the
`psql` equivalent can be applied manually on TSDB-enabled instances.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ohlcv",
        sa.Column("time", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("exchange", sa.String(32), primary_key=True),
        sa.Column("symbol", sa.String(32), primary_key=True),
        sa.Column("timeframe", sa.String(8), primary_key=True),
        sa.Column("open", sa.Numeric(24, 8)),
        sa.Column("high", sa.Numeric(24, 8)),
        sa.Column("low", sa.Numeric(24, 8)),
        sa.Column("close", sa.Numeric(24, 8)),
        sa.Column("volume", sa.Numeric(24, 8)),
    )
    op.create_index("ix_ohlcv_symbol_tf_time", "ohlcv", ["symbol", "timeframe", "time"])

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("exchange_order_id", sa.String(64), index=True),
        sa.Column("exchange", sa.String(32)),
        sa.Column("symbol", sa.String(32), index=True),
        sa.Column("side", sa.String(8)),
        sa.Column("order_type", sa.String(16)),
        sa.Column("amount", sa.Numeric(24, 8)),
        sa.Column("price", sa.Numeric(24, 8), nullable=True),
        sa.Column("filled", sa.Numeric(24, 8), server_default="0"),
        sa.Column("status", sa.String(16)),
        sa.Column("strategy", sa.String(64)),
        sa.Column("reasoning", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "positions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(32), index=True),
        sa.Column("amount", sa.Numeric(24, 8)),
        sa.Column("avg_entry_price", sa.Numeric(24, 8)),
        sa.Column("strategy", sa.String(64)),
        sa.Column("opened_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("realized_pnl", sa.Numeric(24, 8), server_default="0"),
    )

    op.create_table(
        "equity_snapshots",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("time", sa.DateTime(timezone=True), server_default=sa.text("now()"), index=True),
        sa.Column("total_krw", sa.Numeric(24, 8)),
        sa.Column("cash_krw", sa.Numeric(24, 8)),
        sa.Column("positions_value_krw", sa.Numeric(24, 8)),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("time", sa.DateTime(timezone=True), server_default=sa.text("now()"), index=True),
        sa.Column("event", sa.String(64), index=True),
        sa.Column("actor", sa.String(64)),
        sa.Column("detail", sa.Text),
    )

    # TimescaleDB is optional — wrap in DO block so plain Postgres also passes
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'timescaledb') THEN
                CREATE EXTENSION IF NOT EXISTS timescaledb;
                PERFORM create_hypertable('ohlcv', 'time',
                                          chunk_time_interval => INTERVAL '7 days',
                                          if_not_exists => TRUE);
                PERFORM add_retention_policy('ohlcv', INTERVAL '10 years', if_not_exists => TRUE);
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("equity_snapshots")
    op.drop_table("positions")
    op.drop_table("orders")
    op.drop_index("ix_ohlcv_symbol_tf_time", table_name="ohlcv")
    op.drop_table("ohlcv")
