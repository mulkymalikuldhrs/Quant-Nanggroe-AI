# ════════════════════════════════════════════
# SECURITY AUDIT REPORT — E:/trading/
# 19 July 2026 — HACKERBOT Autonomous Audit
# ════════════════════════════════════════════

## Target: `E:/trading/`

### Files Scanned
- 17 Python files (.py)
- 2 Batch files (.bat)
- 1 Environment file (.env)
- 2 JSON config files
- 1 Markdown handoff

### Finding Summary

| Severity | Count |
|----------|-------|
| 🔴 CRITICAL | 5 |
| 🟡 HIGH | 3 |
| 🔵 MEDIUM | 1 |
| ⚪ LOW | 2 |

---

## 🔴 CRITICAL (Fix Immediately)

### C1 — Hardcoded MT5 Password in hedge_fund.py

**File:** `E:/trading/hedge_fund.py`, line 13

```python
CREDS = {"login": 372044706, "password": "@15September", "server": "ValetaxIntl_Live-2"}
```

**Risk:** Plaintext broker credentials hardcoded in source code. Anyone who gains read access to this file can:
- Log into the MT5 Valetax account
- View portfolio, trade history
- Execute unauthorized trades
- Withdraw funds (if MT5 allows)

**Worse — line 28 passes credentials via CLI:**
```python
subprocess.Popen([TERMINAL, f"/login:{CREDS['login']}", f"/password:{CREDS['password']}", f"/server:{CREDS['server']}"])
```
These credentials leak into the process table and can be viewed by any process on the same machine via `wmic process get commandline`.

**Evidence:**
- `grep -rn "password.*@15September" /e/trading/` → hedge_fund.py:13:28

---

### C2 — Plaintext MT5 Password in metatrader-mcp.env

**File:** `E:/trading/metatrader-mcp.env`, line 3

```
MT5_PASSWORD=@15September
```

**Risk:** Same credentials as C1, stored unencrypted in a `.env` file that is world-readable (644). On Windows, any user or malware on this machine can read it.

**File permissions:** 0644 (-rw-r--r--) — readable by **everyone** on the system.

---

### C3 — Plaintext Credentials in freqtrade.json

**File:** `E:/trading/config/freqtrade.json`, lines 24-27

```json
"jwt_secret_key": "dhaher-secret-key-2026",
"username": "dhaher",
"password": "trading2026"
```

**Risk:**
- **jwt_secret_key** is weak (`dhaher-secret-key-2026`) — JWT tokens signed with this key can be forged by anyone who reads the file.
- **password** `trading2026` is weak and used in multiple places.
- If the Freqtrade API server is exposed (currently bound to `127.0.0.1:8080`), an attacker with local access can authenticate.

---

### C4 — Password Leaked via Batch File (ui.bat)

**File:** `E:/trading/ui.bat`, line 8

```batch
echo Password: trading2026
```

**Risk:** Running `ui.bat` prints the password to the console, where it's visible to anyone at the terminal, captured in scrollback, and potentially logged.

---

### C5 — Password Reuse Across Services

**Finding:** Password `@15September` is used for:
1. MT5 account (Valetax Intl — real money)
2. MCP server auth

Password `trading2026` is used for:
1. Freqtrade UI API
2. Displayed in `ui.bat`

**Risk:** Password reuse means a compromise of one service compromises all. The MT5 password (`@15September`) appears to be a date-based password (15 September) — predictable pattern.

---

## 🟡 HIGH

### H1 — All Config Files are World-Readable (0644)

**Files affected:**
```
0644 /e/trading/metatrader-mcp.env      ← MT5 password
0644 /e/trading/config/freqtrade.json   ← username/password/JWT secret
0644 /e/trading/config/risk.json        ← trading config (lower risk)
0644 /e/trading/hedge_fund.py           ← hardcoded CREDS
0644 /e/trading/*.py (all)
```

**Risk:** On a shared system or if malware gains user-level access, every secret in this directory is immediately readable. No files have restricted permissions (e.g., 600).

**Recommended:** Set `chmod 600` on `metatrader-mcp.env`, `config/freqtrade.json`, and any file containing credentials.

---

### H2 — No .gitignore / No Protection Against Accidental Git Commit

**Finding:** No `.gitignore` file exists in `E:/trading/`.

**Risk:** If this directory is ever `git init`'d and committed (even to a local repo), ALL secrets become part of git history — including the MT5 password, JWT secret, and API credentials. Git history is notoriously difficult to clean.

