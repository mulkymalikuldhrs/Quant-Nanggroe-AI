"use client";

/**
 * Quant-Nanggroe OrderFlowMap — placeholder component
 * The shared orderflow-map module is not available in this build
 */

interface OrderFlowMapProps {
  symbol?: string;
  tick?: number;
  initialMid?: number;
}

export default function OrderFlowMap(props: OrderFlowMapProps) {
  return (
    <div className="p-4 rounded-xl bg-white/5 border border-white/10 text-center">
      <p className="text-sm text-white/40">Order Flow Map</p>
      <p className="text-xs text-white/30 mt-1">Symbol: {props.symbol || "BTC-USD"}</p>
      <p className="text-xs text-white/20 mt-1">Shared module not available in this build</p>
    </div>
  );
}

export type { OrderFlowMapProps };
