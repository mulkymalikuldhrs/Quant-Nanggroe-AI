import React, { useState, useEffect, useCallback } from "react";
import { apiRequest } from "../../lib/api-client";

// ponytail: one generic renderer for all "fetch + display" pages.
// Adapts to any JSON shape: array of objects -> table; object -> key/value cards.
// Replaces 10 near-identical hand-rolled pages.

type Json = Record<string, unknown> | unknown[] | null;

function isArrayOfObjects(d: Json): d is Record<string, unknown>[] {
  return Array.isArray(d) && d.length > 0 && typeof d[0] === "object" && !Array.isArray(d[0]);
}

function TableView({ rows }: { rows: Record<string, unknown>[] }) {
  const cols = Array.from(
    rows.reduce((set, r) => {
      Object.keys(r).forEach((k) => set.add(k));
      return set;
    }, new Set<string>())
  );
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ borderCollapse: "collapse", width: "100%", fontSize: 13 }}>
        <thead>
          <tr>
            {cols.map((c) => (
              <th key={c} style={{ borderBottom: "2px solid #333", textAlign: "left", padding: "6px 10px" }}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              {cols.map((c) => (
                <td key={c} style={{ borderBottom: "1px solid #222", padding: "6px 10px" }}>
                  {typeof r[c] === "object" ? JSON.stringify(r[c]) : String(r[c] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CardsView({ obj }: { obj: Record<string, unknown> }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 12 }}>
      {Object.entries(obj).map(([k, v]) => (
        <div key={k} style={{ border: "1px solid #222", borderRadius: 8, padding: 12 }}>
          <div style={{ fontSize: 11, opacity: 0.6, textTransform: "uppercase" }}>{k}</div>
          <div style={{ marginTop: 4, fontSize: 14, wordBreak: "break-word" }}>
            {typeof v === "object" ? <pre style={{ margin: 0, fontSize: 12 }}>{JSON.stringify(v, null, 2)}</pre> : String(v ?? "")}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function DataPage({
  title,
  endpoint,
  refreshMs,
}: {
  title: string;
  endpoint: string;
  refreshMs?: number;
}) {
  const [data, setData] = useState<Json>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiRequest<Json>(endpoint);
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [endpoint]);

  useEffect(() => {
    load();
    if (refreshMs && refreshMs > 0) {
      const id = setInterval(load, refreshMs);
      return () => clearInterval(id);
    }
  }, [load, refreshMs]);

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
        <h1 style={{ fontSize: 22, margin: 0 }}>{title}</h1>
        <button onClick={load} disabled={loading} style={{ padding: "6px 14px", borderRadius: 6, cursor: "pointer" }}>
          {loading ? "Loading…" : "Refresh"}
        </button>
      </div>
      {error && (
        <div style={{ border: "1px solid #5a1a1a", background: "#2a1515", padding: 12, borderRadius: 8, color: "#ff9a9a" }}>
          Error: {error}
        </div>
      )}
      {loading && !error && <div style={{ opacity: 0.7 }}>Loading {endpoint}…</div>}
      {!loading && !error && data === null && <div style={{ opacity: 0.7 }}>No data.</div>}
      {!loading && !error && isArrayOfObjects(data) && <TableView rows={data} />}
      {!loading && !error && data && !Array.isArray(data) && typeof data === "object" && (
        <CardsView obj={data as Record<string, unknown>} />
      )}
      {!loading && !error && Array.isArray(data) && data.length === 0 && <div style={{ opacity: 0.7 }}>Empty list.</div>}
    </div>
  );
}
