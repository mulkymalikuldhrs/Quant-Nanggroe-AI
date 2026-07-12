// Live proxy mock-data — fetches from real API, falls back to inline defaults.
// ALL 14 dashboard pages continue to import from this file — zero page changes.
// Uses Proxy so all property reads forward to the current (possibly API-refreshed) value.

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Proxy helper ─────────────────────────────────────────────────────────
function live<T extends object>(defaults: T, endpoint: string, mapper?: (d: unknown) => T): T {
  let value = defaults;
  fetch(`${API_BASE}${endpoint}`)
    .then((r) => (r.ok ? r.json() : null))
    .then((d) => { if (d != null) value = mapper ? mapper(d) : (d as T); })
    .catch(() => {});
  return new Proxy(defaults, {
    get(target, prop: string | symbol) { return (value as Record<string | symbol, unknown>)[prop]; },
    set(target, prop: string | symbol, v) { (value as Record<string | symbol, unknown>)[prop] = v; return true; },
    has(target, prop: string | symbol) { return prop in value; },
    ownKeys() { return Reflect.ownKeys(value); },
    getOwnPropertyDescriptor(target, prop: string | symbol) { return Object.getOwnPropertyDescriptor(value, prop); },
  }) as T;
}

// ── Helpers ──────────────────────────────────────────────────────────────
const pick = <T, K extends keyof T>(...keys: K[]) => (obj: T) => {
  const out: Partial<T> = {};
  keys.forEach((k) => (out[k] = obj[k]));
  return out as Pick<T, K>;
};

const defaultAgents = [
  { id: "research", name: "Research Agent", status: "active", emotion: "curious", action: "Scanning SEC filings for AAPL", lastDecision: "Buy signal on AAPL", icon: "🔍" },
  { id: "market_intel", name: "Market Intelligence", status: "active", emotion: "focused", action: "Monitoring order flow", lastDecision: "High buy pressure detected", icon: "📊" },
  { id: "portfolio", name: "Portfolio Manager", status: "active", emotion: "confident", action: "Rebalancing positions", lastDecision: "Reduce NVDA to 8%", icon: "💼" },
  { id: "risk", name: "Risk Manager", status: "active", emotion: "cautious", action: "Running VaR calculations", lastDecision: "Portfolio within risk limits", icon: "🛡️" },
  { id: "strategy", name: "Strategy Agent", status: "active", emotion: "analytical", action: "Optimizing factor weights", lastDecision: "Momentum + Value combo best", icon: "🎯" },
  { id: "execution", name: "Execution Agent", status: "idle", emotion: "patient", action: "Awaiting order signals", lastDecision: "TWAP execution complete", icon: "⚡" },
  { id: "crypto", name: "Crypto Specialist", status: "active", emotion: "excited", action: "Analyzing BTC on-chain data", lastDecision: "BTC accumulation phase", icon: "₿" },
  { id: "forex", name: "Forex Specialist", status: "warning", emotion: "alert", action: "Monitoring EUR/USD spread", lastDecision: "Spread widening on NFP", icon: "💱" },
  { id: "macro", name: "Macro Analyst", status: "active", emotion: "thoughtful", action: "Processing FOMC minutes", lastDecision: "Hawkish tilt expected", icon: "🌍" },
  { id: "prediction", name: "Prediction Market", status: "idle", emotion: "neutral", action: "Scanning Polymarket odds", lastDecision: "72% chance rate hold", icon: "🔮" },
  { id: "trader", name: "Trader Agent", status: "active", emotion: "decisive", action: "Placing stop-loss orders", lastDecision: "SL set at -2% for TSLA", icon: "📈" },
];

