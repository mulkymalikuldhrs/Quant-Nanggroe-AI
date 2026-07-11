/**
 * Quant Nanggroe AI — Comprehensive API Client
 * Connects to the FastAPI backend at port 8000 via the Caddy gateway.
 */

const API_BASE = "/api";
const BACKEND_PORT = "8000";

interface RequestOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  timeout?: number;
}

class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(`API Error ${status}: ${detail}`);
    this.status = status;
    this.detail = detail;
  }
}

class ApiClient {
  private async request<T>(
    endpoint: string,
    options: RequestOptions = {}
  ): Promise<T> {
    const { method = "GET", body, headers = {}, timeout = 30000 } = options;

    const separator = endpoint.includes("?") ? "&" : "?";
    const url = `${API_BASE}${endpoint}${separator}XTransformPort=${BACKEND_PORT}`;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    const config: RequestInit = {
      method,
      headers: {
        "Content-Type": "application/json",
        ...headers,
      },
      signal: controller.signal,
    };

    if (body) {
      config.body = JSON.stringify(body);
    }

    try {
      const response = await fetch(url, config);
      clearTimeout(timeoutId);

      if (!response.ok) {
        let detail = response.statusText;
        try {
          const errBody = await response.json();
          detail = errBody.detail || errBody.message || response.statusText;
        } catch {
          // ignore json parse error
        }
        throw new ApiError(response.status, detail);
      }

      // Handle 204 No Content
      if (response.status === 204) {
        return {} as T;
      }

      return response.json();
    } catch (error) {
      clearTimeout(timeoutId);
      if (error instanceof ApiError) throw error;
      if ((error as Error).name === "AbortError") {
        throw new ApiError(408, "Request timeout");
      }
      console.error(`API request failed: ${endpoint}`, error);
      throw error;
    }
  }

  // ══════════════════════════════════════════════════════════════════════
  // Health / System
  // ══════════════════════════════════════════════════════════════════════

  async getHealth() {
    return this.request<{
      status: string;
      service: string;
      database?: string;
      redis?: string;
    }>("/health");
  }

  // ══════════════════════════════════════════════════════════════════════
  // Agents
  // ══════════════════════════════════════════════════════════════════════

  async getAgentStatus() {
    return this.request<{
      agents: Array<{
        name: string;
        role: string;
        registered: boolean;
      }>;
      active: boolean;
      kill_switch_active: boolean;
    }>("/agents/status");
  }

  async runAgent(data: { symbol: string; query?: string; timeframe?: string }) {
    return this.request<{
      status: string;
      symbol: string;
      query: string;
      agent_trace: Array<{
        agent: string;
        content: string;
        confidence: number;
        success: boolean;
      }>;
      decision_action: string;
      risk_verdict: string;
      strategy_signal: string;
      error: string | null;
    }>("/agents/run", { method: "POST", body: data });
  }

  async getKillSwitchStatus() {
    return this.request<{
      is_active: boolean;
      activated_at: string | null;
      activation_reason: string | null;
      auto_triggers: number;
      manual_triggers: number;
      total_resets: number;
      message: string;
    }>("/agents/kill-switch/status");
  }

  async activateKillSwitch(reason: string = "MANUAL") {
    return this.request<{
      is_active: boolean;
      message: string;
    }>("/agents/kill-switch/activate", {
      method: "POST",
      body: { reason },
    });
  }

  async resetKillSwitch() {
    return this.request<{
      is_active: boolean;
      message: string;
    }>("/agents/kill-switch/reset", {
      method: "POST",
      body: { confirmation: "CONFIRM" },
    });
  }

  // ══════════════════════════════════════════════════════════════════════
  // Market Data
  // ══════════════════════════════════════════════════════════════════════

  async getPrice(symbol: string) {
    return this.request<{
      symbol: string;
      price: number | null;
      timestamp: string;
    }>(`/market/price/${encodeURIComponent(symbol)}`);
  }

  async getOHLCV(data: {
    symbol: string;
    timeframe?: string;
    limit?: number;
  }) {
    return this.request<{
      symbol: string;
      timeframe: string;
      data: Array<{
        timestamp: string;
        open: number;
        high: number;
        low: number;
        close: number;
        volume: number;
      }>;
      count: number;
    }>("/market/ohlcv", { method: "POST", body: data });
  }

  async detectRegime(data: {
    symbol: string;
    price_change_5d?: number;
    price_change_1d?: number;
    adx?: number;
    rsi?: number;
    atr_pct?: number;
    volume_ratio?: number;
    ema_trend?: string;
  }) {
    return this.request<{
      symbol: string;
      regime: string;
      base_regime: string;
      volatility: string;
      liquidity: string;
      no_trade_reasons: string[];
      trade_allowed: boolean;
      inputs: Record<string, unknown>;
    }>("/market/regime", { method: "POST", body: data });
  }

  async getPressure(symbol: string) {
    return this.request<{
      symbol: string;
      buy_pressure: number;
      sell_pressure: number;
      bid_volume: number;
      ask_volume: number;
      spread: number;
      mid_price: number;
      verdict: string;
      timestamp: string;
    }>(`/market/pressure/${encodeURIComponent(symbol)}`);
  }

