"use client";

// ── Core Data Types ─────────────────────────────────────────────────

export interface DepthLevel {
  /** Price level */
  price: number;
  /** Quantity at this level */
  qty: number;
  /** Number of orders at this level */
  orders?: number;
}

export interface DepthSnapshot {
  time: number;
  bids: DepthLevel[];
  asks: DepthLevel[];
}

export interface Trade {
  time: number;
  price: number;
  qty: number;
  /** 'B' for buy, 'S' for sell */
  side: "B" | "S";
}

export interface CvdBar {
  time: number;
  value: number;
}

export interface Wall {
  price: number;
  /** 'bid' or 'ask' */
  side: "bid" | "ask";
  /** Average quantity at wall */
  avgQty: number;
}

export interface BarData {
  time: number;
  mid: number;
  bbid: number;
  bask: number;
  vwap: number;
}

// ── Config Types ────────────────────────────────────────────────────

export type ColorMapName = "bookmap" | "mono" | "inferno" | "viridis";

export interface HeatmapConfig {
  /** Whether heatmap is visible */
  visible: boolean;
  /** Gamma correction for color intensity */
  gamma: number;
  /** Intensity multiplier */
  intensity: number;
  /** Height of each heatmap row in pixels */
  rowHeight: number;
  /** Minimum quantity to render */
  minQty: number;
  /** Color map to use */
  colorMap: ColorMapName;
}

export interface BubbleConfig {
  /** Whether bubbles are visible */
  visible: boolean;
  /** Minimum bubble radius in pixels */
  minRadius: number;
  /** Maximum bubble radius in pixels */
  maxRadius: number;
  /** Size scaling function: 'sqrt' | 'log' | 'linear' */
  scale: "sqrt" | "log" | "linear";
  /** Quantity threshold for large trade markers */
  largeQty: number;
  /** Minimum trade quantity to render */
  minTrade: number;
  /** Whether small trades render as hollow circles */
  hollowSmall: boolean;
}

export interface WallsConfig {
  /** Whether walls are visible */
  visible: boolean;
  /** Minimum qty to consider (passed from heatmap config) */
  minQty: number;
}

// ── Component Props ─────────────────────────────────────────────────

export interface HeatmapPrimitiveData {
  depth: DepthSnapshot[];
  bars: BarData[];
}

export interface OrderflowHeatmapProps {
  data: HeatmapPrimitiveData;
  config: HeatmapConfig;
  /** Series instance to attach to - injected by parent */
  seriesRef?: React.RefObject<{ attachPrimitive: (p: unknown) => void; detachPrimitive: (p: unknown) => void } | null>;
  chartRef?: React.RefObject<{ timeScale: () => { timeToCoordinate: (t: number) => number | null; options: () => { barSpacing: number }; getVisibleLogicalRange: () => { from: number; to: number } | null } } | null>;
  midSeriesRef?: React.RefObject<{ priceToCoordinate: (p: number) => number | null } | null>;
}

export interface TradeBubblesProps {
  trades: Trade[];
  config: BubbleConfig;
  seriesRef?: React.RefObject<{ attachPrimitive: (p: unknown) => void; detachPrimitive: (p: unknown) => void } | null>;
  chartRef?: React.RefObject<{ timeScale: () => { timeToCoordinate: (t: number) => number | null } } | null>;
  midSeriesRef?: React.RefObject<{ priceToCoordinate: (p: number) => number | null } | null>;
}

export interface CvdPaneProps {
  data: CvdBar[];
  chartRef?: React.RefObject<{ timeScale: () => { fitContent: () => void } } | null>;
}

export interface LiquidityWallsProps {
  walls: Wall[];
  depth: DepthSnapshot[];
  bars: BarData[];
  config: WallsConfig;
  seriesRef?: React.RefObject<{ attachPrimitive: (p: unknown) => void; detachPrimitive: (p: unknown) => void } | null>;
  chartRef?: React.RefObject<{ timeScale: () => { timeToCoordinate: (t: number) => number | null } } | null>;
  midSeriesRef?: React.RefObject<{ priceToCoordinate: (p: number) => number | null } | null>;
}
