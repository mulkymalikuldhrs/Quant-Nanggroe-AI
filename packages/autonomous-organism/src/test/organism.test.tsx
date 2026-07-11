import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { OrganismCore } from "@/components/OrganismCore";
import { AuthGate } from "@/components/AuthGate";
import { useOrganismReal } from "@/hooks/useOrganismReal";
import { renderHook } from "@testing-library/react";

// ── Mocks ──────────────────────────────────────────────────────────────────────

// Mock supabase client
const mockGetSession = vi.fn();
const mockOnAuthStateChange = vi.fn();
const mockFrom = vi.fn();
const mockFunctionsInvoke = vi.fn();

vi.mock("@/integrations/supabase/client", () => ({
  supabase: {
    auth: {
      getSession: (...args: unknown[]) => mockGetSession(...args),
      onAuthStateChange: (...args: unknown[]) => mockOnAuthStateChange(...args),
      signOut: vi.fn(() => Promise.resolve({ error: null })),
    },
    from: (...args: unknown[]) => mockFrom(...args),
    functions: {
      invoke: (...args: unknown[]) => mockFunctionsInvoke(...args),
    },
  },
}));

// Mock react-router-dom
const mockNavigate = vi.fn();
vi.mock("react-router-dom", () => ({
  useNavigate: () => mockNavigate,
}));

// Mock @tanstack/react-query
vi.mock("@tanstack/react-query", () => ({
  useQuery: vi.fn(() => ({
    data: null,
    isLoading: false,
    error: null,
  })),
  useQueryClient: vi.fn(() => ({
    invalidateQueries: vi.fn(),
  })),
}));

// ── OrganismCore Tests ────────────────────────────────────────────────────────

describe("OrganismCore", () => {
  it("renders the status text", () => {
    render(<OrganismCore status="alive" />);
    expect(screen.getByText("alive")).toBeInTheDocument();
  });

  it("renders dormant status", () => {
    render(<OrganismCore status="dormant" />);
    expect(screen.getByText("dormant")).toBeInTheDocument();
  });

  it("renders spawning status", () => {
    render(<OrganismCore status="spawning" />);
    expect(screen.getByText("spawning")).toBeInTheDocument();
  });

  it("renders dying status", () => {
    render(<OrganismCore status="dying" />);
    expect(screen.getByText("dying")).toBeInTheDocument();
  });

  it("renders outer ring elements", () => {
    const { container } = render(<OrganismCore status="alive" />);
    const rings = container.querySelectorAll(".rounded-full.border");
    expect(rings.length).toBe(3);
  });
});

// ── useOrganismReal Hook Tests ────────────────────────────────────────────────

describe("useOrganismReal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns the expected shape with default values", () => {
    const { result } = renderHook(() => useOrganismReal());

    // Should have all expected keys
    expect(result.current).toHaveProperty("session");
    expect(result.current).toHaveProperty("profile");
    expect(result.current).toHaveProperty("logs");
    expect(result.current).toHaveProperty("logsLoading");
    expect(result.current).toHaveProperty("state");
    expect(result.current).toHaveProperty("stateLoading");
    expect(result.current).toHaveProperty("engineRuns");
    expect(result.current).toHaveProperty("ideas");
    expect(result.current).toHaveProperty("sources");
    expect(result.current).toHaveProperty("schedulerConfig");
    expect(result.current).toHaveProperty("runSense");
    expect(result.current).toHaveProperty("runDecision");
    expect(result.current).toHaveProperty("runFactory");
    expect(result.current).toHaveProperty("runGrowth");
    expect(result.current).toHaveProperty("runDecisionClient");
  });

  it("returns arrays for logs, engineRuns, ideas, and sources by default", () => {
    const { result } = renderHook(() => useOrganismReal());

    expect(Array.isArray(result.current.logs)).toBe(true);
    expect(Array.isArray(result.current.engineRuns)).toBe(true);
    expect(Array.isArray(result.current.ideas)).toBe(true);
    expect(Array.isArray(result.current.sources)).toBe(true);
  });

  it("exposes run functions that are callable", () => {
    const { result } = renderHook(() => useOrganismReal());

    expect(typeof result.current.runSense).toBe("function");
    expect(typeof result.current.runDecision).toBe("function");
    expect(typeof result.current.runFactory).toBe("function");
    expect(typeof result.current.runGrowth).toBe("function");
  });
});

// ── AuthGate Tests ────────────────────────────────────────────────────────────

describe("AuthGate", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockOnAuthStateChange.mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } },
    });
  });

  it("redirects to /login when no session exists", async () => {
    mockGetSession.mockResolvedValue({
      data: { session: null },
    });

    render(
      <AuthGate>
        <div>Protected Content</div>
      </AuthGate>
    );

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/login", { replace: true });
    });
  });

  it("renders children when session exists", async () => {
    mockGetSession.mockResolvedValue({
      data: {
        session: {
          user: { id: "test-user-id" },
          access_token: "mock-token",
        },
      },
    });

    render(
      <AuthGate>
        <div>Protected Content</div>
      </AuthGate>
    );

    await waitFor(() => {
      expect(screen.getByText("Protected Content")).toBeInTheDocument();
    });
  });

  it("renders nothing while session is being checked", () => {
    mockGetSession.mockReturnValue(new Promise(() => {})); // Never resolves

    const { container } = render(
      <AuthGate>
        <div>Protected Content</div>
      </AuthGate>
    );

    expect(container.innerHTML).toBe("");
  });
});