  // ══════════════════════════════════════════════════════════════════════
  // Trading
  // ══════════════════════════════════════════════════════════════════════

  async placeOrder(data: {
    symbol: string;
    direction: string;
    quantity: number;
    order_type?: string;
    price?: number;
    stop_loss?: number;
    take_profit?: number;
  }) {
    return this.request<{
      order_id: string;
      status: string;
      symbol: string;
      direction: string;
      quantity: number;
      filled_price: number | null;
      timestamp: string;
    }>("/trading/order", { method: "POST", body: data });
  }

  async getPositions() {
    return this.request<{
      positions: Array<{
        ticker: string;
        amount: number;
        avg_price: number;
        current_price: number;
        pnl: number;
        last_updated: string;
      }>;
      total_count: number;
    }>("/trading/positions");
  }

  async getTradeHistory(limit: number = 50) {
    return this.request<{
      trades: Array<{
        id: string;
        timestamp: string;
        ticker: string;
        action: string;
        amount: number;
        price: number;
        total_value: number;
        fees: number;
        realized_pnl: number | null;
      }>;
      total_count: number;
      limit: number;
    }>(`/trading/trades?limit=${limit}`);
  }

  async riskCheck(data: {
    symbol: string;
    direction: string;
    entry: number;
    lot_size?: number;
    stop_loss?: number;
    take_profit?: number;
    account_balance?: number;
  }) {
    return this.request<{
      symbol: string;
      direction: string;
      lot_size: number;
      entry: number;
      stop_loss: number | null;
      take_profit: number | null;
      risk_pct: number;
      rr_ratio: number;
      verdict: string;
      checkpoints: Record<
        string,
        { name: string; value: string; limit: string; passed: boolean }
      >;
      veto_count_total: number;
      approval_count_total: number;
    }>("/trading/risk-check", { method: "POST", body: data });
  }

  // ══════════════════════════════════════════════════════════════════════
  // Portfolio
  // ══════════════════════════════════════════════════════════════════════

  async getPortfolioSummary() {
    return this.request<{
      total_value: number;
      unrealized_pnl: number;
      realized_pnl: number;
      positions: Array<{
        ticker: string;
        amount: number;
        avg_price: number;
        current_price: number;
        pnl: number;
      }>;
      position_count: number;
      cash_balance: number;
      timestamp: string;
    }>("/portfolio/summary");
  }

  async getPortfolioRisk() {
    return this.request<{
      var_95: number;
      cvar_95: number;
      max_drawdown: number;
      current_drawdown: number;
      sharpe_ratio: number;
      sortino_ratio: number;
      daily_pnl_pct: number;
      weekly_pnl_pct: number;
      daily_trades: number;
      risk_status: string;
      timestamp: string;
    }>("/portfolio/risk");
  }

  async runStressTest() {
    return this.request<{
      scenarios: Record<
        string,
        {
          description: string;
          portfolio_value_pre: number;
          estimated_loss: number;
          loss_pct: number;
          portfolio_value_post: number;
          p95_loss: number;
          p99_loss: number;
          position_impacts: Record<
            string,
            {
              pre_shock_value: number;
              estimated_loss: number;
              post_shock_value: number;
              loss_pct: number;
            }
          >;
        }
      >;
      summary: {
        portfolio_value: number;
        worst_scenario: string;
        worst_case_loss_pct: number;
        total_scenarios: number;
      };
      timestamp: string;
    }>("/portfolio/stress-test");
  }

  // ══════════════════════════════════════════════════════════════════════
  // Backtest
  // ══════════════════════════════════════════════════════════════════════

  async submitBacktest(data: {
    symbol: string;
    strategy: string;
    start_date: string;
    end_date: string;
    initial_capital?: number;
    commission?: number;
    slippage?: number;
    position_sizing?: string;
  }) {
    return this.request<{
      backtest_id: string;
      status: string;
      symbol: string;
      strategy: string;
      message: string;
    }>("/backtest/run", { method: "POST", body: data });
  }

  async getBacktestResult(backtestId: string) {
    return this.request<{
      backtest_id: string;
      status: string;
      symbol: string;
      strategy: string;
      total_return: number;
      sharpe_ratio: number;
      max_drawdown: number;
      win_rate: number;
      total_trades: number;
      profit_factor: number;
      avg_trade_pnl: number;
      avg_win: number;
      avg_loss: number;
      equity_curve: number[];
      error: string | null;
    }>(`/backtest/result/${backtestId}`);
  }

  async listBacktests() {
    return this.request<{
      backtests: Array<{
        id: string;
        status: string;
        symbol: string;
        strategy: string;
      }>;
      total: number;
    }>("/backtest/list");
  }

  // ══════════════════════════════════════════════════════════════════════
  // Memory
  // ══════════════════════════════════════════════════════════════════════

  async searchMemory(query: string) {
    return this.request<unknown[]>(
      `/memory/search?q=${encodeURIComponent(query)}`
    );
  }

  async storeMemory(data: { key: string; value: string; category?: string }) {
    return this.request<unknown>("/memory/store", { method: "POST", body: data });
  }
}

export const apiClient = new ApiClient();
export { ApiError };
