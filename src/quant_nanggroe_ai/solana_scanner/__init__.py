"""
SolSniperX Scanner Module
Solana memecoin scanning, trading, and AI analysis services.
Merged from SolSniperX v3.3.0 (Ultimate Intelligence Upgrade) branch.
"""

from quant_nanggroe_ai.solana_scanner.config import (
    DEXSCREENER_BASE_URL,
    BIRDEYE_BASE_URL,
    LLM7_BASE_URL,
    JUPITER_API_BASE_URL,
    SOLANA_RPC_URL,
    SOLANA_WS_URL,
)

from quant_nanggroe_ai.solana_scanner.data_fetcher import DataFetcherService, data_fetcher_service
from quant_nanggroe_ai.solana_scanner.mempool_monitor import MempoolMonitorService, mempool_monitor_service
from quant_nanggroe_ai.solana_scanner.trading_service import TradingService, trading_service
from quant_nanggroe_ai.solana_scanner.wallet_service import WalletService, wallet_service
from quant_nanggroe_ai.solana_scanner.ai_analysis import AIAnalysisService, ai_analysis_service
from quant_nanggroe_ai.solana_scanner.auto_trader import AutoTraderService, auto_trader_service
from quant_nanggroe_ai.solana_scanner.db import init_db, record_trade, save_position, remove_position

__all__ = [
    "DEXSCREENER_BASE_URL",
    "BIRDEYE_BASE_URL", 
    "LLM7_BASE_URL",
    "JUPITER_API_BASE_URL",
    "SOLANA_RPC_URL",
    "SOLANA_WS_URL",
    "DataFetcherService",
    "data_fetcher_service",
    "MempoolMonitorService",
    "mempool_monitor_service",
    "TradingService",
    "trading_service",
    "WalletService",
    "wallet_service",
    "AIAnalysisService",
    "ai_analysis_service",
    "AutoTraderService",
    "auto_trader_service",
    "init_db",
    "record_trade",
    "save_position",
    "remove_position",
]
