/**
 * Ecosystem Client — Typed frontend client for all ecosystem services.
 *
 * Provides React hooks and API methods for:
 *   - Crucix OSINT intelligence
 *   - HermesQuant trading
 *   - Autonomous Organism
 *   - Ecosystem overview
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface EcosystemStatus {
  ecosystem: string;
  version: string;
  overall: "healthy" | "degraded";
  services: {
    crucix?: { status: string; type: string; port?: number };
    hermes_quant?: { status: string; type: string };
    autonomous_organism?: { status: string; type: string };
  };
}

export interface CrucixSweepData {
  regime: string;
  sources_active: number;
  signals: Array<{
    id: string;
    source: string;
    category: string;
    summary: string;
    delta?: { direction: string; magnitude: number };
  }>;
  news: Array<{ title: string; source: string; timestamp: string }>;
  market_indices: Record<string, number>;
  commodities: Record<string, number>;
}

export interface HermesPortfolio {
  available: boolean;
  portfolio?: {
    allocation?: unknown;
    journal_stats?: unknown;
    pnl?: unknown;
  };
  error?: string;
}

export interface OrganismInfo {
  available: boolean;
  organism?: {
    org_id: string;
    name: string;
    generation: number;
    status: string;
  };
}

export interface EcosystemOverview {
  ecosystem: string;
  version: string;
  crucix: {
    regime?: string;
    sources_active?: number;
    signal_count?: number;
    news_count?: number;
    health?: string;
    status?: string;
  };
  hermes_quant: Record<string, unknown>;
  autonomous_organism: { available?: boolean; status?: string };
}

// ---------------------------------------------------------------------------
// API Client
// ---------------------------------------------------------------------------

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchAPI<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

/** Fetch overall ecosystem status. */
export async function getEcosystemStatus(): Promise<EcosystemStatus> {
  return fetchAPI<EcosystemStatus>("/api/ecosystem/status");
}

/** Fetch Crucix OSINT sweep data. */
export async function getCrucixData(): Promise<{
  sweep: CrucixSweepData;
  health: { status: string; uptime: number };
}> {
  return fetchAPI("/api/ecosystem/crucix");
}

/** Fetch HermesQuant trading status. */
export async function getHermesStatus(): Promise<HermesPortfolio> {
  return fetchAPI<HermesPortfolio>("/api/ecosystem/hermes");
}

/** Fetch Autonomous Organism status. */
export async function getOrganismStatus(): Promise<OrganismInfo> {
  return fetchAPI<OrganismInfo>("/api/ecosystem/organism");
}

/** Fetch combined ecosystem overview. */
export async function getEcosystemOverview(): Promise<EcosystemOverview> {
  return fetchAPI<EcosystemOverview>("/api/ecosystem/overview");
}
