"""Domain exceptions.

Exchange-specific errors are translated into these standard types so strategies
and risk layers stay exchange-agnostic.
"""


class QuantSageError(Exception):
    """Base exception."""


class ConfigError(QuantSageError):
    """Misconfiguration."""


class ExchangeError(QuantSageError):
    """Generic exchange failure."""


class OrderRejectedError(ExchangeError):
    """Order rejected by the exchange."""


class InsufficientFundsError(ExchangeError):
    """Insufficient KRW / crypto balance."""


class RateLimitError(ExchangeError):
    """Rate-limit hit; caller should back off."""


class MarketDataError(QuantSageError):
    """WebSocket / REST data feed failure."""


class RiskBlockedError(QuantSageError):
    """A risk layer blocked the order."""

    def __init__(self, layer: str, reason: str):
        self.layer = layer
        self.reason = reason
        super().__init__(f"Risk layer '{layer}' blocked: {reason}")


class KillSwitchActive(QuantSageError):
    """Kill-switch is engaged; no new orders."""


class BacktestError(QuantSageError):
    """Backtest engine failure."""
