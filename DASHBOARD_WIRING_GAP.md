# Dashboard → Backend Wiring Gap Analysis
Generated: 2026-08-04
Total pages: 28
Pages with API calls: 10
Pages WITHOUT API calls: 18

## agents/page.tsx
- Dashboard status: NO FETCH
- Backend: /api/agents/status → MISSING
- Backend: /api/agents/run → MISSING
- Backend: /api/agents/kill-switch/status → MISSING

## autonomous/page.tsx
- Dashboard status: NO FETCH
- Backend: /api/autonomous/status → MISSING
- Backend: /api/autonomous/start → MISSING
- Backend: /api/autonomous/stop → MISSING
- Backend: /api/autonomous/self-awareness → MISSING

## backtest/page.tsx
- Dashboard status: NO FETCH
- Backend: /api/backtest/strategies → MISSING
- Backend: /api/backtest/engines → EXISTS
- Backend: /api/backtest/run → MISSING
- Backend: /api/backtest/walk-forward → MISSING
- Backend: /api/backtest/tune → MISSING

## brokers/page.tsx
- Dashboard status: NO FETCH
- Backend: /api/brokers/ → MISSING
- Backend: /api/brokers/{name}/account → MISSING
- Backend: /api/brokers/{name}/positions → MISSING

## channels/page.tsx
- Dashboard status: NO FETCH
- Backend: /api/channels/list → MISSING

## colony/page.tsx
- Dashboard status: NO FETCH
- Backend: /api/colony/status → MISSING
- Backend: /api/colony/list → MISSING
- Backend: /api/colony/create → MISSING

## evolution/page.tsx
- Dashboard status: NO FETCH
- Backend: /api/evolution/status → MISSING
- Backend: /api/evolution/strategies → MISSING
- Backend: /api/evolution/trades → MISSING
- Backend: /api/evolution/config → MISSING

## factors/page.tsx
- Dashboard status: NO FETCH
- Backend: /api/backtest/factors → EXISTS

## market/page.tsx
- Dashboard status: NO FETCH
- Backend: /api/market/price/{symbol} → MISSING
- Backend: /api/market/sentiment → MISSING
- Backend: /api/market/signals → MISSING

## memory/page.tsx
- Dashboard status: NO FETCH
- Backend: /api/memory/search → MISSING
- Backend: /api/memory/store → MISSING
- Backend: /api/memory/list → MISSING

## orderflow/page.tsx
- Dashboard status: NO FETCH
- Backend: /api/terminal/cvd → MISSING
- Backend: /api/terminal/liquidity-walls → MISSING
- Backend: /api/terminal/orderbook → MISSING

## pipeline/page.tsx
- Dashboard status: NO FETCH
- Backend: /api/pipeline/status → MISSING

## portfolio/page.tsx
- Dashboard status: NO FETCH
- Backend: /api/portfolio/summary → MISSING
- Backend: /api/portfolio/performance → MISSING
- Backend: /api/portfolio/risk → MISSING

## qna-status/page.tsx
- Dashboard status: NO FETCH
- Backend: /api/qna-status → MISSING

## risk/page.tsx
- Dashboard status: NO FETCH
- Backend: /api/portfolio/risk → MISSING
- Backend: /api/monitor/risk → MISSING

## security/page.tsx
- Dashboard status: NO FETCH
- Backend: /api/security/events → MISSING
- Backend: /api/security/status → MISSING

## settings/page.tsx
- Dashboard status: NO FETCH
- Backend: /api/credentials → MISSING
- Backend: /api/config/schema → MISSING

## strategies/page.tsx
- Dashboard status: NO FETCH
- Backend: /api/strategies/list → MISSING
- Backend: /api/strategies/toggles → MISSING
- Backend: /api/backtest/strategies → MISSING

## terminal/page.tsx
- Dashboard status: NO FETCH
- Backend: /api/terminal/sentiment → MISSING
- Backend: /api/terminal/crypto-pulse → MISSING
- Backend: /api/terminal/macro-pulse → MISSING
- Backend: /api/terminal/econ-calendar → MISSING

## tools/page.tsx
- Dashboard status: NO FETCH
- Backend: /api/tools/list → MISSING
- Backend: /api/tools/{id}/execute → MISSING

## trading/page.tsx
- Dashboard status: NO FETCH
- Backend: /api/trading/positions → MISSING
- Backend: /api/trading/orders → EXISTS
- Backend: /api/trading/order → EXISTS

## trading/history/page.tsx
- Dashboard status: NO FETCH
- Backend: /api/trading/history → MISSING

## walkforward/page.tsx
- Dashboard status: NO FETCH
- Backend: /api/backtest/walk-forward → MISSING
- Backend: /api/backtest/walk-forward/status → MISSING

## Backend Stub/503/501 Endpoints
### causal_engine.py
  raise HTTPException(status_code=503, detail="Insufficient market data for DCC fit")
  raise HTTPException(status_code=503, detail="Insufficient price data")
### channels.py
  raise HTTPException(status_code=503, detail=f"Channel {channel_id} connector not available")
### features.py
  raise HTTPException(status_code=503, detail=f"feature_engine unavailable: {e}")
### memory.py
  raise HTTPException(status_code=501, detail="Vector store not available")
### options.py
  raise HTTPException(status_code=501, detail="Vol surface module requires scipy")
  raise HTTPException(status_code=501, detail=f"Strategy module error: {e}")
### orderbook.py
  status_code=503,
### rl.py
  raise HTTPException(status_code=501, detail=f"RL module not available: {e}")
### security_tools.py
  raise HTTPException(status_code=501, detail="Encryption not available")
  raise HTTPException(status_code=501, detail="Encryption not available")
### wiring_compat.py
  raise HTTPException(status_code=503, detail=f"Broker unavailable: {exc}")
  raise HTTPException(status_code=503, detail=f"Market data unavailable for {symbol}: {exc}")