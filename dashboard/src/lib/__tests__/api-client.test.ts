import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { apiRequest, ApiError, agentsApi, tradingApi, marketApi } from "../api-client";

// ── Helpers ─────────────────────────────────────────────────────────

const API_BASE = "http://localhost:8000";

function mockFetch(status: number, body: unknown, ok?: boolean) {
  return vi.mocked(fetch).mockResolvedValueOnce({
    ok: ok ?? (status >= 200 && status < 300),
    status,
    json: () => Promise.resolve(body),
    statusText: status === 200 ? "OK" : "Error",
  } as Response);
}

// ── Setup ────────────────────────────────────────────────────────────

beforeEach(() => {
  vi.useFakeTimers();
  vi.spyOn(console, "error").mockImplementation(() => {});
  vi.spyOn(globalThis, "fetch").mockImplementation(
    () => Promise.resolve(new Response()),
  );
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});

// ═════════════════════════════════════════════════════════════════════
//  ApiError
// ═════════════════════════════════════════════════════════════════════

describe("ApiError", () => {
  it("creates error with status, body, retryable flag", () => {
    const err = new ApiError("Not found", 404, { detail: "missing" }, false);
    expect(err.message).toBe("Not found");
    expect(err.status).toBe(404);
    expect(err.body).toEqual({ detail: "missing" });
    expect(err.retryable).toBe(false);
    expect(err.name).toBe("ApiError");
  });

  it("defaults retryable to false", () => {
    const err = new ApiError("err", 500, null);
    expect(err.retryable).toBe(false);
  });
});

// ═════════════════════════════════════════════════════════════════════
//  apiRequest — Basic
// ═════════════════════════════════════════════════════════════════════

