# UI PLAN — QNA v8.0.21 (2026-09-03) — All Complete UI + Auto Launch

**SSOT:** `CANONICAL.md v8.0.21` — dashboard 31p, brutalism Tactical Telemetry Dark, launch.bat 1, vector 6 live

## 1. Inventory — 31p + 46 API 207 route

**Dashboard 31p:** `agents, autonomous, backtest, brokers, candle-monitor, channels, colony, committee, config, data-pipeline, evaluator, evolution, export, factors, market, memory, notifications, orderflow, pipeline, portfolio, qna-status, risk, security, settings, strategies, tools, trading, trading/history, vector, walkforward` + `/` root

**API 46 file 207 route:** `market, trading, brokers, export, assistant, vector, autonomous, agents, portfolio, risk, etc.` — **28 REAL, 2 hybrid (factors, orderflow), 1 no-op (pipeline Run)**

## 2. Settings/Env/Config — All Complete

**Settings page:** `dashboard/src/app/settings/page.tsx:55` — `apiKeys, brokers, exchanges, llmKeys, riskLimits, systemToggles, agentModels` — `GET /api/credentials` `PUT /api/credentials` `/api/config/files` — **wired** `file:line settings:75 load, 94 save, 125 addBroker, 322 llmKeys` — **complete**, needs `env` sync.

**Env:** `qna.py:27 load_dotenv(".env")` before import, `QNAI_JWT_SECRET`, `QNA_ADMIN_API_KEY`, `MT5_LOGIN/PASSWORD/SERVER`, `QNA_LIVE_TRADING=0`, `launch.bat 29` auto-gen `.env` `QNAI_JWT_SECRET` `TZ=Asia/Jakarta` — **complete**, `PYTHONPATH=""` guard.

**Config:** `config/mt5_accounts.yaml` gitignored, `config/*` editable via `/config` `PUT /api/config/files/{name}` `file-backed` `secret masking` `path-traversal guard` — **complete**.

**Plan:** Keep `settings` as **single UI** for `env+config+brokers+LLM+risk` — add `env` sync: `settings` `Save` writes to `config/credentials.json` + `.env` via `bootstrap_env()` `api/app.py:31`.

## 3. Chart/Orderflow — Wire to MT5 Real

**Chart:** `dashboard/src/app/market/page.tsx:104` `lightweight-charts 5.2` `CandlestickSeries` `priceToCoordinate` `trading/page.tsx:239` `close via ticket` `brokersApi.modify/close` `market drag SL/TP` `overlay` `priceToCoordinate` `coordinateToPrice` `handleDragEnd` `brokersApi.modifyPosition` — **WIRE:** `mt5_adapter:235 ticket+sl/tp` `api/routes/brokers:165 modify 195 close` `POST /{name}/modify` `ticket` `stop_loss` `take_profit` — **complete**, `market` already `drag 0.05 mesh` `vector Step 4.6`.

**Orderflow:** `dashboard/src/app/orderflow/page.tsx` `Bookmap, heatmap, CVD, VWAP` `proxied to backend /api/orderflow` — **hybrid** `orderbook` `time&sales` `FIXED` `fail-closed empty` `brokers/page.tsx` dark-tech rewrite `no Math.random` — **keep fail-closed** `UNAVAILABLE` vs fake, **wire** `mt5 symbol_info_tick` `orderbook` when `trade_mode=4`.

**Portfolio:** `dashboard/src/app/portfolio/page.tsx:275` `bbg-cell` `ATR $2,450→--` `kellyFraction` — **complete**.

**Risk:** `dashboard/src/app/risk/page.tsx:281` `0.5%` `used 50` — **wire** `GET /api/portfolio/risk` `RiskManager` `9-gate`.

## 4. Chatbot — Wire to LLM + Tool Calling

**Current:** `assistant-widget.tsx:105` `apiRequest /api/assistant/chat` `rule 7 intent` `assistant.py:1 NO LLM 7 regex` `status/positions/scorecard/allocation/close/export/help` `190-198`

