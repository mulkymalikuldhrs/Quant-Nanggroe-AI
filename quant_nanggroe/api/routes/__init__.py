"""API Routes — Package initialization."""
from quant_nanggroe.api.routes import (
    agents,
    agentic,
    analytics,
    backtest,
    colony,
    council,
    credentials,
    debate,
    ecosystem,
    market,
    memory,
    monitor,
    options,
    personas,
    portfolio,
    rl,
    strategy,
    trading,
    ws,
    wiring_compat,
)

# WhatsApp gateway routes (optional - requires bridge service)
try:
    from quant_nanggroe.api.routes import whatsapp
except ImportError:
    whatsapp = None  # type: ignore[assignment]

__all__ = [
    "market", "trading", "agents", "backtest", "portfolio", "ws",
    "memory", "ecosystem", "colony", "council", "debate", "monitor",
    "options", "personas", "rl", "analytics", "agentic", "whatsapp",
    "wiring_compat",
]
