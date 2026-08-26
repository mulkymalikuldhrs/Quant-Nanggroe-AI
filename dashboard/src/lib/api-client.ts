const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

// ponytail: API key is now injected server-side by middleware (not NEXT_PUBLIC).
// Never read API keys in client code — they'd be bundled into JS.
function defaultHeaders(extra: Record<string, string> = {}): Record<string, string> {
  return { ...extra };
}

// ── Retry configuration ───────────────────────────────────────────

const RETRY_CONFIG = {
  maxRetries: 3,
  baseDelayMs: 500,
  maxDelayMs: 5000,
  // Status codes that should NOT be retried
  nonRetryableStatuses: [400, 401, 403, 404, 405, 422, 429],
};

// ── Request deduplication ─────────────────────────────────────────

const pendingRequests = new Map<string, Promise<unknown>>();

function getRequestKey(endpoint: string, options: RequestInit = {}): string {
  return `${options.method || "GET"}:${endpoint}:${JSON.stringify(options.body || "")}`;
}

// ── Error class ───────────────────────────────────────────────────

export class ApiError extends Error {
  status: number;
  body: unknown;
  retryable: boolean;

  constructor(message: string, status: number, body: unknown, retryable = false) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
    this.retryable = retryable;
  }
}

// ── Delay helper ──────────────────────────────────────────────────

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// ── Core API request with retry ───────────────────────────────────

export async function apiRequest<T>(
  endpoint: string,
  options: RequestOptions = {},
): Promise<T> {
  const {
    method = "GET",
    body,
    headers = {},
    signal,
    retries = RETRY_CONFIG.maxRetries,
    deduplicate = true,
  } = options;

  // Check for duplicate in-flight request
  if (deduplicate && method === "GET") {
    const key = getRequestKey(endpoint, { method, body: undefined });
    const existing = pendingRequests.get(key);
    if (existing) return existing as Promise<T>;
  }

  const config: RequestInit = {
    method,
    headers: { "Content-Type": "application/json", ...defaultHeaders(headers) },
    signal,
  };

  if (body) config.body = JSON.stringify(body);

  const execute = async (attempt: number): Promise<T> => {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 30000);

    // Combine external signal with timeout
    const combinedSignal = signal
      ? combineAbortSignals(signal, controller.signal)
      : controller.signal;
    config.signal = combinedSignal;

    try {
      const response = await fetch(`${API_BASE}${endpoint}`, config);
      clearTimeout(timeout);

      if (!response.ok) {
        const errorBody = await response.json().catch(() => null);

        // Determine if retryable
        const isRetryable =
          attempt < retries &&
          !RETRY_CONFIG.nonRetryableStatuses.includes(response.status) &&
          response.status >= 500;

        let message: string;
        if (response.status === 429) {
          message = "Rate limited. Please wait...";
        } else if (response.status >= 500) {
          message = `Server error (${response.status}). ${isRetryable ? "Retrying..." : ""}`;
        } else if (response.status === 422) {
          const detail = errorBody?.detail
            ? Array.isArray(errorBody.detail)
              ? errorBody.detail.map((d: { msg?: string }) => d.msg || "").join(", ")
              : errorBody.detail
            : "";
          message = `Validation error: ${detail || response.statusText}`;
        } else {
          message = errorBody?.message || `API Error: ${response.status} ${response.statusText}`;
        }

        if (isRetryable) {
          const backoff = Math.min(
            RETRY_CONFIG.baseDelayMs * Math.pow(2, attempt),
            RETRY_CONFIG.maxDelayMs,
          );
          await delay(backoff);
          return execute(attempt + 1);
        }

        throw new ApiError(message, response.status, errorBody, isRetryable);
      }

      // Handle 204 No Content
      if (response.status === 204) {
        return undefined as T;
      }

      return response.json();
    } catch (error) {
      clearTimeout(timeout);

      if (error instanceof ApiError) throw error;

      // Network error — retry if attempts remain
      if (attempt < retries) {
        const backoff = Math.min(
          RETRY_CONFIG.baseDelayMs * Math.pow(2, attempt),
          RETRY_CONFIG.maxDelayMs,
        );
        await delay(backoff);
        return execute(attempt + 1);
      }

      if (error instanceof DOMException && error.name === "AbortError") {
        throw new ApiError("Request timed out after 30s", 0, null, true);
      }

      throw new ApiError(
        error instanceof Error ? error.message : "Network error",
        0,
        null,
        true,
      );
    }
  };

  const key = getRequestKey(endpoint, { method, body: undefined });
  const promise = execute(0);

  if (deduplicate && method === "GET") {
    pendingRequests.set(key, promise);
    promise.finally(() => pendingRequests.delete(key));
  }

  return promise;
}

