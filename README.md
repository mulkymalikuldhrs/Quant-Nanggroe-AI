# Quant-Nanggroe-AI

> Autonomous Quantitative Hedge Fund — FX/Commodity/Indices on MT5
> Version: v8.0.0-alpha | Status: LIVE (proof phase)

## Quick Start
```bash
"QNA Launcher.bat"          # Windows all-in-one
python qna.py daemon        # Live autonomous trading loop
python qna.py api           # FastAPI backend :8000
cd dashboard && npm run dev # Dashboard :3000
```

## Documentation
**[CANONICAL.md](CANONICAL.md)** is the single source of truth for ALL claims, architecture, strategy evidence, and operational procedures. Every other .md file is a mirror or has been consolidated into it.

## Key Features (v8.0)
- Signal Aggregation Engine — one position per symbol, fixed 0.5% risk
- CPCV Validation — tri-asset combinatorial purged cross-validation
- Per-Symbol Allocation — only CPCV-proven specialists trade each asset class
- Tuned Params — Bayesian/grid-search optimized parameters per symbol
- Native SMC Engine — Order Block, FVG, BOS/CHoCH, Liquidity Sweep
- Trading Profiles — scalp(M15)/day(H1)/swing(D1) ATR-adaptive SL/TP
- Journal-MT5 Sync — real PnL flows into self-evaluate loop
- Trade Awareness — what/why/how/lesson per closed trade
- Export Center — custom date range to xlsx/csv/md/json/pdf
- Config Center — every config/*.yaml editable via UI
