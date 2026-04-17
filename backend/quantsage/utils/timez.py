"""KST-aware timestamp helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timezone

KST = timezone(offset=__import__("datetime").timedelta(hours=9), name="Asia/Seoul")


def now_kst() -> datetime:
    return datetime.now(tz=KST)


def now_utc() -> datetime:
    return datetime.now(tz=UTC)


def to_kst(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(KST)