const defaultPortfolio = {
  totalValue: 284750.32, dayPnl: 3241.56, dayPnlPercent: 1.15, totalPnl: 34750.32,
  totalPnlPercent: 13.9, cashBalance: 42850.0, investedAmount: 241900.32,
  positions: [
    { symbol: "AAPL", name: "Apple Inc.", quantity: 50, avgPrice: 178.5, currentPrice: 189.84, pnl: 566.7, pnlPercent: 6.35, weight: 3.33, side: "long" },
    { symbol: "NVDA", name: "NVIDIA Corp.", quantity: 25, avgPrice: 450.2, currentPrice: 875.28, pnl: 10627.0, pnlPercent: 94.4, weight: 7.68, side: "long" },
    { symbol: "BTC", name: "Bitcoin", quantity: 0.85, avgPrice: 42500, currentPrice: 67250.5, pnl: 21012.93, pnlPercent: 58.27, weight: 20.04, side: "long" },
    { symbol: "ETH", name: "Ethereum", quantity: 5.2, avgPrice: 2300, currentPrice: 3520.8, pnl: 6348.16, pnlPercent: 53.18, weight: 6.43, side: "long" },
    { symbol: "SPY", name: "S&P 500 ETF", quantity: 30, avgPrice: 480.5, currentPrice: 528.75, pnl: 1447.5, pnlPercent: 10.04, weight: 5.57, side: "long" },
    { symbol: "TSLA", name: "Tesla Inc.", quantity: 15, avgPrice: 245.8, currentPrice: 178.35, pnl: -1011.75, pnlPercent: -27.43, weight: 0.94, side: "long" },
    { symbol: "EUR/USD", name: "Euro/US Dollar", quantity: 10000, avgPrice: 1.085, currentPrice: 1.0872, pnl: 22.0, pnlPercent: 0.2, weight: 3.81, side: "long" },
    { symbol: "SOL", name: "Solana", quantity: 40, avgPrice: 95.5, currentPrice: 148.32, pnl: 2112.8, pnlPercent: 55.32, weight: 2.08, side: "long" },
  ],
  allocation: [
    { name: "Crypto", value: 35, color: "#f59e0b" }, { name: "Equities", value: 30, color: "#10b981" },
    { name: "ETFs", value: 15, color: "#3b82f6" }, { name: "Forex", value: 10, color: "#8b5cf6" },
    { name: "Cash", value: 10, color: "#6b7280" },
  ],
};

const eqCurve = (n: number) => Array.from({ length: n }, (_, i) => {
  const d = new Date(); d.setDate(d.getDate() - (n - 1 - i));
  return { date: d.toISOString().split("T")[0], value: Math.round((250000 + Math.sin(i / 10) * 10000 + i * 400 + Math.random() * 3000) * 100) / 100 };
});
const candles = (n: number) => Array.from({ length: n }, (_, i) => {
  const d = new Date(); d.setDate(d.getDate() - (n - 1 - i));
  const base = 67000 + Math.sin(i / 15) * 3000;
  return { time: d.toISOString().split("T")[0], open: +(base + (Math.random() - 0.5) * 500).toFixed(2), high: +(base + Math.random() * 500).toFixed(2), low: +(base - Math.random() * 500).toFixed(2), close: +(base + (Math.random() - 0.5) * 200).toFixed(2) };
});

// ── Live exports (all 14 dashboard pages read these) ─────────────────────
export const mockAgents = live(defaultAgents, "/api/agents/status");
export const mockPortfolio = live(defaultPortfolio, "/api/portfolio/summary");
export const mockEquityCurve = live(eqCurve(90), "/api/portfolio/equity-curve", (d) => (Array.isArray(d) ? d : eqCurve(90)));
export const mockMarketData = live({
  symbols: [
    { symbol: "BTC", price: 67250.5, change: 2.34, volume: "28.5B" },
    { symbol: "ETH", price: 3520.8, change: 1.87, volume: "15.2B" },
    { symbol: "SPY", price: 528.75, change: 0.42, volume: "89.3M" },
    { symbol: "EUR/USD", price: 1.0872, change: -0.15, volume: "1.2T" },
  ],
  sentiment: { overall: 0.65, fear_greed: 72, sectors: [
    { name: "Technology", sentiment: 0.78 }, { name: "Finance", sentiment: 0.55 },
    { name: "Healthcare", sentiment: 0.62 }, { name: "Energy", sentiment: 0.45 },
    { name: "Crypto", sentiment: 0.82 },
  ]},
}, "/api/market/sentiment");

