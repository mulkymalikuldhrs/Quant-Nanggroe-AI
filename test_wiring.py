"""Test all Quant Nanggroe API endpoints that dashboard pages depend on."""
import json, sys, time, urllib.request, urllib.error

BASE = "http://localhost:8333"
results = []  # (page, endpoint, method, status, valid, note)

def req(method, path, body=None, timeout=30):
    """Make HTTP request, return (status_code, body_dict_or_none)."""
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Content-Type", "application/json")
    try:
        resp = urllib.request.urlopen(r, timeout=timeout)
        status = resp.status
        text = resp.read().decode()
        try:
            body = json.loads(text)
        except json.JSONDecodeError:
            body = text
        return status, body
    except urllib.error.HTTPError as e:
        status = e.code
        try:
            body = json.loads(e.read().decode())
        except:
            body = str(e)
        return status, body
    except urllib.error.URLError as e:
        return 0, {"error": str(e.reason)}

def test(page, label, method, path, body=None):
    status, resp = req(method, path, body)
    valid = "YES" if 200 <= status < 500 else "NO"  # 500+ means broken
    note = ""
    if status == 0:
        note = "connection refused"
        valid = "NO"
    elif status == 200:
        note = "OK"
    elif status == 422:
        note = "validation error (needs params)"
        valid = "YES"  # endpoint exists and responds
    elif status == 401:
        note = "auth required"
        valid = "YES"
    elif status == 404:
        note = "not found"
        valid = "NO"
    elif status >= 500:
        note = f"server error: {resp}"
        valid = "NO"
    else:
        note = f"status {status}"
        valid = "YES" if status < 500 else "NO"
    results.append((page, label, method, path, status, valid, note))
    print(f"  [{valid}] {method:6s} {path:45s} -> {status} {note[:80]}")

def section(name):
    print(f"\n{'='*70}\n{name}\n{'='*70}")

# ── Warmup: hit /api/version first to load pydantic ──
print("Warming up pydantic (may take 60s+ on first load)...")
sys.stdout.flush()
status, resp = req("GET", "/api/version", timeout=120)
print(f"  Warmup: {status} {resp}")

section("1. SYSTEM / HEALTH")
test("system", "health", "GET", "/health")
test("system", "version", "GET", "/api/version")
test("system", "metrics", "GET", "/metrics")

section("2. AGENTS (agents page, colony page, dashboard home)")
test("agents", "status", "GET", "/api/agents/status")
test("agents", "decisions", "GET", "/api/agents/decisions")
test("agents", "kill-switch-status", "GET", "/api/agents/kill-switch/status")

section("3. BACKTEST (backtest page, strategies page)")
test("backtest", "strategies", "GET", "/api/backtest/strategies")
test("backtest", "engines", "GET", "/api/backtest/engines")
test("backtest", "factors", "GET", "/api/backtest/factors")
test("backtest", "list", "GET", "/api/backtest/list")

section("4. TRADING (trading page)")
test("trading", "positions", "GET", "/api/trading/positions")
test("trading", "orders", "GET", "/api/trading/orders")
test("trading", "exchanges", "GET", "/api/trading/exchanges")
test("trading", "trades", "GET", "/api/trading/trades")

section("5. MARKET (market page, dashboard home)")
test("market", "sentiment", "GET", "/api/market/sentiment")
test("market", "signals", "GET", "/api/market/signals")
test("market", "price", "GET", "/api/market/price/BTCUSD")
test("market", "candles", "GET", "/api/market/candles/BTCUSD")
test("market", "ohlcv", "POST", "/api/market/ohlcv", {"symbol": "BTCUSD", "timeframe": "1d", "limit": 10})
test("market", "regime", "POST", "/api/market/regime", {"symbol": "BTCUSD"})

section("6. PORTFOLIO (portfolio page, risk page)")
test("portfolio", "summary", "GET", "/api/portfolio/summary")
test("portfolio", "performance", "GET", "/api/portfolio/performance")
test("portfolio", "equity-curve", "GET", "/api/portfolio/equity-curve")
test("portfolio", "risk", "GET", "/api/portfolio/risk")

section("7. MEMORY (memory page)")
test("memory", "search", "GET", "/api/memory/search?q=test")

section("8. CHANNELS (channels page)")
test("channels", "list", "GET", "/api/channels/list")

section("9. COLONY (colony page)")
test("colony", "list", "GET", "/api/colony/list")
test("colony", "status", "GET", "/api/colony/status")
test("colony", "agents", "GET", "/api/colony/agents")

section("10. SECURITY (security page)")
test("security", "events", "GET", "/api/security/events")
test("security", "status", "GET", "/api/security/status")

section("11. TOOLS (tools page)")
test("tools", "list", "GET", "/api/tools/list")

section("12. MONITOR")
test("monitor", "summary", "GET", "/api/monitor/summary")
test("monitor", "health", "GET", "/api/monitor/health")
test("monitor", "metrics", "GET", "/api/monitor/metrics")

print(f"\n{'='*70}")
print("WIRING MATRIX")
print(f"{'='*70}")
print(f"{'Page':<20} {'API Endpoint':<40} {'Method':<8} {'Status':<8} {'Valid':<6} {'Note'}")
print(f"{'-'*20} {'-'*40} {'-'*8} {'-'*8} {'-'*6} {'-'*30}")
for page, label, method, path, status, valid, note in results:
    print(f"{page:<20} {path:<40} {method:<8} {status:<8} {valid:<6} {note[:60]}")

print(f"\nSUMMARY:")
pages_tested = set(r[0] for r in results)
valid_count = sum(1 for r in results if r[5] == "YES")
total = len(results)
print(f"  Pages tested: {len(pages_tested)} ({', '.join(sorted(pages_tested))})")
print(f"  Endpoints:    {total}")
print(f"  Working:      {valid_count}")
print(f"  Broken:       {total - valid_count}")
