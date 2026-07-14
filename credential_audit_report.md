# QNAI Credential Audit Report

**Source**: `credentials.md.txt` (Desktop) → QNAI codebase mapping
**Date**: 2026-07-14

---

## Summary

| Metric | Count |
|--------|-------|
| Credentials in source file | 35+ services |
| Wired into QNAI codebase | **12** (partial/direct) |
| Not wired / no codebase usage | **20+** |
| Plaintext in `config/` files | **1** (Exness MT5 password) |
| .env templates define but not populated | **17 env vars** |

---

## ✅ Services WITH codebase wiring

| # | Service | Env Var(s) | Codebase Location | Status in credentials.md |
|---|---------|-----------|-------------------|--------------------------|
| 1 | **Groq API** | `GROQ_API_KEY` | `engine/autonomous/llm_router.py` (line 23-25) | ✅ Keys present (gsk_\*) |
| 2 | **NVIDIA NIM** | `QNAI_NVIDIA_NIM_API_KEY` | `engine/nvidia_nim/config.py`, `engine/nim_provider.py` | ✅ 3 keys (nvapi-\*) |
| 3 | **OpenCode Zen** | — | `engine/autonomous/llm_router.py` | ❌ DEAD (401 auth invalid) |
| 4 | **Together AI** | `TOGETHER_API_KEY` | Referenced in fallback chain | ❌ BROKEN (402 credit limit) |
| 5 | **HuggingFace** | `HF_API_KEY` | `engine/autonomous/llm_router.py` (line 35) | ✅ 3 tokens (hf_\*) |
| 6 | **Alpha Vantage** | `QNAI_ALPHA_VANTAGE_API_KEY` | `.env.example`, `.env.template` | ✅ Key present |
| 7 | **Polygon.io** | `QNAI_POLYGON_API_KEY` / `QNAI_API_KEY` | `providers/data_manager.py` (line 62) | ✅ Key present |
| 8 | **GitHub** | `GITHUB_TOKEN` / `GH_TOKEN` | `connectors/github_integration.py` (stub) | ✅ 5+ tokens |
| 9 | **Exness MT5** | (config files) | `config/credentials.json`, `config/mt5_accounts.yaml` | ⚠️ Password in plaintext |
| 10 | **CoinGecko** | `QNAI_COINGECKO_API_KEY` | `providers/data_manager.py` (line 21) | ❌ No key in source |
| 11 | **Supabase** | `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` | `.env.template` | ✅ URL + all keys present |
| 12 | **OpenRouter** | `OPENROUTER_API_KEY` | `config/system_config.yaml`, `engine/autonomous/llm_router.py` | ❌ No key in source |

---

## ❌ Services IN credentials.md but NOT wired into codebase

These credentials are documented in `credentials.md.txt` but have **zero references** in the QNAI codebase:

| Service | What's in credentials.md |
|---------|--------------------------|
| **Telegram Bots** (6 bots) | 6 bot tokens + chat IDs |
| **Steem Blockchain** | Posting, active, owner, memo keys |
| **BullX Wallets** | EVM, Solana, Tron wallet + private keys |
| **Phantom Wallet** | Seed phrase + private key |
| **MEVX API** | API key |
| **Wix API** | JWT token + account ID |
| **Photon Trading** | Wallet address + private key |
| **TON Wallet** | Address + seed phrase |
| **Pi Wallet** | 2 wallets + seed phrases |
| **OpenMemory** | API key (m0-\*) |
| **Convex** | Deploy key + deployment URL |
| **Hyperbrowser** | API key |
| **Cron Job API** | API key |
| **Notion** | Secret token |
| **Helius (Solana)** | Dev API key |
| **AgentMail/SMTP** | API key + SMTP/IMAP credentials |
| **Tavily** | API key |
| **SkillsMP** | API key |
| **LobeHub** | API key |
| **OllamaCloud** | API key |
| **Composio MCP** | Token |
| **MCP Market** | API key |
| **Vercel** | Token + project ID |
| **Bytez AI** | API key |
| **FascAPI** | API key |
| **Financial Dataset** | API key |
| **Infura** | Project ID + seed phrase |
| **MetaMask** | 12-word seed phrase |
| **NVIDIA NIM (kimi-k2.6)** | Additional NIM key |

---

## ⚠️ Existing env templates expectations

`.env.example` and `.env.template` define these vars — **NONE** are currently set:

```
QNAI_OPENAI_API_KEY       QNAI_ANTHROPIC_API_KEY    QNAI_GOOGLE_API_KEY
QNAI_ALPACA_API_KEY       QNAI_ALPACA_SECRET_KEY    QNAI_POLYGON_API_KEY
QNAI_TWELVEDATA_API_KEY   QNAI_ALPHA_VANTAGE_API_KEY QNAI_BINANCE_API_KEY
QNAI_BINANCE_SECRET_KEY   QNAI_BYBIT_API_KEY        QNAI_BYBIT_SECRET_KEY
QNAI_FINNHUB_API_KEY      QNAI_FRED_API_KEY         QNAI_COINGECKO_API_KEY
QNAI_NVIDIA_NIM_API_KEY   QNAI_API_KEY              QNAI_JWT_SECRET
HF_API_KEY                 OPENROUTER_API_KEY        GITHUB_TOKEN
```

---

## 🔐 Files created

| File | Purpose |
|------|---------|
| `quant_nanggroe/security/credential_manager.py` | CredentialManager — single entry point for all service credentials. Reports configured vs missing. CLI-ready. |

### How to use

```python
from quant_nanggroe.security.credential_manager import credential_manager

# Full audit report
status = credential_manager.check_all()
print(status.report())

# Check a specific service
if credential_manager.check("nvidia_nim"):
    key = credential_manager.get("nvidia_nim")

# See which env vars a service expects
credential_manager.env_key_for("alpha_vantage")
# → ['QNAI_ALPHA_VANTAGE_API_KEY']
```

Or from CLI:
```bash
python -m quant_nanggroe.security.credential_manager
```

---

## 🚨 Security issues found

1. **Exness MT5 password in plaintext**: `config/credentials.json` and `config/mt5_accounts.yaml` both contain the password `@15September` in readable form.
2. **Credentials file contains blockchain seed phrases and private keys** — these are irreversibly compromised if the file is leaked.
3. **No .env file exists** — no credentials are loaded into environment variables, so none of the codebase's env-based credential loading works at runtime.
4. **Credentials scattered across multiple files** — `credentials.md.txt`, `config/credentials.json`, `config/mt5_accounts.yaml`, `config/system_config.yaml` all contain different secrets with no single manager.

---

## 📋 Next actions recommended

1. Create `.env` from `.env.template` and populate with credentials from `credentials.md.txt`
2. Remove `config/credentials.json` and `config/mt5_accounts.yaml` — migrate to env vars
3. File `credentials.md.txt` should be encrypted at rest or moved to a password manager
4. Wire Telegram bot tokens into a connector module
5. Wire Supabase credentials into a database connector
6. Review blockchain private keys — consider hardware wallet or keyless sign patterns