export const mockRiskData = {
  var95: -4250.32, var99: -8920.15, cvar95: -6830.45, maxDrawdown: -12.3,
  currentDrawdown: -2.1, kellyFraction: 0.18, riskScore: 42,
  checks: [
    { id: 1, name: "Position Size Limit", status: "pass", value: "8% of portfolio", limit: "10%" },
    { id: 2, name: "Sector Concentration", status: "pass", value: "28% tech", limit: "40%" },
    { id: 3, name: "VaR Limit", status: "pass", value: "$4,250", limit: "$10,000" },
    { id: 4, name: "Drawdown Limit", status: "warning", value: "-2.1%", limit: "-5%" },
    { id: 5, name: "Correlation Check", status: "pass", value: "0.45 avg", limit: "0.70" },
    { id: 6, name: "Liquidity Check", status: "pass", value: "85% liquid", limit: "50%" },
    { id: 7, name: "Leverage Limit", status: "pass", value: "1.0x", limit: "2.0x" },
    { id: 8, name: "Emotional Lockout", status: "pass", value: "Calm", limit: "Locked" },
    { id: 9, name: "Kill Switch", status: "pass", value: "Off", limit: "N/A" },
  ],
  correlationMatrix: [
    [1.0, 0.82, 0.45, 0.38, -0.12], [0.82, 1.0, 0.51, 0.42, -0.08],
    [0.45, 0.51, 1.0, 0.28, -0.15], [0.38, 0.42, 0.28, 1.0, -0.05],
    [-0.12, -0.08, -0.15, -0.05, 1.0],
  ],
  correlationLabels: ["BTC", "ETH", "SPY", "AAPL", "EUR/USD"],
};

const defaultEngines = [
  "Equity Engine", "Crypto Engine", "Forex Engine", "Futures Engine",
  "Composite Engine", "Market Detection", "Walk Forward", "Monte Carlo",
  "Mean Variance Optimizer", "Risk Parity Optimizer",
];
export const mockBacktestEngines = live(defaultEngines as unknown[], "/api/backtest/engines", (d) => (Array.isArray(d) ? d : defaultEngines));

export const mockFactorZoos = [
  { name: "Alpha101", count: 101, description: "WorldQuant 101 Alpha factors" },
  { name: "GTJA191", count: 191, description: "Guotai Junan 191 factors" },
  { name: "Qlib158", count: 158, description: "Microsoft Qlib 158 factors" },
  { name: "Barra", count: 10, description: "Barra risk model factors" },
  { name: "Technical", count: 5, description: "Technical analysis factors" },
  { name: "Fundamental", count: 3, description: "Fundamental analysis factors" },
  { name: "Academic", count: 1, description: "Academic research factors" },
];

const defaultExchanges = [
  { id: "alpaca", name: "Alpaca", type: "Equity", status: "connected" },
  { id: "binance", name: "Binance", type: "Crypto", status: "connected" },
  { id: "coinbase", name: "Coinbase", type: "Crypto", status: "connected" },
  { id: "kraken", name: "Kraken", type: "Crypto", status: "disconnected" },
  { id: "bybit", name: "Bybit", type: "Crypto", status: "connected" },
  { id: "okx", name: "OKX", type: "Crypto", status: "connected" },
  { id: "kucoin", name: "KuCoin", type: "Crypto", status: "disconnected" },
  { id: "gate", name: "Gate.io", type: "Crypto", status: "connected" },
  { id: "polymarket", name: "Polymarket", type: "Prediction", status: "connected" },
  { id: "solana", name: "Solana/Jupiter", type: "DeFi", status: "connected" },
];
export const mockExchanges = live(defaultExchanges, "/api/trading/exchanges", (d) => (Array.isArray(d) ? d : defaultExchanges));