// ── Combine two AbortSignals ──────────────────────────────────────

function combineAbortSignals(
  s1: AbortSignal,
  s2: AbortSignal,
): AbortSignal {
  if (s1.aborted || s2.aborted) {
    return s1.aborted ? s1 : s2;
  }

  const controller = new AbortController();
  const abort = () => controller.abort();

  s1.addEventListener("abort", abort, { once: true });
  s2.addEventListener("abort", abort, { once: true });

  return controller.signal;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  signal?: AbortSignal;
  retries?: number;
  deduplicate?: boolean;
}

// ════════════════════════════════════════════════════════════════════
//  API Endpoints
// ════════════════════════════════════════════════════════════════════

export const agentsApi = {
  run: (req: AgentRunRequest) =>
    apiRequest<AgentRunResponse>("/api/agents/run", { method: "POST", body: req }),
  getStatus: () =>
    apiRequest<AgentStatusResponse>("/api/agents/status"),
  getDecisions: () =>
    apiRequest<Decision[]>("/api/agents/decisions"),
  activateKillSwitch: (reason: string) =>
    apiRequest<KillSwitchStatusResponse>("/api/agents/kill-switch/activate", {
      method: "POST",
      body: { reason },
    }),
  resetKillSwitch: () =>
    apiRequest<KillSwitchStatusResponse>("/api/agents/kill-switch/reset", {
      method: "POST",
      body: { confirmation: "CONFIRM_RESET_AFTER_REVIEW" },
    }),
};

export const backtestApi = {
  run: (config: BacktestRunRequest) =>
    apiRequest<{ id: string }>("/api/backtest/run", { method: "POST", body: config }),
  getResult: (id: string) =>
    apiRequest<BacktestResult>(`/api/backtest/result/${id}`),
  getStrategies: () =>
    apiRequest<Strategy[]>("/api/backtest/strategies"),
  getEngines: () =>
    apiRequest<string[]>("/api/backtest/engines"),
  getFactors: () =>
    apiRequest<FactorZoo[]>("/api/backtest/factors"),
  // Walk-Forward endpoints
  runWalkForward: (config: WalkForwardRequest) =>
    apiRequest<WalkForwardResult>("/api/backtest/walk-forward", { method: "POST", body: config }),
  batchWalkForward: (config?: { symbol?: string; period?: string }) =>
    apiRequest<BatchWalkForwardResult>("/api/backtest/walk-forward/batch", { method: "POST", body: config || {} }),
  walkForwardStatus: () =>
    apiRequest<WalkForwardStatus>("/api/backtest/walk-forward/status"),
  // Auto-Tune endpoint
  tune: (config: TuneRequest) =>
    apiRequest<TuneResult>("/api/backtest/tune", { method: "POST", body: config }),
  // Evolution endpoint
  evolutionStatus: () =>
    apiRequest<EvolutionStatus>("/api/backtest/evolution/status"),
};

export const tradingApi = {
  placeOrder: (req: PlaceOrderRequest) =>
    apiRequest<PlaceOrderResponse>("/api/trading/order", { method: "POST", body: req }),
  getPositions: () =>
    apiRequest<PositionsResponse>("/api/trading/positions"),
  getOrders: () =>
    apiRequest<Order[]>("/api/trading/orders"),
  cancelOrder: (id: string) =>
    apiRequest<{ success: boolean }>(`/api/trading/order/${id}`, { method: "DELETE" }),
  getExchanges: () =>
    apiRequest<Exchange[]>("/api/trading/exchanges"),
  sliceOrder: (req: {
    symbol: string; side: string; quantity: number;
    algo?: string; duration_minutes?: number; num_slices?: number;
  }) =>
    apiRequest<Record<string, unknown>>("/api/trading/slice-order", { method: "POST", body: req }),
  getHistory: (params?: {
    symbol?: string; date_from?: string; date_to?: string;
    strategy?: string; limit?: number;
  }) => {
    const q = new URLSearchParams();
    if (params?.symbol) q.set("symbol", params.symbol);
    if (params?.date_from) q.set("date_from", params.date_from);
    if (params?.date_to) q.set("date_to", params.date_to);
    if (params?.strategy) q.set("strategy", params.strategy);
    q.set("limit", String(params?.limit ?? 50));
    return apiRequest<TradeHistoryResponse>(`/api/trading/history?${q.toString()}`);
  },
  getTradeDetail: (id: string) =>
    apiRequest<TradeDetail>(`/api/trading/history/${id}`),
};

