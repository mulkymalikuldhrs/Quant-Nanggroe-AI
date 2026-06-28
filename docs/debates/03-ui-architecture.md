# Debate Record: Theme 3 — UI Architecture & Visualization

**Date:** 2026-06-28
**Presiding:** Dev Lead (w: 1.5)
**Council:** QT (w: 1.2), Data Engineer (w: 1.0), PM (w: 2.0)
**Questions:** Q5-Q7, Q14, Q43-Q61

---

## Round 1: Initial Stances

### Dev Lead
- **Q5:** Wire api-client to pages, replace mock data. No middleware, thin UI.
- **Q6:** NO dragable. DnD adds 23KB, layout persistence, complexity. Zero alpha.
- **Q7:** Only what trader needs to SEE or DECIDE. UI is a window, not the system.
- **Q14:** Active positions + configurable watchlist. Not all pairs.
- **Q43-Q61:** Essential: chart (lightweight-charts 5KB), P&L, risk, signals, order mgmt, backtest, agent status. **Bloat:** dragable, MCP UI, MT5 wizard, broker manager, LLM API, custom URLs, bookmap, Telegram UI, strategy builder, all-pairs browser.
- **Priorities:** Kill mock data → WebSocket stream → lightweight-charts

### QT
- **Q6:** YES dragable. Trader's mental model changes intraday.
- **Q7:** Order entry, live P&L, order book depth, position sizing, hotkeys, execution log, kill-switch.
- **Q14:** Unified positions table with asset/side/qty/entry/mark/uP&L. Sortable by P&L.
- **Q43-Q61:** Open positions, order book, chart (candle+EMA+VWAP), broker summary, economic calendar, data toggle, Telegram+CSV export.
- **Priorities:** Hotkey-driven order entry, live P&L sorted by loser, kill-switch 1-click

### Data Engineer
- **Q5:** Declarative config-driven datasource registry. No visual wiring.
- **Q6:** NO dragable. Fixed grid with column visibility.
- **Q7:** Provider health, per-symbol staleness, bar count, cache hit/miss, fetch queue, pipeline health score.
- **Q14:** Data Universe grid: symbols × providers = freshness status cells.
- **Q43-Q61:** Data source toggle (P0), freshness indicators (P0), coverage grid (P0), cache analytics (P1), custom data URL (P2).
- **Priorities:** Data freshness monitoring, cache optimization, automated provider failover

### PM
- **Q5:** Minimal: strategy on/off, global risk limit slider, status indicator.
- **Q6:** **NO. Veto drag-and-drop.** Cosmetic, delays deployment.
- **Q7:** Essential: P&L, drawdown, exposure, strategy status, signal timestamp, daily P&L.
- **Q14:** Aggregated first. Top 5 by P&L, concentration %. Individual drill-down tier-2.
- **Q43-Q61:** P&L tracking (mandatory), position mgmt (mandatory), toggle (mandatory). Charts defer. CSV export enough. Economic calendar skip.
- **Veto:** Drag-and-drop, economic calendar, complex charting, pair-level before aggregated, any UI blocking RegimeBased deployment.

---

## Round 2: Dev Lead Final Decision

### Q5: Wiring
Imperative: api-client hooks in thin React components. No middleware, no visual wiring. Config-driven datasource registry.

### Q6: Dragable
**NO.** 4:1 against, PM vetoed. Fixed grid with column visibility presets. QT's intraday layout concern solved via preset slot layouts, not free drag.

### Q7: UI Scope
Only what trader needs to SEE or DECIDE: strategy status (on/off), global risk limit slider, real-time P&L + drawdown, total exposure. No order entry hotkeys, no order book depth, no execution log (tier-2). Backend must not wait for frontend.

### Q14: Pairs Visibility
Aggregated first: portfolio exposure by asset class, top 5 ±P&L, concentration %. Pair-level drill-down tier-2. Data Eng's freshness grid = separate ops panel, not main trading UI.

### Q43-Q61: Feature Scope
**Build:** P&L tracking, position exposure + risk limit, strategy status panel, toggle settings, lightweight-charts lib installed (not yet integrated).
**Defer:** Chart rendering, CSV export, pair drill-down, order entry, data pipeline health panel.
**Skip:** Drag-and-drop, economic calendar, MT5 wizard, broker manager, LLM settings, custom URLs, bookmap, Telegram UI, strategy builder, all-pairs browser, Excel integration, MCP UI.

### Minimum Viable UI
1. Strategy on/off toggle + live status indicator
2. Global risk limit slider (one number)
3. Real-time P&L (total + drawdown %)
4. Total exposure / concentration %
5. Last signal timestamp + direction

### Priority Ranking
1. Kill all mock data — wire api-client to real WebSocket stream
2. Strategy status panel — toggle RegimeBased on/off, show live state
3. Real-time P&L + drawdown indicator
4. Position exposure + risk limit monitor
5. Aggregated portfolio view — top 5 ±P&L, concentration
6. Fixed-grid layout with column visibility presets
7. Pair-level drill-down (tier-2)
8. Chart integration (lightweight-charts, post-deployment)
9. CSV export
10. Data pipeline health panel (ops view, not trading UI)

### Vetoes
1. Drag-and-drop UI — cosmetic, delays deployment, zero P&L impact
2. Economic calendar — deflects from 85% deployment
3. Complex charting pre-deployment — blocked until RegimeBased live
4. Pair-level visibility before aggregated view
5. Any UI blocking RegimeBased deployment — frontend is a window, not the system
6. MT5 config wizard, broker connection manager, strategy builder, all-pairs browser
7. MCP UI, LLM API settings panel, custom data URL builder
8. Bookmap, Telegram UI, Excel/Google Sheets integration beyond CSV

---

**Status: COMPLETE**
**Next:** Theme 4 — Broker API & MT5/4 Bridge (Q11)