export const mockSignals = [
  { id: 1, time: "2m ago", agent: "Research", symbol: "AAPL", signal: "BUY", confidence: 0.85, reason: "Strong earnings beat" },
  { id: 2, time: "5m ago", agent: "Crypto", symbol: "BTC", signal: "HOLD", confidence: 0.72, reason: "Consolidation phase" },
  { id: 3, time: "8m ago", agent: "Risk", symbol: "TSLA", signal: "SELL", confidence: 0.68, reason: "High volatility alert" },
  { id: 4, time: "12m ago", agent: "Strategy", symbol: "NVDA", signal: "BUY", confidence: 0.91, reason: "Momentum breakout" },
  { id: 5, time: "15m ago", agent: "Forex", symbol: "EUR/USD", signal: "HOLD", confidence: 0.55, reason: "Waiting for NFP data" },
  { id: 6, time: "20m ago", agent: "Macro", symbol: "SPY", signal: "BUY", confidence: 0.78, reason: "Fed pivot expected" },
];

const defaultDecisions = [
  { id: 1, time: "1m ago", agent: "Trader", decision: "Placed BUY limit order for NVDA at $870", impact: "high" },
  { id: 2, time: "3m ago", agent: "Risk", decision: "Reduced position size for TSLA to 3%", impact: "medium" },
  { id: 3, time: "7m ago", agent: "Portfolio", decision: "Rebalanced: +2% BTC, -2% AAPL", impact: "medium" },
  { id: 4, time: "12m ago", agent: "Strategy", decision: "Switched to momentum+value hybrid", impact: "high" },
  { id: 5, time: "18m ago", agent: "Crypto", decision: "Set stop-loss for ETH at $3,400", impact: "low" },
];
export const mockRecentDecisions = live(defaultDecisions, "/api/agents/decisions", (d) => (Array.isArray(d) ? d : defaultDecisions));

export const mockPerformanceMetrics = {
  sharpe: 1.84, sortino: 2.31, calmar: 1.56, maxDrawdown: -12.3,
  winRate: 58.2, profitFactor: 1.72, avgWin: 345.6, avgLoss: -201.4,
  totalTrades: 247, avgHoldingPeriod: "3.2 days",
};

export const mockCandlestickData = live(candles(100), "/api/market/candles/BTC", (d) => (Array.isArray(d) ? d : candles(100)));

export const mockBacktestResult = {
  id: "bt_001", strategy: "Momentum Alpha", symbol: "AAPL",
  startDate: "2023-01-01", endDate: "2024-01-01",
  initialCapital: 100000, finalValue: 128450, totalReturn: 28.45,
  sharpe: 1.92, maxDrawdown: -8.7, winRate: 61.5, totalTrades: 156,
  equityCurve: Array.from({ length: 252 }, (_, i) => {
    const d = new Date(2023, 0, 1); d.setDate(d.getDate() + i);
    return { date: d.toISOString().split("T")[0], value: Math.round((100000 + Math.sin(i / 20) * 5000 + i * 110 + Math.random() * 2000) * 100) / 100 };
  }),
  drawdownCurve: Array.from({ length: 252 }, (_, i) => {
    const d = new Date(2023, 0, 1); d.setDate(d.getDate() + i);
    return { date: d.toISOString().split("T")[0], value: -Math.abs(Math.sin(i / 30) * 5 + Math.random() * 3) };
  }),
  monteCarlo: { simulations: 1000, meanReturn: 26.8, p5Return: 12.3, p95Return: 42.1, worstCase: -5.2, bestCase: 58.4 },
};