export const marketApi = {
  getPrice: (symbol: string) =>
    apiRequest<PriceResponse>(`/api/market/price/${symbol}`),
  getSentiment: () =>
    apiRequest<MarketSentiment>("/api/market/sentiment"),
  getCandles: (symbol: string) =>
    apiRequest<CandleStick[]>(`/api/market/candles/${symbol}`),
  getSignals: () =>
    apiRequest<TradingSignal[]>("/api/market/signals"),
  getOrderBook: (symbol: string, limit: number = 20) =>
    apiRequest<OrderBookResponse>(`/api/market/orderbook/${symbol}?limit=${limit}`),
};

export const portfolioApi = {
  getSummary: () =>
    apiRequest<PortfolioSummary>("/api/portfolio/summary"),
  getPerformance: () =>
    apiRequest<PerformanceMetrics>("/api/portfolio/performance"),
  getEquityCurve: () =>
    apiRequest<EquityCurveResponse>("/api/portfolio/equity-curve"),
  getRisk: () =>
    apiRequest<RiskData>("/api/portfolio/risk"),
  getRiskParity: (targetVol: number = 0.15) =>
    apiRequest<Record<string, number>>(`/api/portfolio/risk-parity?target_vol=${targetVol}`),
};

export const memoryApi = {
  search: (q: string, type?: string) =>
    apiRequest<MemorySearchResponse>(
      `/api/memory/search?q=${encodeURIComponent(q)}${type ? `&type=${type}` : ""}`,
    ),
  store: (req: StoreMemoryRequest) =>
    apiRequest<{ id: string }>("/api/memory/store", { method: "POST", body: req }),
  getEntry: (id: string) =>
    apiRequest<MemoryEntry>(`/api/memory/entry/${id}`),
  deleteEntry: (id: string) =>
    apiRequest<{ success: boolean }>(`/api/memory/entry/${id}`, { method: "DELETE" }),
};

export const colonyApi = {
  list: () =>
    apiRequest<Colony[]>("/api/colony/list"),
  getDetail: (id: string) =>
    apiRequest<ColonyDetail>(`/api/colony/${id}`),
  create: (req: ColonyCreateRequest) =>
    apiRequest<Colony>("/api/colony/create", { method: "POST", body: req }),
  runTask: (id: string, task: string) =>
    apiRequest<{ result: string }>(`/api/colony/${id}/run`, { method: "POST", body: { task } }),
};

export const monitorApi = {
  getSummary: () => apiRequest<Record<string, unknown>>("/api/monitor/summary"),
  getHealth: () => apiRequest<Record<string, unknown>>("/api/monitor/health"),
  getMetrics: () => apiRequest<Record<string, unknown>>("/api/monitor/metrics"),
  getPnl: () => apiRequest<Record<string, unknown>>("/api/monitor/pnl"),
  getRegime: () => apiRequest<Record<string, unknown>>("/api/monitor/regime"),
  getRisk: () => apiRequest<Record<string, unknown>>("/api/monitor/risk"),
};

export const channelsApi = {
  list: () =>
    apiRequest<Channel[]>("/api/channels/list"),
  sendMessage: (channelId: string, content: string) =>
    apiRequest<{ success: boolean }>(`/api/channels/${channelId}/send`, {
      method: "POST",
      body: { content },
    }),
  updateConfig: (channelId: string, config: Record<string, string>) =>
    apiRequest<{ success: boolean }>(`/api/channels/${channelId}/config`, {
      method: "PUT",
      body: config,
    }),
};

export const securityApi = {
  getEvents: () =>
    apiRequest<SecurityEvent[]>("/api/security/events"),
  getStatus: () =>
    apiRequest<SecurityStatus>("/api/security/status"),
};

export const toolsApi = {
  list: () =>
    apiRequest<Tool[]>("/api/tools/list"),
  execute: (toolId: string, params: Record<string, unknown>) =>
    apiRequest<ExecuteToolResponse>(`/api/tools/${toolId}/execute`, {
      method: "POST",
      body: { toolId, params },
    }),
};

