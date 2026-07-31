"use client";

// ── Orderflow Components ────────────────────────────────────────────
// Ported from OrderFlowMap (E:\OrderFlowMap\index.html)
// Lightweight Charts v5 primitives for bookmap-style visualizations.

export { OrderflowHeatmap, createHeatmapPrimitive } from "./orderflow-heatmap";
export { TradeBubbles, createBubblesPrimitive } from "./trade-bubbles";
export { addCvdSeries, setCvdData } from "./cvd-pane";
export { LiquidityWalls, createWallsPrimitive } from "./liquidity-walls";

// ── Types ───────────────────────────────────────────────────────────
export type {
  DepthLevel,
  DepthSnapshot,
  Trade,
  CvdBar,
  Wall,
  BarData,
  ColorMapName,
  HeatmapConfig,
  BubbleConfig,
  WallsConfig,
  HeatmapPrimitiveData,
  OrderflowHeatmapProps,
  TradeBubblesProps,
  CvdPaneProps,
  LiquidityWallsProps,
} from "./types";
