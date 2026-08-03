"use client";

import React, { useState, useEffect } from "react";
import { apiRequest } from "@/lib/api-client";
import { LoadingSkeleton } from "@/components/shared/loading-skeleton";

interface Filing {
  accessionNo: string;
  filingDate: string;
  fileType: string;
  size: number;
  ticker: string;
  cik: string;
}

interface FilingsResponse {
  items: Filing[];
  count: number;
  ticker: string;
  module: string;
  timestamp: string;
  status: string;
  error?: string;
}

export default function SecEdgarPage() {
  const [filings, setFilings] = useState<Filing[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [ticker, setTicker] = useState("AAPL");

  const loadFilings = async (tickerSymbol: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiRequest<FilingsResponse>(`/api/sec/edgar/filings?ticker=${tickerSymbol}&limit=10`);
      setFilings(response.items);
    } catch (err) {
      setError("Failed to load SEC filings");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFilings(ticker);
  }, [ticker]);

  if (loading) {
    return (
      <div className="space-y-4 animate-slide-up">
        <div className="h-8 w-64 rounded-lg bg-white/5 animate-pulse" />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-32 rounded-xl bg-white/5 animate-pulse" />
          ))}
        </div>
        <div className="h-8 w-48 rounded-lg bg-white/5 animate-pulse" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20">
        <p className="text-sm text-red-400">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4 animate-slide-up">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <span className="text-blue-400 w-5 h-5">📄</span>
            SEC EDGAR Filings
          </h1>
          <p className="text-sm text-white/40 mt-0.5">
            Real-time SEC filings for {ticker}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <input
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            onBlur={() => loadFilings(ticker)}
            className="px-3 py-2 rounded-lg bg-gray-600/30 text-white border border-gray-500/30 focus:outline-none focus:ring-2 focus:ring-amber-400"
            placeholder="Enter ticker (e.g. AAPL)"
          />
          <button
            onClick={() => loadFilings(ticker)}
            className="px-4 py-2 bg-amber-500/20 text-amber-400 rounded hover:bg-amber-500/30 focus:outline-none"
          >
            Search
          </button>
        </div>
      </div>

      {filings.length === 0 && (
        <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
          <p className="text-sm text-yellow-400">No filings found for {ticker}</p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
        {filings.map((filing) => (
          <div key={filing.accessionNo} className="p-4 rounded-lg bg-white/5 border border-white/10">
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium text-white">{filing.fileType}</span>
              <span className="text-xs text-white/50">{filing.filingDate}</span>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-white/40">CIK:</span>
                <span className="text-white/60 font-mono">{filing.cik}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-white/40">Ticker:</span>
                <span className="text-white/60 font-mono">{filing.ticker}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-white/40">Size:</span>
                <span className="text-white/60">{filing.size} KB</span>
              </div>
              <div className="flex items-center gap-2 mt-1">
                <a
                  href={`https://www.sec.gov/Archives/edgar/data/${filing.cik}/${filing.accessionNo}/${filing.accessionNo}-index.html`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-amber-400 hover:text-amber-300 underline"
                >
                  View on SEC.gov
                </a>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}