**Files that MUST be in .gitignore:**
- `metatrader-mcp.env`
- `config/freqtrade.json`
- `*.local`
- `*.secrets`
- `data/`
- `logs/`
- `.venv/`

---

### H3 — Broker Credentials Passed via Command Line Arguments

**File:** `E:/trading/hedge_fund.py`, line 28

```python
subprocess.Popen([TERMINAL, f"/login:{CREDS['login']}", f"/password:{CREDS['password']}", f"/server:{CREDS['server']}"])
```

**Risk:** Command-line arguments are visible to all processes on Windows via:
```
wmic process get commandline
```
or Process Explorer / Task Manager. Any malware or user on this machine can see the password in the process table.

---

## 🔵 MEDIUM

### M1 — Telegram Chat ID Exposed in Config + Empty Token

**File:** `E:/trading/config/freqtrade.json`, lines 13-16

```json
"telegram": {
    "enabled": false,
    "chat_id": "1474659350",
    "token": ""
}
```

**Risk:** The Telegram `chat_id` (`1474659350`) is exposed. While Telegram bot is disabled (`token: ""`), if it's ever enabled, the chat_id is known — an attacker who gains the bot token can pwn the trading notifications channel.

---

## ⚪ LOW

### L1 — Weak JWT Secret Key

**File:** `E:/trading/config/freqtrade.json`, line 24

```json
"jwt_secret_key": "dhaher-secret-key-2026"
```

**Risk:** The JWT signing key is a predictable, low-entropy string. If the API server is exposed beyond localhost, JWT tokens can be forged. Severity reduced because the server binds to `127.0.0.1` only.

---

### L2 — Dangerously High Leverage Configured

**File:** `E:/trading/config/risk.json`, line 8

```json
"leverage": 2000
```

**Risk:** 2000:1 leverage means a 0.05% adverse move liquidates the entire account. This is an extreme financial risk, not a security vulnerability per se, but it compounds the damage if credentials are compromised — an attacker can drain the account in seconds.

---

## ✅ GOOD (Pass)

| Item | Status |
|------|--------|
| No .git directory | **PASS** — no git history with secrets |
| No SSH keys in repo | **PASS** |
| No database connection strings | **PASS** |
| No AWS/Azure/GCP keys | **PASS** |
| No hardcoded API keys (OpenAI, etc.) | **PASS** |
| No eval() | **PASS** |
| SSL/TLS not applicable (desktop MT5) | **PASS** |
| No `StrictHostKeyChecking=no` | **PASS** |

---

## ⚡ Priority Recommendations

### CRITICAL (Today)

1. **Move credentials out of source code**
   - `E:/trading/hedge_fund.py` line 13: Remove `CREDS` dict. Read from environment variables or a secrets file loaded at runtime.
   - Create `E:/trading/.secrets/config.enc` (encrypted) OR use environment variables:
     ```python
     CREDS = {
         "login": int(os.environ["MT5_LOGIN"]),
         "password": os.environ["MT5_PASSWORD"],
         "server": os.environ["MT5_SERVER"],
     }
     ```

2. **Restrict file permissions**
   ```bash
   chmod 600 /e/trading/metatrader-mcp.env
   chmod 600 /e/trading/config/freqtrade.json
   ```

3. **Remove CLI password from subprocess call**
   - `E:/trading/hedge_fund.py` line 28: Instead of passing credentials on the CLI, use MT5's `mt5.initialize(path=..., login=..., password=..., server=...)` directly (the MT5 Python API supports this).

4. **Create a .gitignore**
   ```gitignore
   # E:/trading/.gitignore
   metatrader-mcp.env
   config/freqtrade.json
   .secrets/
   *.local
   data/
   logs/
   .venv/
   __pycache__/
   ```

5. **Change all passwords** — both `@15September` and `trading2026` have been exposed in multiple plaintext files.

### HIGH (This Week)

6. **Remove password echo from `ui.bat`** line 8: Delete or comment out the `echo Password: trading2026` line.

7. **Add `.env` loader** to scripts that need MT5 credentials:
   ```bash
   pip install python-dotenv
   ```
   Then `from dotenv import load_dotenv; load_dotenv("metatrader-mcp.env")` instead of hardcoding.

---

## Disclaimer

This audit was performed on a local, non-production trading system for educational/security awareness purposes. Findings reflect the state of files at audit time. Real production trading systems should undergo professional security review.