describe("apiRequest", () => {
  it("makes GET request and returns parsed JSON", async () => {
    const data = { symbol: "BTC", price: 65000 };
    mockFetch(200, data);

    const result = await apiRequest("/api/market/price/BTC");
    expect(result).toEqual(data);
    expect(fetch).toHaveBeenCalledWith(
      `${API_BASE}/api/market/price/BTC`,
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("makes POST request with body", async () => {
    const body = { symbol: "BTC", side: "buy" as const, type: "market" as const, quantity: 1 };
    const response = { orderId: "123", status: "filled" as const, message: "ok" };
    mockFetch(200, response);

    const result = await apiRequest("/api/trading/order", { method: "POST", body });
    expect(result).toEqual(response);
    expect(fetch).toHaveBeenCalledWith(
      `${API_BASE}/api/trading/order`,
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(body),
      }),
    );
  });

  it("handles 204 No Content", async () => {
    mockFetch(204, null, true);
    const result = await apiRequest("/api/trading/order/123", { method: "DELETE" });
    expect(result).toBeUndefined();
  });
});

// ═════════════════════════════════════════════════════════════════════
//  apiRequest — Retry Logic
// ═════════════════════════════════════════════════════════════════════

describe("apiRequest — retry", () => {
  it("retries on 5xx errors up to maxRetries", async () => {
    const data = { success: true };
    vi.mocked(fetch)
      .mockRejectedValueOnce(new TypeError("Network error"))
      .mockResolvedValueOnce({
        ok: false,
        status: 502,
        json: () => Promise.resolve(null),
        statusText: "Bad Gateway",
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(data),
        statusText: "OK",
      } as Response);

    const promise = apiRequest("/api/test", { retries: 3 });
    await vi.advanceTimersByTimeAsync(500);
    await vi.advanceTimersByTimeAsync(1000);
    const result = await promise;

    expect(result).toEqual(data);
    expect(fetch).toHaveBeenCalledTimes(3);
  });

  it("does NOT retry on 4xx client errors", async () => {
    mockFetch(400, { message: "Bad request" });

    await expect(apiRequest("/api/test", { retries: 3 })).rejects.toThrow(ApiError);
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("does NOT retry on 429 rate limit", async () => {
    mockFetch(429, { message: "Rate limited" });

    await expect(apiRequest("/api/test", { retries: 3 })).rejects.toThrow("Rate limited");
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("throws non-retryable ApiError for 404", async () => {
    mockFetch(404, { detail: "Not found" });

    await expect(apiRequest("/api/test")).rejects.toMatchObject({
      status: 404,
      retryable: false,
    });
  });

  it("gives up after exhausting retries on persistent network errors", async () => {
    vi.mocked(fetch).mockRejectedValue(new TypeError("Network error"));

    const promise = apiRequest("/api/test", { retries: 2 });
    await vi.advanceTimersByTimeAsync(500);
    await vi.advanceTimersByTimeAsync(1000);
    await expect(promise).rejects.toThrow("Network error");
    expect(fetch).toHaveBeenCalledTimes(3); // initial + 2 retries
  });
});

// ═════════════════════════════════════════════════════════════════════
//  apiRequest — Deduplication
// ═════════════════════════════════════════════════════════════════════

describe("apiRequest — dedup", () => {
  it("deduplicates concurrent GET requests to same endpoint", async () => {
    const data = { price: 100 };
    mockFetch(200, data);

    const [r1, r2] = await Promise.all([
      apiRequest("/api/market/price/BTC"),
      apiRequest("/api/market/price/BTC"),
    ]);

    expect(r1).toEqual(data);
    expect(r2).toEqual(data);
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("does NOT deduplicate POST requests", async () => {
    mockFetch(200, { id: "1" });
    mockFetch(200, { id: "2" });

    const [r1, r2] = await Promise.all([
      apiRequest("/api/test", { method: "POST", body: { x: 1 } }),
      apiRequest("/api/test", { method: "POST", body: { x: 2 } }),
    ]);

    expect(fetch).toHaveBeenCalledTimes(2);
  });

  it("can opt out of dedup via deduplicate: false", async () => {
    mockFetch(200, { a: 1 });
    mockFetch(200, { a: 2 });

    const [r1, r2] = await Promise.all([
      apiRequest("/api/market/price/BTC", { deduplicate: false }),
      apiRequest("/api/market/price/BTC", { deduplicate: false }),
    ]);

    expect(fetch).toHaveBeenCalledTimes(2);
  });
});

// ═════════════════════════════════════════════════════════════════════
//  apiRequest — Non-retryable error propagation
// ═════════════════════════════════════════════════════════════════════

describe("apiRequest — error messages", () => {
  it("formats validation error with detail array", async () => {
    const errorBody = { detail: [{ msg: "symbol is required" }, { msg: "side must be buy or sell" }] };
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: false,
      status: 422,
      json: () => Promise.resolve(errorBody),
      statusText: "Unprocessable",
    } as Response);

    await expect(apiRequest("/api/test", { retries: 0 })).rejects.toThrow(
      "Validation error: symbol is required, side must be buy or sell",
    );
  });
});

// ═════════════════════════════════════════════════════════════════════
//  API Endpoint Objects
// ═════════════════════════════════════════════════════════════════════

describe("API endpoint objects", () => {
  it("agentsApi.getStatus calls correct endpoint", async () => {
    const data = { agents: [], kill_switch_active: false };
    mockFetch(200, data);

    const result = await agentsApi.getStatus();
    expect(result).toEqual(data);
    expect(fetch).toHaveBeenCalledWith(
      `${API_BASE}/api/agents/status`,
      expect.any(Object),
    );
  });

  it("tradingApi.placeOrder sends POST with body", async () => {
    const req = { symbol: "BTC", side: "buy" as const, type: "market" as const, quantity: 0.5 };
    const resp = { orderId: "o1", status: "filled" as const, message: "done" };
    mockFetch(200, resp);

    const result = await tradingApi.placeOrder(req);
    expect(result).toEqual(resp);
  });

  it("marketApi.getSentiment returns sentiment data", async () => {
    const sentiment = { overall: 65, fear_greed: 55, sectors: [] };
    mockFetch(200, sentiment);

    const result = await marketApi.getSentiment();
    expect(result.overall).toBe(65);
  });

  it("agentsApi.activateKillSwitch sends reason", async () => {
    mockFetch(200, { is_active: true, activation_reason: "manual override", message: "" });

    const result = await agentsApi.activateKillSwitch("manual override");
    expect(result.is_active).toBe(true);
    expect(fetch).toHaveBeenCalledWith(
      `${API_BASE}/api/agents/kill-switch/activate`,
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ reason: "manual override" }),
      }),
    );
  });
});
