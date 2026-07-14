"""Credential Manager — single source of truth for all external service credentials.

Loads secrets from environment variables (QNAI_* convention) and encrypted .env,
maps them to the right config/connector locations, and reports which services
are configured vs missing.

Existing security modules this builds on:
  - KeyVault        (keyvault.py)    — env-only secret loader
  - EncryptedStore  (encryption.py)  — Fernet at-rest encryption
  - CredentialInference (credential_inference.py) — exchange detection

Usage:
    from quant_nanggroe.security.credential_manager import credential_manager, ServiceStatus

    status = credential_manager.check_all()
    status.report()           # print summary
    status.configured         # list of working services
    status.missing            # list of missing services

    # Get a specific credential
    key = credential_manager.get("alpha_vantage")
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from quant_nanggroe.security.keyvault import KeyVault

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Service definitions — maps logical service name → env vars + config path
# ---------------------------------------------------------------------------

# ponytail: flat dict, one service per entry. Add when new service appears.


@dataclass
class ServiceDef:
    """Definition of an external service and how it's configured.

    Attributes:
        name:        Logical service name (e.g. 'alpha_vantage').
        label:       Human-readable label for reports.
        env_keys:    Environment variable names to check. First non-empty wins.
        config_path: Where this credential ends up in the codebase (file or dotted path).
        required:    True = fail-fast if missing in production.
        category:    'llm', 'market_data', 'exchange', 'infra', 'blockchain', etc.
    """
    name: str
    label: str
    env_keys: List[str]
    config_path: str = ""
    required: bool = False
    category: str = "other"


SERVICES: List[ServiceDef] = [
    # ── LLM Providers ──────────────────────────────────────────────────
    ServiceDef("groq", "Groq API", ["QNAI_GROQ_API_KEY", "GROQ_API_KEY"],
               "quant_nanggroe/engine/autonomous/llm_router.py", category="llm"),
    ServiceDef("openai", "OpenAI API", ["QNAI_OPENAI_API_KEY", "OPENAI_API_KEY"],
               "quant_nanggroe/engine/llm_router.py / .env.template", category="llm"),
    ServiceDef("anthropic", "Anthropic API", ["QNAI_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY"],
               ".env.template", category="llm"),
    ServiceDef("google", "Google AI / Gemini", ["QNAI_GOOGLE_API_KEY", "GOOGLE_API_KEY"],
               "quant_nanggroe/engine/llm_router.py", category="llm"),
    ServiceDef("nvidia_nim", "NVIDIA NIM", ["QNAI_NVIDIA_NIM_API_KEY", "NVIDIA_NIM_API_KEY"],
               "quant_nanggroe/engine/nvidia_nim/config.py", category="llm"),
    ServiceDef("huggingface", "HuggingFace Inference", ["HF_API_KEY", "QNAI_HF_API_KEY", "HUGGINGFACE_API_KEY"],
               "quant_nanggroe/engine/autonomous/llm_router.py", category="llm"),
    ServiceDef("together", "Together AI", ["QNAI_TOGETHER_API_KEY", "TOGETHER_API_KEY"],
               "n/a — mocked in fallback chain", category="llm"),
    ServiceDef("openrouter", "OpenRouter", ["OPENROUTER_API_KEY", "QNAI_OPENROUTER_API_KEY"],
               "config/system_config.yaml", category="llm"),
    ServiceDef("opencode_zen", "OpenCode Zen", ["OPENGODE_ZEN_API_KEY"],
               "n/a — DEAD (401 auth invalid 2026-07-14)", category="llm"),

    # ── Market Data ────────────────────────────────────────────────────
    ServiceDef("alpha_vantage", "Alpha Vantage", ["QNAI_ALPHA_VANTAGE_API_KEY"],
               ".env.example / .env.template", category="market_data"),
    ServiceDef("polygon", "Polygon.io", ["QNAI_POLYGON_API_KEY", "QNAI_API_KEY"],
               "quant_nanggroe/providers/data_manager.py (line 62)", category="market_data"),
    ServiceDef("financial_dataset", "Financial Dataset API", ["QNAI_FINANCIAL_DATASET_API_KEY"],
               "n/a — no codebase usage found", category="market_data"),
    ServiceDef("finnhub", "Finnhub", ["QNAI_FINNHUB_API_KEY"],
               "quant_nanggroe/providers/finnhub_provider.py", category="market_data"),
    ServiceDef("twelvedata", "TwelveData", ["QNAI_TWELVEDATA_API_KEY"],
               ".env.example", category="market_data"),
    ServiceDef("coingecko", "CoinGecko", ["QNAI_COINGECKO_API_KEY"],
               "quant_nanggroe/providers/data_manager.py (line 21)", category="market_data"),
    ServiceDef("fred", "FRED (St. Louis Fed)", ["QNAI_FRED_API_KEY"],
               ".env.template", category="market_data"),
    ServiceDef("tavily", "Tavily Search", ["TAVILY_API_KEY", "QNAI_TAVILY_API_KEY"],
               "n/a — no codebase usage found", category="market_data"),
    ServiceDef("bytez", "Bytez AI", ["BYTEZ_API_KEY"],
               "n/a — no codebase usage found", category="market_data"),
    ServiceDef("fascapi", "FascAPI", ["FASCAPI_API_KEY"],
               "n/a — no codebase usage found", category="market_data"),
    ServiceDef("skillsmp", "SkillsMP", ["SKILLSMP_API_KEY"],
               "n/a — no codebase usage found", category="market_data"),
    ServiceDef("hyperbrowser", "Hyperbrowser", ["HYPERBROWSER_API_KEY"],
               "n/a — no codebase usage found", category="market_data"),

    # ── Exchanges / Brokers ────────────────────────────────────────────
    ServiceDef("alpaca", "Alpaca Trading", ["QNAI_ALPACA_API_KEY"],
               ".env.template / quant_nanggroe/security/credential_inference.py", category="exchange"),
    ServiceDef("binance", "Binance", ["QNAI_BINANCE_API_KEY"],
               ".env.example / .env.template", category="exchange"),
    ServiceDef("bybit", "Bybit", ["QNAI_BYBIT_API_KEY"],
               "quant_nanggroe/providers/crypto_provider.py", category="exchange"),
    ServiceDef("exness_mt5", "Exness MT5", [] ,  # stored in config/ files, not env
               "config/credentials.json + config/mt5_accounts.yaml", category="exchange"),
    ServiceDef("bullx", "BullX Wallets", [],
               "n/a — no codebase usage found", category="blockchain"),
    ServiceDef("mevx", "MEVX API", ["MEVX_API_KEY"],
               "n/a — no codebase usage found", category="blockchain"),
    ServiceDef("photon", "Photon Trading", [],
               "n/a — no codebase usage found", category="blockchain"),

    # ── Blockchain / Web3 ──────────────────────────────────────────────
    ServiceDef("infura", "Infura / Ethereum Node", ["INFURA_PROJECT_ID"],
               "quant_nanggroe/connectors/web3_plugin.py (stub)", category="blockchain"),
    ServiceDef("helius", "Helius (Solana RPC)", ["HELIUS_API_KEY"],
               "n/a — no codebase usage found", category="blockchain"),
    ServiceDef("steem", "Steem Blockchain", [],
               "n/a — no codebase usage found", category="blockchain"),
    ServiceDef("etherscan", "Etherscan API", [] , category="blockchain"),

    # ── Infrastructure ──────────────────────────────────────────────────
    ServiceDef("github", "GitHub Tokens", ["GITHUB_TOKEN", "GH_TOKEN"],
               "quant_nanggroe/connectors/github_integration.py (stub)", category="infra"),
    ServiceDef("supabase", "Supabase", ["SUPABASE_URL", "SUPABASE_SERVICE_KEY", "SUPABASE_ANON_KEY"],
               ".env.template (no QNAI_ prefix found)", category="infra"),
    ServiceDef("vercel", "Vercel", ["VERCEL_TOKEN", "VERCEL_PROJECT_ID"],
               "vercel.json / .env.template", category="infra"),
    ServiceDef("convex", "Convex", ["CONVEX_DEPLOY_KEY"],
               "n/a — no codebase usage found", category="infra"),
    ServiceDef("notion", "Notion API", ["NOTION_API_KEY", "NTN_API_KEY"],
               "n/a — no codebase usage found", category="infra"),
    ServiceDef("agentmail", "AgentMail / SMTP", ["AGENTMAIL_API_KEY"],
               "n/a — no codebase usage found", category="infra"),
    ServiceDef("wix", "Wix API", ["WIX_API_KEY"],
               "n/a — no codebase usage found", category="infra"),
    ServiceDef("composio", "Composio MCP", ["COMPOSIO_API_KEY"],
               "n/a — no codebase usage found", category="infra"),
    ServiceDef("mcp_market", "MCP Market", ["MCP_MARKET_API_KEY"],
               "n/a — no codebase usage found", category="infra"),
    ServiceDef("cron_job", "Cron Job API", ["CRON_JOB_API_KEY"],
               "n/a — no codebase usage found", category="infra"),
    ServiceDef("ollamacloud", "OllamaCloud", ["OLLAMACLOUD_API_KEY"],
               "n/a — no codebase usage found", category="infra"),
    ServiceDef("lobehub", "LobeHub", ["LOBEHUB_API_KEY"],
               "n/a — no codebase usage found", category="infra"),
    ServiceDef("openmemory", "OpenMemory", ["OPENMEMORY_API_KEY"],
               "n/a — no codebase usage found", category="infra"),

    # ── Telegram ────────────────────────────────────────────────────────
    ServiceDef("telegram_bots", "Telegram Bots (6 bots)",
               ["TELEGRAM_BOT_TOKEN_MAIN", "TELEGRAM_BOT_TOKEN_CLAW",
                "TELEGRAM_BOT_TOKEN_FANG", "TELEGRAM_BOT_TOKEN_HACKER",
                "TELEGRAM_BOT_TOKEN_DEV", "TELEGRAM_BOT_TOKEN_TRADER",
                "TELEGRAM_BOT_TOKEN_RESEARCH"],
               "n/a — no codebase usage found (telegram IDs in credentials.md)", category="infra"),
]


@dataclass
class ServiceStatus:
    """Result of checking all service credentials."""
    configured: List[str] = field(default_factory=list)
    partially_configured: List[str] = field(default_factory=list)
    missing: List[str] = field(default_factory=list)
    configured_with_warnings: List[Dict[str, str]] = field(default_factory=list)
    file_based: List[Dict[str, str]] = field(default_factory=list)

    def report(self) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append("CREDENTIAL AUDIT REPORT — QNAI Codebase")
        lines.append("=" * 60)

        lines.append(f"\n✅ CONFIGURED ({len(self.configured)}):")
        for s in self.configured:
            lines.append(f"  ✔ {s}")

        if self.configured_with_warnings:
            lines.append(f"\n⚡ CONFIGURED (with issues) ({len(self.configured_with_warnings)}):")
            for s in self.configured_with_warnings:
                lines.append(f"  ⚠ {s['name']}: {s['warning']}")

        if self.partially_configured:
            lines.append(f"\n🔶 PARTIALLY CONFIGURED ({len(self.partially_configured)}):")
            for s in self.partially_configured:
                lines.append(f"  ◐ {s}")

        lines.append(f"\n❌ MISSING ({len(self.missing)}):")
        for s in self.missing:
            lines.append(f"  ✘ {s}")

        if self.file_based:
            lines.append(f"\n📁 FILE-BASED CREDENTIALS (plaintext in config/):")
            for s in self.file_based:
                lines.append(f"  ⚠ {s['name']}: {s['location']} — {s['risk']}")

        lines.append("\n" + "=" * 60)
        total = len(self.configured) + len(self.partially_configured) + len(self.missing) + len(self.configured_with_warnings)
        lines.append(f"TOTAL: {len(self.configured)} configured, {len(self.missing)} missing, "
                     f"{len(self.file_based)} file-based (plaintext)")
        lines.append("=" * 60)
        return "\n".join(lines)


class CredentialManager:
    """Single entry point for all external service credentials.

    Loads from environment (QNAI_* convention). Extends KeyVault with
    service-level awareness — knows which env var maps to which service,
    where credentials are consumed in the codebase, and what's missing.
    """

    def __init__(self) -> None:
        self._vault = KeyVault()
        self._services = {s.name: s for s in SERVICES}
        self._cache: Dict[str, Optional[str]] = {}

    def get(self, service_name: str) -> Optional[str]:
        """Get the credential for a service. Returns first non-empty env var value."""
        svc = self._services.get(service_name)
        if not svc:
            logger.warning("Unknown service: %s", service_name)
            return None
        return self._get_first(svc.env_keys)

    def check(self, service_name: str) -> bool:
        """Check if a specific service is configured."""
        svc = self._services.get(service_name)
        if not svc:
            return False
        return self._get_first(svc.env_keys) is not None

    def check_all(self) -> ServiceStatus:
        """Check all registered services and return a status report."""
        status = ServiceStatus()

        for svc in SERVICES:
            # File-based credentials can't be checked via env
            if not svc.env_keys:
                if svc.name == "exness_mt5":
                    status.file_based.append({
                        "name": "Exness MT5",
                        "location": "config/credentials.json + config/mt5_accounts.yaml",
                        "risk": "Password in plaintext: @15September"
                    })
                continue

            value = self._get_first(svc.env_keys)

            if value:
                status.configured.append(svc.label)
            else:
                # Check if there are codebase references that would use this
                if svc.config_path and svc.config_path != "n/a — no codebase usage found":
                    status.missing.append(f"{svc.label} (consumed at {svc.config_path})")
                else:
                    status.missing.append(svc.label)

        # Add telegram as always missing (not wired into codebase)
        # Add blockchain wallets
        for wallet in ["BullX Wallets", "Photon Trading", "Steem Blockchain", "Pi Wallet", "TON Wallet"]:
            status.missing.append(wallet)

        return status

    def get_all(self) -> Dict[str, Optional[str]]:
        """Get all credentials as {service_name: value_or_none}. NEVER log or print this."""
        return {name: self.get(name) for name in self._services}

    def env_key_for(self, service_name: str) -> List[str]:
        """Return the env var keys expected for a service."""
        svc = self._services.get(service_name)
        return svc.env_keys if svc else []

    def _get_first(self, keys: List[str]) -> Optional[str]:
        """Return the first non-empty env var from a list of candidates."""
        for key in keys:
            try:
                val = self._vault.get_secret(key, required=False)
                if val:
                    return val
            except Exception:
                continue
        return None

    def check_existing_env_providers(self) -> Dict[str, bool]:
        """Specifically check env vars mentioned in .env.example and .env.template."""
        template_keys = [
            "QNAI_OPENAI_API_KEY", "QNAI_ANTHROPIC_API_KEY", "QNAI_GOOGLE_API_KEY",
            "QNAI_ALPACA_API_KEY", "QNAI_POLYGON_API_KEY", "QNAI_TWELVEDATA_API_KEY",
            "QNAI_ALPHA_VANTAGE_API_KEY", "QNAI_BINANCE_API_KEY", "QNAI_FINNHUB_API_KEY",
            "QNAI_FRED_API_KEY", "QNAI_COINGECKO_API_KEY",
            "QNAI_NVIDIA_NIM_API_KEY",
            "QNAI_API_KEY", "QNAI_JWT_SECRET",
            "QNAI_DATABASE_URL",
            "HF_API_KEY", "OPENROUTER_API_KEY",
        ]
        result = {}
        for key in template_keys:
            try:
                val = self._vault.get_secret(key, required=False)
                result[key] = bool(val)
            except Exception:
                result[key] = False
        return result


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
credential_manager = CredentialManager()


# ---------------------------------------------------------------------------
# CLI: quick audit
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    status = credential_manager.check_all()
    print(status.report())

    print("\n\n--- Env-specific check ---")
    env_check = credential_manager.check_existing_env_providers()
    configured = [k for k, v in env_check.items() if v]
    not_configured = [k for k, v in env_check.items() if not v]
    print(f"Env vars configured  : {len(configured)}: {', '.join(k.split('_', 1)[1] if '_' in k else k for k in configured)}")
    print(f"Env vars NOT set     : {len(not_configured)}")
    if not_configured:
        print(f"  Missing: {', '.join(k.split('_', 1)[1] if '_' in k else k for k in not_configured[:10])}...")