**Target:** `chat_llm POST /api/assistant/chat_llm` `groq/openai` `llmKeys settings:322` `history 8` `tool calling` `status,positions,close,risk,backtest,agents/status,portfolio/summary` `memoryApi.search:311` `streaming SSE` `ReadableStream` `markdown+recharts` `voice MediaRecorder` `selectedSymbol store:99` `CONFIRM` `risk` `slash /` `command-palette:6`

**Plan:** Keep `rule` fallback, add `chat_llm` with `NIMProvider` `REAL-ONLY` `Ollama` `history` `tool` `streaming` `recharts` `voice` — **complete**.

## 5. Auto Launch — Daemon + QNA Entry + Tray

**Current:** `launch.bat 198` `launch.sh 121` `qna.py 1055` `daemon 1s M15/H1/H4/D1` `CandleScheduler 8×4=32` `probe 0/32` `weekly 0 WIB` `qna_tray.py:43 Online/Offline/Error` `5s poll` `GET /health` `webbrowser.open` `Exit` `Start/Restart`

**Plan:** `launch.bat all` **Single** `Backend :8000 + Dashboard :3000 + Tray + Browser` `pause` `all` `api` `daemon` `dashboard` `test` `status` `weekly-reset` `logs` `monitor` `verbose` — **auto launch** `Backend :8000` `Dashboard :3000` `Tray` `Browser` `WIB` `PYTHONPATH=""` `PY=.venv\Scripts\python.exe` `logs` `data/persistence` `weekly_override.json` `+07:00` — **complete**, `launch.sh` `+x` `chmod` `timeout 15000`.

**QNA Entry:** `qna.py` **single SSOT** `daemon` `api` `status` `backtest` `load_dotenv` `QNA_KILL_SWITCH_STATE_FILE` `L1 daily 0.8%` `L2/L3 CONFIRM_RESET_AFTER_REVIEW` — **complete**.

## 6. All Complete UI Checklist

- [x] `trading` `market` `portfolio` `risk` `brokers` `settings` `config` `vector` `export` `pipeline` `agents` `market drag` `trading close` `assistant` `orderflow` `chart` `all 31p`
- [ ] `tuning` `retrain_report.json` `best_params_for` `decay guard` `allocation_map 10/102` `0.35` `yfinance EURUSD=X` `strategy_evaluator:111 RR` `MCP 23689` `graphify 28208`
- [ ] `notifications 5s→WS` `websocket.ts` `useRealtimeData` `store.ts` `addNotification`
- [ ] `PWA 4h` vs `Electron 120MB` vs `Tauri 8MB` `manifest.json` `service-worker`

## 7. Next Steps

1. **Wire chatbot LLM** `assistant.py:264 chat_llm` `NIMProvider` `history` `tool` `streaming`
2. **Fix orderflow live** `mt5 orderbook` `trade_mode` `bare EURUSD` `4`
3. **Auto launch verify** `launch.bat all` `5s` `Backend 8000 Dashboard 3000 Tray Browser`
4. **Verify** `tsc clean` `MCP 23689` `test_vector 16/16` `test 29/29` `git status 0` `push 5 remote`

**Plus/Minus:**
- **Plus:** `MCP 23689 vector6 drag SL/TP FILLED NZDUSD 22:14 WIB` `31p` `207 CPCV` `launch 1` `PWA 4h`
- **Minus:** `tri_arb dry-run` `grid lot fixed` `committee 0.10 noise` `CPCV 10/102` `weekly 0 mask` `yfinance` `tuning stale`
- **Pro:** `fail-closed` `REAL-ONLY` `single position` `trailing short-aware` `BE+ATR` `auto-detect 372044706`
- **Cons:** `vector origin USD-base` `√2 myth` `sigma 0.05 540 pips` `grid 0.05 across vols 10-100x`