const defaultStrategies = [
  { id: "strat_1", name: "Momentum Alpha", type: "Momentum", performance: 28.45, sharpe: 1.92, status: "active" },
  { id: "strat_2", name: "Value + Quality", type: "Value", performance: 18.23, sharpe: 1.45, status: "active" },
  { id: "strat_3", name: "Mean Reversion", type: "Statistical", performance: -2.15, sharpe: 0.82, status: "paused" },
  { id: "strat_4", name: "Breakout Scanner", type: "Technical", performance: 35.67, sharpe: 2.15, status: "active" },
  { id: "strat_5", name: "Crypto Momentum", type: "Crypto", performance: 42.1, sharpe: 1.78, status: "active" },
  { id: "strat_6", name: "Forex Carry", type: "Forex", performance: 8.9, sharpe: 1.12, status: "paused" },
];
export const mockStrategies = live(defaultStrategies, "/api/strategy/list", (d) => (Array.isArray(d) ? d : defaultStrategies));

const defaultOrders = [
  { id: "ord_1", symbol: "NVDA", side: "buy", type: "limit", quantity: 10, price: 870.0, status: "pending", time: "2m ago", exchange: "Alpaca" },
  { id: "ord_2", symbol: "BTC", side: "buy", type: "market", quantity: 0.1, price: 67250.5, status: "filled", time: "5m ago", exchange: "Binance" },
  { id: "ord_3", symbol: "TSLA", side: "sell", type: "stop", quantity: 5, price: 175.0, status: "active", time: "15m ago", exchange: "Alpaca" },
  { id: "ord_4", symbol: "ETH", side: "sell", type: "limit", quantity: 1.5, price: 3600.0, status: "pending", time: "22m ago", exchange: "Coinbase" },
  { id: "ord_5", symbol: "SPY", side: "buy", type: "market", quantity: 5, price: 528.75, status: "filled", time: "1h ago", exchange: "Alpaca" },
];
export const mockOrders = live(defaultOrders, "/api/trading/orders", (d) => (Array.isArray(d) ? d : defaultOrders));

export const mockDataProviders = [
  { name: "Alpaca", status: "connected", type: "Market Data", latency: "45ms" },
  { name: "Polygon", status: "connected", type: "Market Data", latency: "32ms" },
  { name: "Yahoo Finance", status: "connected", type: "Historical Data", latency: "120ms" },
  { name: "Binance", status: "connected", type: "Crypto Data", latency: "18ms" },
  { name: "FRED", status: "connected", type: "Economic Data", latency: "250ms" },
  { name: "SEC EDGAR", status: "degraded", type: "Filings Data", latency: "850ms" },
  { name: "CoinGecko", status: "connected", type: "Crypto Data", latency: "95ms" },
  { name: "TwelveData", status: "disconnected", type: "Market Data", latency: "N/A" },
];

export const mockMemoryEntries: { id: string; type: string; content: string; timestamp: string; key: string; relevance: number }[] = [
  { id: "mem_1", type: "decision", content: "Portfolio rebalanced", timestamp: "2026-07-12T10:00:00Z", key: "portfolio.rebalance", relevance: 87 },
];
export const mockSecurityEvents: { id: string; type: string; severity: string; message: string; timestamp: string; detail: string; agent: string }[] = [
  { id: "sec_1", type: "access", severity: "low", message: "API key rotated", timestamp: "2026-07-12T09:00:00Z", detail: "Access key for trading agent was rotated", agent: "trader-alpha" },
];
export const mockTools: { id: string; name: string; description: string; status: string; category: string; executions: number; lastUsed: string }[] = [
  { id: "tool_1", name: "Web Search", description: "Search the web", status: "active", category: "web", executions: 42, lastUsed: "2m ago" },
];
export const mockChannels: { id: string; name: string; type: string; status: string; config: Record<string, string>; messages: number }[] = [
  { id: "discord", name: "Discord", type: "social", status: "connected", config: { webhook: "https://discord.com/api/webhooks/xxx", channel: "#general" }, messages: 128 },
];
export const mockColonies: { id: string; name: string; agents: number; capacity: number; health: number; status: string; schedule: string }[] = [
  { id: "alpha", name: "Alpha Colony", agents: 3, capacity: 10, health: 95, status: "active", schedule: "*/15 * * * *" },
];
