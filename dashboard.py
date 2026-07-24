"""
Hedge Fund Dashboard — FastAPI
Running status + market context + strategy performance
"""
import sys, json, os
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse

app = FastAPI(title="Dhaher Hedge Fund Dashboard", version="5.1.0")

SRC = Path(__file__).parent
DATA = SRC / 'data'

@app.get("/", response_class=HTMLResponse)
def dashboard():
    # Load trade log
    trades = []
    trade_log = DATA / 'hedge_fund_trades.csv'
    if trade_log.exists():
        with open(trade_log) as f:
            lines = f.readlines()
            trades = [l.strip().split(',') for l in lines[-20:]]
    
    # Load market context
    ctx = {}
    ctx_file = DATA / 'context_cache' / 'market_context.json'
    if ctx_file.exists():
        with open(ctx_file) as f:
            ctx = json.load(f)
    
    # Load trade log stats
    wins = sum(1 for t in trades[1:] if len(t) > 5 and t[5].strip() == 'win') if trades else 0
    losses = sum(1 for t in trades[1:] if len(t) > 5 and t[5].strip() == 'loss') if trades else 0
    total = wins + losses
    
    strategies = [
        ("Wyckoff", "🟢", "SR 3.022", "Live"),
        ("MeanRev", "🟢", "SR 1.982", "Live"),
        ("MSNR", "🟢", "SR 1.889", "Live"),
        ("SMC 🆕", "🟢", "SR 1.562", "UPGRADED"),
        ("Dhaher System", "🟡", "Tuning", "Optimizing"),
        ("Kronos", "🔵", "P1", "In Progress"),
    ]
    
    html = f"""<!DOCTYPE html>
<html>
<head><title>Dhaher Hedge Fund</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:system-ui,-apple-system,sans-serif;background:#0a0a0f;color:#e0e0e0;padding:20px}}
h1{{color:#00ff88;font-size:24px;margin-bottom:5px}}
.sub{{color:#888;font-size:14px;margin-bottom:20px}}
.card{{background:#14141f;border:1px solid #2a2a3a;border-radius:12px;padding:16px;margin-bottom:16px}}
.card h2{{color:#00ff88;font-size:16px;margin-bottom:12px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}}
.stat{{background:#1a1a2a;padding:12px;border-radius:8px;text-align:center}}
.stat .val{{font-size:28px;font-weight:bold;color:#00ff88}}
.stat .lbl{{font-size:12px;color:#888;margin-top:4px}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th,td{{padding:8px 12px;text-align:left;border-bottom:1px solid #2a2a3a}}
th{{color:#888;font-weight:500}}
.strat-dot{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px}}
.green{{background:#00ff88}}
.yellow{{background:#ffcc00}}
.blue{{background:#4488ff}}
.metrics{{color:#888;font-size:12px}}
</style>
</head>
<body>
<h1>📈 Dhaher Hedge Fund</h1>
<p class="sub">{datetime.now().strftime('%A, %d %B %Y %H:%M WIB')} · Valetax Demo $1K</p>

<div class="card">
<h2>💰 Account</h2>
<div class="grid">
<div class="stat"><div class="val">$1,000</div><div class="lbl">Balance</div></div>
<div class="stat"><div class="val">1:2000</div><div class="lbl">Leverage</div></div>
<div class="stat"><div class="val">{total}</div><div class="lbl">Total Trades</div></div>
<div class="stat"><div class="val">{wins}/{losses}</div><div class="lbl">W/L</div></div>
</div>
</div>

<div class="card">
<h2>🎯 Strategies ({len(strategies)})</h2>
<table>
<tr><th></th><th>Strategy</th><th>Sharpe</th><th>Status</th></tr>"""
    for name, dot, sr, status in strategies:
        html += f"<tr><td><span class='strat-dot {dot.replace('🟢','green').replace('🟡','yellow').replace('🔵','blue')}'></span></td><td>{name}</td><td>{sr}</td><td>{status}</td></tr>"
    
    html += """</table>
</div>

<div class="card">
<h2>🌍 Market Context</h2>
<div class="grid">"""
    
    ctx_items = [
        ("DXY", ctx.get('dxy', 'N/A')),
        ("VIX", ctx.get('vix', 'N/A')),
        ("10Y Yield", ctx.get('yield', 'N/A')),
        ("EURUSD", ctx.get('eurusd', 'N/A')),
    ]
    for label, val in ctx_items:
        html += f"<div class='stat'><div class='val' style='font-size:20px'>{val}</div><div class='lbl'>{label}</div></div>"
    
    html += """</div>
</div>

<div class="card">
<h2>📋 Recent Trades</h2>
<table>
<tr><th>Time</th><th>Pair</th><th>Action</th><th>Volume</th><th>Result</th></tr>"""
    
    for t in trades[1:][-10:]:
        if len(t) >= 6:
            html += f"<tr><td>{t[0][:16] if t[0] else ''}</td><td>{t[3] if len(t)>3 else ''}</td><td>{t[4] if len(t)>4 else ''}</td><td>{t[2] if len(t)>2 else ''}</td><td>{t[5]}</td></tr>"
    
    html += """</table>
</div>
<p style="text-align:center;color:#444;font-size:12px">Dhaher Labs Hedge Fund · Auto-update setiap cron cycle</p>
</body>
</html>"""
    return HTMLResponse(html)

@app.get("/health")
def health():
    return {"status": "live", "balance": 1000}