export const brokersApi = {
  list: () =>
    apiRequest<BrokerListResponse>("/api/brokers/"),
  account: (name: string) =>
    apiRequest<MT5AccountInfo>(`/api/brokers/${name}/account`),
  positions: (name: string) =>
    apiRequest<BrokerPositionsResponse>(`/api/brokers/${name}/positions`),
  portfolio: (name: string) =>
    apiRequest<Record<string, unknown>>(`/api/brokers/${name}/portfolio`),
  placeOrder: (name: string, order: Record<string, unknown>) =>
    apiRequest<Record<string, unknown>>(`/api/brokers/${name}/order`, {
      method: "POST",
      body: order,
    }),
  register: (acc: Record<string, unknown>) =>
    apiRequest<Record<string, unknown>>("/api/brokers/register", {
      method: "POST",
      body: acc,
    }),
  // GATE-6: multi-account (all logged-in MT5 terminals + all-ever-connected)
  accounts: () =>
    apiRequest<{ accounts: Array<{ login: number; server: string; name: string; equity: number; balance: number; currency: string; terminal_path: string }>; count: number }>("/api/trading/accounts"),
  ledger: () =>
    apiRequest<LedgerResponse>("/api/accounts/ledger"),
};

export const schedulerApi = {
  getStatus: () =>
    apiRequest<SchedulerStatus>("/api/scheduler/status"),
  start: (intervalMinutes?: number, symbols?: string[]) =>
    apiRequest<SchedulerStatus>("/api/scheduler/start", {
      method: "POST",
      body: { interval_minutes: intervalMinutes, symbols },
    }),
  stop: () =>
    apiRequest<SchedulerStatus>("/api/scheduler/stop", { method: "POST" }),
  triggerCycle: (symbols?: string[]) =>
    apiRequest<PipelineCycleResult>("/api/scheduler/cycle", {
      method: "POST",
      body: { symbols },
    }),
};

export interface SchedulerStatus {
  running: boolean;
  interval_minutes?: number;
  symbols?: string[];
  error?: string;
}

export interface PipelineCycleResult {
  total: number;
  success_count: number;
  results: Array<{
    symbol: string;
    success: boolean;
    signal: string;
    confidence: number;
    reason: string;
  }>;
}

export default apiRequest;

// ── Types ────────────────────────────────────────────────────────────

export type OrderSide = "buy" | "sell";
export type OrderType = "market" | "limit" | "stop" | "stop_limit" | "oco" | "oto";
export type OrderStatus = "pending" | "filled" | "active" | "canceled" | "rejected";
export type AgentStatus = "active" | "idle" | "warning" | "error" | "paused";
export type AgentEmotion =
  | "curious" | "focused" | "confident" | "cautious"
  | "analytical" | "patient" | "excited" | "alert"
  | "thoughtful" | "neutral" | "decisive";
export type ExchangeType = "Equity" | "Crypto" | "Prediction" | "DeFi";
export type ExchangeStatus = "connected" | "disconnected" | "degraded";
export type ProviderStatus = "connected" | "disconnected" | "degraded";
export type ColonyStatus = "active" | "idle" | "degraded";
export type MemoryEntryType = "knowledge" | "session" | "vector" | "condenser" | "paging";
export type DecisionImpact = "high" | "medium" | "low";
export type RiskCheckStatus = "pass" | "warning" | "fail";

// ── Market Types ─────────────────────────────────────────────────────
export interface MarketSymbol { symbol: string; price: number; change: number; volume: string; }
export interface SectorSentiment { name: string; sentiment: number; }
export interface MarketSentiment { overall: number; fear_greed: number; sectors: SectorSentiment[]; }
export interface PriceResponse { symbol: string; price: number; change: number; changePercent: number; timestamp: string; }
export interface CandleStick { time: string; open: number; high: number; low: number; close: number; }
export interface TradingSignal { id: number; time: string; agent: string; symbol: string; signal: "BUY" | "SELL" | "HOLD"; confidence: number; reason: string; price: number; change_pct: number; volume: number; }

