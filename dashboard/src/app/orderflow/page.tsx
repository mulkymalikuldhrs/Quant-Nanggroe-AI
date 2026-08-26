"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useState, useEffect, useRef } from "react";
import { ErrorBoundary } from "@/components/shared/error-boundary";

const OrderFlowMap = dynamic(() => import("@/components/OrderFlowMap"), {
  ssr: false,
  loading: () => (
    <div className="h-screen flex items-center justify-center bg-[#080b10] text-gray-500">
      <div className="text-center">
        <div className="animate-pulse text-2xl mb-2">📡</div>
        <div className="text-xs">Loading OrderFlow…</div>
      </div>
    </div>
  ),
});

const INSTRUMENTS = [
  { sym: "EURUSD", name: "EUR/USD", tick: 0.00001, mid: 1.0875 },
  { sym: "GBPUSD", name: "GBP/USD", tick: 0.00001, mid: 1.2750 },
  { sym: "USDJPY", name: "USD/JPY", tick: 0.001, mid: 157.5 },
  { sym: "AUDUSD", name: "AUD/USD", tick: 0.00001, mid: 0.6550 },
  { sym: "USDCAD", name: "USD/CAD", tick: 0.00001, mid: 1.3650 },
  { sym: "USDCHF", name: "USD/CHF", tick: 0.00001, mid: 0.8750 },
  { sym: "NZDUSD", name: "NZD/USD", tick: 0.00001, mid: 0.5950 },
  { sym: "EURGBP", name: "EUR/GBP", tick: 0.00001, mid: 0.8520 },
  { sym: "XAUUSD", name: "Gold", tick: 0.01, mid: 2420 },
  { sym: "XAGUSD", name: "Silver", tick: 0.01, mid: 28.5 },
];

function OrderFlowContent() {
  const [selected, setSelected] = useState(INSTRUMENTS[0]);
  const [showPicker, setShowPicker] = useState(false);
  const pickerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!showPicker) return;
    const handler = (e: MouseEvent) => {
      if (pickerRef.current && !pickerRef.current.contains(e.target as Node)) {
        setShowPicker(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [showPicker]);

  useEffect(() => {
    if (!showPicker) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setShowPicker(false);
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [showPicker]);

  return (
    <div className="h-screen flex flex-col">
      <div className="h-8 border-b border-white/[0.06] flex items-center px-3 gap-3 text-xs bg-white/[0.02]">
        <Link href="/" className="text-white/40 hover:text-white transition-colors">← Dashboard</Link>
        <span className="text-white/20">|</span>
        <span className="text-white/40">📡 Order Flow</span>
        <div className="ml-auto flex items-center gap-2">
          <div className="relative" ref={pickerRef}>
            <button
              onClick={() => setShowPicker(!showPicker)}
              className="px-2 py-0.5 bg-white/[0.04] border border-white/[0.06] rounded text-xs text-white font-bold hover:bg-white/[0.08] transition-colors"
            >
              {selected.name} ▾
            </button>
            {showPicker && (
              <div className="absolute top-full right-0 mt-1 w-48 bg-[#0e131b] border border-white/[0.08] rounded-md shadow-xl z-50 max-h-60 overflow-y-auto">
                {INSTRUMENTS.map((s, i) => (
                  <button
                    key={`${s.sym}-${i}`}
                    onClick={() => { setSelected(s); setShowPicker(false); }}
                    className={`w-full text-left px-3 py-1.5 text-xs hover:bg-white/[0.05] flex justify-between items-center ${
                      selected.sym === s.sym ? "bg-white/[0.05] text-white" : "text-white/70"
                    }`}
                  >
                    <span className="font-medium">{s.sym}</span>
                    <span className="text-white/30">{s.name}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="flex-1 min-h-0">
        <OrderFlowMap
          symbol={selected.sym}
          tick={selected.tick}
          initialMid={selected.mid}
        />
      </div>
    </div>
  );
}

export default function OrderFlowPage() {
  return (
    <ErrorBoundary>
      <OrderFlowContent />
    </ErrorBoundary>
  );
}
