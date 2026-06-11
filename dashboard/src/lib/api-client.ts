const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface RequestOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
}

async function apiRequest<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, headers = {} } = options;

  const config: RequestInit = {
    method,
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
  };

  if (body) {
    config.body = JSON.stringify(body);
  }

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, config);
    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }
    return response.json();
  } catch (error) {
    console.error(`API request failed for ${endpoint}:`, error);
    throw error;
  }
}

// Agents
export const agentsApi = {
  run: (symbol: string) =>
    apiRequest<unknown>("/api/agents/run", { method: "POST", body: { symbol } }),
  getStatus: () => apiRequest<unknown>("/api/agents/status"),
};

// Backtest
export const backtestApi = {
  run: (config: Record<string, unknown>) =>
    apiRequest<unknown>("/api/backtest/run", { method: "POST", body: config }),
  getResult: (id: string) => apiRequest<unknown>(`/api/backtest/result/${id}`),
};

// Trading
export const tradingApi = {
  placeOrder: (order: Record<string, unknown>) =>
    apiRequest<unknown>("/api/trading/order", { method: "POST", body: order }),
  getPositions: () => apiRequest<unknown>("/api/trading/positions"),
};

// Market
export const marketApi = {
  getPrice: (symbol: string) => apiRequest<unknown>(`/api/market/price/${symbol}`),
  getSentiment: () => apiRequest<unknown>("/api/market/sentiment"),
};

// Portfolio
export const portfolioApi = {
  getSummary: () => apiRequest<unknown>("/api/portfolio/summary"),
  getPerformance: () => apiRequest<unknown>("/api/portfolio/performance"),
};

export default apiRequest;