// ── Trading Types ────────────────────────────────────────────────────
export interface Order { id: string; symbol: string; side: OrderSide; type: OrderType; quantity: number; price: number; status: OrderStatus; time: string; exchange: string; }
export interface PlaceOrderRequest { symbol: string; side: OrderSide; type: OrderType; quantity: number; price?: number; stopPrice?: number; exchange?: string; }
export interface PlaceOrderResponse { orderId: string; status: OrderStatus; message: string; }
export interface Position { symbol: string; name: string; quantity: number; avgPrice: number; currentPrice: number; pnl: number; pnlPercent: number; weight: number; side: "long" | "short"; }
export interface PositionsResponse { positions: Position[]; }
export interface Exchange { id: string; name: string; type: ExchangeType; status: ExchangeStatus; }

// ── Agent Types ──────────────────────────────────────────────────────
export interface Agent { id: string; name: string; status: AgentStatus; emotion: AgentEmotion; action: string; lastDecision: string; icon: string; type?: string; }
export interface KillSwitchStatusResponse {
  is_active: boolean;
  activated_at: string | null;
  activation_reason: string | null;
  auto_triggers?: number;
  manual_triggers?: number;
  total_resets?: number;
  message: string;
}
export interface AgentRunRequest { symbol: string; agentId?: string; }
export interface AgentRunResponse { success: boolean; result: string; agentId: string; }
export interface AgentStatusResponse { agents: Agent[]; kill_switch_active: boolean; }
export interface Decision { id: number; time: string; agent: string; decision: string; impact: DecisionImpact; }

// ── Backtest Types ───────────────────────────────────────────────────
export interface EquityCurvePoint { date: string; value: number; }
export interface DrawdownCurvePoint { date: string; value: number; }
export interface MonteCarloResult { simulations: number; meanReturn: number; p5Return: number; p95Return: number; worstCase: number; bestCase: number; }
export interface BacktestResult { id: string; strategy: string; symbol: string; startDate: string; endDate: string; initialCapital: number; finalValue: number; totalReturn: number; sharpe: number; maxDrawdown: number; winRate: number; totalTrades: number; equityCurve: EquityCurvePoint[]; drawdownCurve: DrawdownCurvePoint[]; monteCarlo: MonteCarloResult; }
export interface BacktestRunRequest { strategy?: string; symbol?: string; startDate?: string; endDate?: string; initialCapital?: number; engine?: string; factors?: string[]; }
export interface Strategy { id: string; name: string; description: string; category: string; asset_classes: string[]; timeframes: string[]; enabled: boolean; backtest?: { btc_return?: number; btc_sharpe?: number; eur_return?: number; eur_sharpe?: number; verdict?: string; reason?: string }; }
export interface FactorZoo { name: string; count: number; description: string; }

// ── Portfolio Types ──────────────────────────────────────────────────
export interface PortfolioPosition { symbol: string; name: string; quantity: number; avgPrice: number; currentPrice: number; pnl: number; pnlPercent: number; weight: number; side: "long" | "short"; }
export interface AllocationBucket { name: string; value: number; color: string; }
export interface PortfolioSummary { totalValue: number; dayPnl: number; dayPnlPercent: number; totalPnl: number; totalPnlPercent: number; cashBalance: number; investedAmount: number; positions: PortfolioPosition[]; allocation: AllocationBucket[]; }
export interface PerformanceMetrics { sharpe: number; sortino: number; calmar: number; maxDrawdown: number; winRate: number; profitFactor: number; avgWin: number; avgLoss: number; totalTrades: number; avgHoldingPeriod: string; }
export interface EquityCurveResponse { points: EquityCurvePoint[]; }
export interface RiskCheck { id: number; name: string; status: RiskCheckStatus; value: string; limit: string; }
export interface RiskData { var95: number; var99: number; cvar95: number; maxDrawdown: number; currentDrawdown: number; kellyFraction: number; riskScore: number; checks: RiskCheck[]; correlationMatrix: number[][]; correlationLabels: string[]; }

// ── Memory Types ─────────────────────────────────────────────────────
export interface MemoryEntry { id: string; type: MemoryEntryType; key: string; content: string; timestamp: number; relevance: number; }
export interface StoreMemoryRequest { key: string; type: MemoryEntryType; content: string; }
export interface MemorySearchResponse { entries: MemoryEntry[]; total: number; }

