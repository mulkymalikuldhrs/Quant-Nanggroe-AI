#!/usr/bin/env python3
"""Dhaher Hedge Fund Terminal — semua tools dalam satu pipeline"""
import sys, os, json, subprocess, time
from pathlib import Path

BASE = Path("E:/trading")
TOOLS = {
    "trading":       BASE,
    "aihf":          Path("E:/ai-hedge-fund"),
    "hidden":        Path("E:/hidden-regime"),
    "freq":          Path("E:/freqtrade"),
    "freqmcp":       Path("E:/freqtrade-mcp"),
    "langalpha":     Path("E:/LangAlpha"),
    "tradingagents": Path("E:/tradingagents"),
    "agentquant":    Path("E:/AgentQuant"),
    "aitrader":      Path("E:/AI-Trader"),
    "clodds":        Path("E:/CloddsBot"),
    "finrl":         Path("E:/FinRL"),
    "lean":          Path("E:/Lean"),
    "lumibot":       Path("E:/lumibot"),
    "qlib":          Path("E:/qlib"),
    "rdagent":       Path("E:/RD-Agent"),
    "gastown":       Path("E:/gastown_bin"),
}

def wib():
    return time.strftime("%H:%M WIB", time.gmtime(time.time() + 7*3600))

def hr(): print("-" * 50)

def menu():
    print(f"""
  DHAHER HEDGE FUND PIPELINE      {wib()}
╔══════════════════════════════════════╗
║ SIGNAL GENERATION                   ║
║  [1] AI-Hedge-Fund (15 agents)     ║
║  [2] Hidden-Regime (market)        ║
║  [3] AI-Trader (Node.js)           ║
║  [4] LangAlpha (research)          ║
╠══════════════════════════════════════╣
║ EXECUTION                           ║
║  [5] Hedge fund live (MT5 Valetax) ║
║  [6] Freqtrade (crypto)            ║
╠══════════════════════════════════════╣
║ RESEARCH & QUANT                    ║
║  [7] AgentQuant / FinRL / Qlib     ║
║  [8] RD-Agent / Lumibot            ║
╠══════════════════════════════════════╣
║ ORCHESTRATION                       ║
║  [g] Gastown rig                   ║
║  [t] TradingAgents / CloddsBot     ║
║  [L] Lean (C# QuantConnect)        ║
╠══════════════════════════════════════╣
║  [s] System status (semua tools)   ║
║  [x] Exit                          ║
╚══════════════════════════════════════╝
""")
    return input("Pilih: ").strip().lower()

def check_all():
    print("\n=== STATUS SEMUA TOOLS → MT5 ===\n")
    print("   VOTING NOW (di aggregator): SMA, AIHF, Hidden-Regime, TradingAgents")
    print("   BUTUH SETUP: AI-Trader (npm), LangAlpha (uv sync), CloddsBot (npm)")
    print("   LIBRARY (pake di strategi): FinRL, lumibot, qlib")
    print("   BEDA STACK: Lean (C# QuantConnect)")
    print("   BROKEN: freqtrade (venv kosong)\n")
    base = {"trading/":"✅ pipeline hub","ai-hedge-fund/":"✅ voting","hidden-regime/":"✅ voting",
            "tradingagents/":"🆕 voting","freqtrade/":"🔴 venv kosong","freqtrade-mcp/":"🟡 standby",
            "LangAlpha/":"🟡 butuh uv sync","AI-Trader/":"🟡 butuh npm","CloddsBot/":"🟡 butuh npm",
            "AgentQuant/":"🟡 research UI","FinRL/":"🟡 library","Lean/":"🟡 C# stack",
            "lumibot/":"🟡 library","qlib/":"🟡 library","RD-Agent/":"🟡 research",
            "Gastown/":"✅ binary ok"}
    for name, status in base.items():
        p = Path(f"E:/{name}")
        icon = "✅" if p.exists() else "❌"
        print(f"  {icon} {name} {status}")

def run_script(path, label):
    """Run a Python script and show output"""
    if not path.exists():
        print(f"  ❌ {label}: not found")
        return
    r = subprocess.run([sys.executable, str(path)], capture_output=True, text=True, timeout=30)
    out = (r.stdout + r.stderr)[:300]
    print(f"  {out}")

def main():
    while True:
        c = menu()
        if c == "1":
            print("\n=== AI-Hedge-Fund ===\n")
            r = subprocess.run([sys.executable, "-c", """
import sys; sys.path.insert(0,'E:/ai-hedge-fund')
try:
    from src.main import run_hedge_fund
    print('✅ AIHF ready - run_hedge_fund() available')
except Exception as e: print(f'  {e}')
"""], capture_output=True, text=True, timeout=15)
            print(r.stdout + r.stderr)
            print("   Jalankan: cd /e/ai-hedge-fund && python -m src.main")
        elif c == "2":
            print("\n=== Hidden-Regime ===\n")
            print("   MCP server aktif. Tools: detect_regime, statistics, transitions")
            print("   Akses via Hermes MCP atau langsung: cd /e/hidden-regime")
        elif c == "3":
            print("\n=== AI-Trader ===\n")
            print("   Node.js service. Butuh npm install: cd /e/AI-Trader && npm start")
        elif c == "4":
            print("\n=== LangAlpha ===\n")
            print("   Research harness. Butuh uv sync: cd /e/LangAlpha && uv sync")
        elif c == "5":
            print("\n=== Hedge Fund Live ===\n")
            r = subprocess.run([sys.executable, str(TOOLS["trading"]/"hedge_fund.py")],
                             capture_output=True, text=True, timeout=60)
            print(r.stdout[-400:] + r.stderr[-200:])
        elif c == "6":
            print("\n=== Freqtrade ===\n")
            print("   🔴 Venv 95% kosong. Setup: cd /e/freqtrade && .venv/Scripts/pip install -r requirements.txt")
            print("   Lalu: freqtrade trade --config user_data/config.json")
        elif c == "7":
            print("\n=== Quant Research ===\n")
            print("   AgentQuant: cd /e/AgentQuant && python run_app.py")
            print("   FinRL: cd /e/FinRL && python -m finrl.main")
            print("   Qlib: cd /e/qlib && python -m qlib.workflow.cli")
        elif c == "8":
            print("\n=== Research ===\n")
            print("   RD-Agent: cd /e/RD-Agent && python -m rdagent.main")
            print("   Lumibot: pip install lumibot (library, import in strategies)")
        elif c == "g":
            print("\n=== Gastown ===\n")
            gt = TOOLS["gastown"]/"gt.exe"
            r = subprocess.run([str(gt), "status"], capture_output=True, text=True, timeout=10)
            print((r.stdout + r.stderr)[:500])
        elif c == "t":
            print("\n=== TradingAgents / CloddsBot ===\n")
            print("   TradingAgents: cd /e/tradingagents && python main.py")
            print("   CloddsBot: cd /e/CloddsBot && python -m clodds.main")
        elif c == "l":
            print("\n=== Lean (C# QuantConnect) ===\n")
            print("   C#/.NET stack. Butuh: dotnet build E:/Lean/Lean.sln")
            print("   Pipeline integration via CLI output parsing")
        elif c == "s":
            check_all()
        elif c == "x":
            break
        else:
            print("?")
        input("\nEnter...")

if __name__ == "__main__":
    main()
