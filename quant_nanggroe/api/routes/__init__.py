"""API Routes — Package initialization."""

from quant_nanggroe.api.routes import market, trading, agents, backtest, portfolio, ws, memory, ecosystem, colony, monitor

# WhatsApp gateway routes (optional - requires bridge service)
try:
    from quant_nanggroe.api.routes import whatsapp
except ImportError:
    whatsapp = None  # type: ignore[assignment]

__all__ = ["market", "trading", "agents", "backtest", "portfolio", "ws", "memory", "ecosystem", "colony", "monitor", "whatsapp"]