// ── Other Types ──────────────────────────────────────────────────────
export interface DataProvider { name: string; status: ProviderStatus; type: string; latency: string; }
export interface Colony { id: string; name: string; status: ColonyStatus; health: number; agents: number; capacity: number; schedule: string; }
export interface ColonyAgent { id: string; name: string; role: string; type: string; status: AgentStatus; lastActive: string; }
export interface ColonyDetail extends Colony { memberAgents: ColonyAgent[]; topology: string; }
export interface ColonyCreateRequest { name: string; description?: string; capacity?: number; schedule?: string; }
export interface Channel { id: string; name: string; type: string; status: string; config: Record<string, string>; messages: number; }
export interface SecurityEvent { id: string; type: string; severity: string; message: string; timestamp: string; detail: string; agent: string; }
export interface SecurityStatus { sandboxRunning: boolean; permissions: number; activeRules: number; }
export interface Tool { id: string; name: string; description: string; status: string; category: string; executions: number; lastUsed: string; }

// ── Brokers (multi-account MT5: Exness / Valutrades / etc) ────────
export interface BrokerAccount { name: string; role: string; connected: boolean; healthy: boolean; state: string; }
export interface BrokerListResponse { accounts: BrokerAccount[]; count: number; }
export interface BrokerPosition { symbol: string; side: string; quantity: number; entry_price: number; current_price: number; unrealized_pnl: number; }
export interface BrokerPositionsResponse { account: string; positions: BrokerPosition[]; }
export interface MT5AccountInfo { login: number; balance: number; equity: number; margin: number; margin_free: number; margin_level: number; server: string; currency: string; leverage: number; }

// ── Account Ledger (GATE-6: all-ever-connected MT5 accounts) ──────
export interface LedgerAccount {
  login: number; name: string; server: string; group: string;
  first_seen: string; last_seen: string; total_trades: number;
  total_pnl: number; status: string;
}
export interface LedgerResponse { accounts: LedgerAccount[]; count: number; }
export interface OrderBookLevel {
  price: number;
  quantity: number;
  total: number | null;
}

export interface OrderBookResponse {
  symbol: string;
  exchange: string;
  bids: OrderBookLevel[];
  asks: OrderBookLevel[];
  bid_depth: number;
  ask_depth: number;
  spread: number;
  spread_pct: number;
  mid_price: number;
  timestamp: string;
  source: string;
}

export interface TradeDetail {
  id: string;
  ticket: number | null;
  symbol: string;
  side: "buy" | "sell";
  volume: number;
  entry_price: number;
  exit_price: number;
  entry_time: string;
  exit_time: string;
  pnl: number;
  pnl_pct: number | null;
  commission: number;
  swap: number;
  strategy: string | null;
  broker: string | null;
  comment: string | null;
}

export interface TradeHistoryResponse {
  trades: TradeDetail[];
  total_count: number;
  limit: number;
  filters: Record<string, unknown>;
}

export interface ExecuteToolResponse { success: boolean; result: string; }

// ── Config API (dynamic settings) ──────────────────────────────────

// ── Walk-Forward Types ─────────────────────────────────────────────
export interface WalkForwardRequest {
  strategy: string;
  symbol?: string;
  period?: string;
  mode?: "rolling" | "anchored" | "cpcv";
  train_window?: number;
  test_window?: number;
}
export interface WalkForwardFold {
  fold: number;
  train_start: string;
  train_end: string;
  test_start: string;
  test_end: string;
  is_sharpe: number;
  oos_sharpe: number;
  is_return: number;
  oos_return: number;
  is_max_dd: number;
  oos_max_dd: number;
}
export interface WalkForwardResult {
  strategy: string;
  mode: string;
  n_folds: number;
  folds: WalkForwardFold[];
  aggregate: {
    mean_is_sharpe: number;
    mean_oos_sharpe: number;
    std_oos_sharpe: number;
    mean_oos_return: number;
    degradation_ratio: number;
  };
  stability: {
    sharpe_stability: number;
    return_stability: number;
    decay_score: number;
    overall_stability: number;
  };
}
export interface BatchWalkForwardResult {
  total: number;
  validated: number;
  results: Array<{
    strategy: string;
    n_folds: number;
    mean_oos_sharpe: number;
    mean_oos_return: number;
    decayed: boolean;
  }>;
}
export interface WalkForwardStatus {
  total_strategies: number;
  validated_count: number;
  decayed_count: number;
  strategies: Array<{
    name: string;
    n_validations: number;
    best_oos_sharpe: number;
    avg_oos_sharpe: number;
    decay_count: number;
  }>;
}
export interface TuneRequest {
  strategy: string;
  symbol?: string;
  period?: string;
  param_grid?: Record<string, unknown>;
  n_windows?: number;
  top_n?: number;
}
export interface TuneResult {
  strategy: string;
  n_evaluated: number;
  n_windows: number;
  results: Array<{
    params: Record<string, unknown>;
    sharpe: number;
    return_pct: number;
    max_dd: number;
    win_rate: number;
  }>;
}
export interface EvolutionStatus {
  enabled: boolean;
  total_attempts: number;
  accepted: number;
  rejected: number;
  acceptance_rate: number;
  last_attempts: Array<{
    strategy: string;
    timestamp: string;
    baseline_sharpe: number;
    mutated_sharpe: number;
    accepted: boolean;
  }>;
}

