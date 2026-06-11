"""Solana/Jupiter V6 Exchange Integration.

Provides Solana wallet management, Jupiter V6 swap execution,
mempool monitoring, token safety checking, and a broker adapter
implementing the unified exchange interface.

Modules
-------
wallet
    Solana wallet service — keypair management, SOL/SPL balances.
jupiter
    Jupiter V6 swap integration — quotes, execution, price impact.
mempool
    Solana mempool monitor — pending transactions, new token detection.
rugcheck
    Token safety checker — mint/freeze authority, LP burn, holder concentration.
broker
    Solana broker adapter implementing :class:`~quant_nanggroe_ai.exchange.base.ExchangeInterface`.

Usage
-----
    from quant_nanggroe_ai.exchange.solana import SolanaWallet, JupiterV6Client, SolanaBroker

    wallet = SolanaWallet(private_key_bs58="...")
    balance = await wallet.get_sol_balance()

    jupiter = JupiterV6Client(rpc_url="https://api.mainnet-beta.solana.com")
    quote = await jupiter.get_quote(
        input_mint="So11111111111111111111111111111111111111112",
        output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        amount=1_000_000,
        slippage_bps=50,
    )
"""

from quant_nanggroe_ai.exchange.solana.wallet import SolanaWallet, TokenAccountInfo
from quant_nanggroe_ai.exchange.solana.jupiter import JupiterV6Client, JupiterQuote, JupiterSwapResult
from quant_nanggroe_ai.exchange.solana.mempool import SolanaMempoolMonitor, MempoolEvent, MempoolEventType
from quant_nanggroe_ai.exchange.solana.rugcheck import RugChecker, TokenSafetyReport, SafetyVerdict
from quant_nanggroe_ai.exchange.solana.broker import SolanaBroker

__all__ = [
    # Wallet
    "SolanaWallet",
    "TokenAccountInfo",
    # Jupiter
    "JupiterV6Client",
    "JupiterQuote",
    "JupiterSwapResult",
    # Mempool
    "SolanaMempoolMonitor",
    "MempoolEvent",
    "MempoolEventType",
    # Rugcheck
    "RugChecker",
    "TokenSafetyReport",
    "SafetyVerdict",
    # Broker
    "SolanaBroker",
]