export interface StrategyPerformance {
  winRate: number;
  sharpe: number;
  totalPnl: number;
  trades: number;
  period: string;
}

export interface StrategyComparison {
  strategies: Strategy[];
  metrics: Record<string, Record<string, number>>;
}

export const strategiesApi = {
  toggle: (id: string) =>
    apiRequest<{ success: boolean }>(`/api/strategies/${id}/toggle`, { method: "PUT" }),
  updateParams: (id: string, params: Record<string, unknown>) =>
    apiRequest<{ success: boolean }>(`/api/strategies/${id}/params`, { method: "PUT", body: params }),
  performance: (id: string) =>
    apiRequest<StrategyPerformance>(`/api/strategies/${id}/performance`),
  compare: (ids: string[]) =>
    apiRequest<StrategyComparison>(`/api/strategies/compare`, { method: "POST", body: { ids } }),
};

export const evolutionApi = {
  status: () =>
    apiRequest<EvolutionApiResponse<EvolutionStats>>("/api/evolution/status"),
  strategies: (limit = 50) =>
    apiRequest<EvolutionApiResponse<StrategySnapshot[]>>(`/api/evolution/strategies?limit=${limit}`),
  trades: (limit = 20) =>
    apiRequest<EvolutionApiResponse<ClosedTrade[]>>(`/api/evolution/trades?limit=${limit}`),
  config: () =>
    apiRequest<EvolutionApiResponse<Record<string, unknown>>>("/api/evolution/config"),
  updateConfig: (key: string, value: string) =>
    apiRequest<{ success: boolean }>(`/api/evolution/config?key=${encodeURIComponent(key)}&value=${encodeURIComponent(value)}`, { method: "POST" }),
};

export const configApi = {
  getConfig: () =>
    apiRequest<Record<string, unknown>>("/api/credentials"),
  updateConfig: (data: Record<string, unknown>) =>
    apiRequest<{ success: boolean }>("/api/credentials", { method: "PUT", body: data }),
};

export interface ConfigFileMeta {
  name: string; description: string; kind: string; editable: boolean;
  exists: boolean; size: number; modified: number | null; path: string;
}
export interface ConfigFileContent {
  name: string; exists: boolean; raw: string; parsed: unknown; kind: string;
}
export const configFilesApi = {
  list: () =>
    apiRequest<{ files: ConfigFileMeta[] }>("/api/config/files"),
  read: (name: string) =>
    apiRequest<ConfigFileContent>(`/api/config/files/${encodeURIComponent(name)}`),
  write: (name: string, body: { raw?: string; data?: unknown }) =>
    apiRequest<ConfigFileContent>(`/api/config/files/${encodeURIComponent(name)}`, {
      method: "PUT",
      body,
    }),
};

// ── Evolution Types ──────────────────────────────────────────────────

export interface EvolutionApiResponse<T> {
  success: boolean;
  data: T;
}

export interface EvolutionStats {
  total_trades: number;
  active_strategies: number;
  disabled_count: number;
  last_run: string | null;
  total_pnl: number;
}

export interface StrategySnapshot {
  id: number;
  run_id: number;
  strategy_name: string;
  timeframe: string | null;
  sharpe: number | null;
  sortino: number | null;
  win_rate: number | null;
  profit_factor: number | null;
  max_drawdown: number | null;
  avg_return: number | null;
  trade_count: number;
  action: string | null;
  action_reason: string | null;
  run_timestamp: string | null;
  run_trigger: string | null;
}

export interface ClosedTrade {
  id: number;
  timestamp: string;
  symbol: string;
  strategy: string;
  timeframe: string | null;
  direction: string;
  entry_price: number | null;
  exit_price: number | null;
  pnl: number | null;
  pnl_pct: number | null;
  hold_hours: number | null;
}
