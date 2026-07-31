"use client";

import { useEffect, useRef } from "react";
import type {
  IChartApi,
  ISeriesApi,
  ISeriesPrimitive,
  SeriesAttachedParameter,
  IPrimitivePaneView,
  IPrimitivePaneRenderer,
  Time,
} from "lightweight-charts";
import type {
  CanvasRenderingTarget2D,
  BitmapCoordinatesRenderingScope,
} from "fancy-canvas";
import type { Wall, WallsConfig, DepthSnapshot, BarData } from "./types";

// ── Walls Renderer (ported from OrderFlowMap WallsPrimitive) ─────────

class WallsRenderer implements IPrimitivePaneRenderer {
  private _walls: Wall[];
  private _depth: DepthSnapshot[];
  private _bars: BarData[];
  private _config: WallsConfig;
  private _series: ISeriesApi<"Line", Time> | null = null;
  private _chart: IChartApi | null = null;

  constructor(
    walls: Wall[],
    depth: DepthSnapshot[],
    bars: BarData[],
    config: WallsConfig,
  ) {
    this._walls = walls;
    this._depth = depth;
    this._bars = bars;
    this._config = config;
  }

  update(
    walls: Wall[],
    depth: DepthSnapshot[],
    bars: BarData[],
    config: WallsConfig,
    series: ISeriesApi<"Line", Time> | null,
    chart: IChartApi | null,
  ) {
    this._walls = walls;
    this._depth = depth;
    this._bars = bars;
    this._config = config;
    this._series = series;
    this._chart = chart;
  }

  draw(target: CanvasRenderingTarget2D): void {
    target.useBitmapCoordinateSpace((scope: BitmapCoordinatesRenderingScope) => {
      if (!this._config.visible || !this._series || !this._chart) return;
      if (this._depth.length < 5) return;

      const { context: ctx, bitmapSize, horizontalPixelRatio: hpr, verticalPixelRatio: vpr } = scope;
      const ts = this._chart.timeScale();
      const lr = ts.getVisibleLogicalRange();
      if (!lr) return;

      const bars = this._bars;
      const startTime = bars[Math.max(0, Math.floor(lr.from))]?.time ?? this._depth[0].time;
      const endTime = bars[Math.min(bars.length - 1, Math.ceil(lr.to))]?.time ?? this._depth[this._depth.length - 1].time;

      ctx.save();

      // Draw historical wall segments between depth snapshots
      for (let i = 0; i < this._depth.length - 1; i++) {
        const d1 = this._depth[i];
        const d2 = this._depth[i + 1];
        if (d1.time < startTime - 10 || d1.time > endTime + 10) continue;

        const x1 = ts.timeToCoordinate(d1.time as Time);
        const x2 = ts.timeToCoordinate(d2.time as Time);
        if (x1 === null || x2 === null) continue;
        const x1Px = Math.round(x1 * hpr);
        const x2Px = Math.round(x2 * hpr);

        // Compute average qty for wall detection threshold
        let sumAsk = 0;
        d1.asks.forEach((x) => (sumAsk += x.qty));
        const avgAsk = d1.asks.length ? sumAsk / d1.asks.length : 1;

        let sumBid = 0;
        d1.bids.forEach((x) => (sumBid += x.qty));
        const avgBid = d1.bids.length ? sumBid / d1.bids.length : 1;

        // Draw ask walls (historical segments)
        d1.asks.forEach((x) => {
          if (x.qty >= avgAsk * 2.2 && x.qty >= this._config.minQty) {
            const y = this._series!.priceToCoordinate(x.price);
            if (y !== null) {
              const yPx = Math.round(y * vpr);
              ctx.strokeStyle = "rgba(239,83,80,0.5)";
              ctx.lineWidth = 1.2 * hpr;
              ctx.beginPath();
              ctx.moveTo(x1Px, yPx);
              ctx.lineTo(x2Px, yPx);
              ctx.stroke();
            }
          }
        });

        // Draw bid walls (historical segments)
        d1.bids.forEach((x) => {
          if (x.qty >= avgBid * 2.2 && x.qty >= this._config.minQty) {
            const y = this._series!.priceToCoordinate(x.price);
            if (y !== null) {
              const yPx = Math.round(y * vpr);
              ctx.strokeStyle = "rgba(38,166,154,0.5)";
              ctx.lineWidth = 1.2 * hpr;
              ctx.beginPath();
              ctx.moveTo(x1Px, yPx);
              ctx.lineTo(x2Px, yPx);
              ctx.stroke();
            }
          }
        });
      }

      // Draw persistent wall tags from recent snapshots
      const N = Math.min(30, this._depth.length);
      const persist = new Map<string, { side: "bid" | "ask"; count: number; totalQty: number; price: number }>();
      let totalQ = 0;
      let n = 0;

      for (let i = this._depth.length - N; i < this._depth.length; i++) {
        const d = this._depth[i];
        for (const lv of d.bids) {
          totalQ += lv.qty;
          n++;
          const k = lv.price.toFixed(2) + "_b";
          const e = persist.get(k) || { side: "bid" as const, count: 0, totalQty: 0, price: lv.price };
          e.count++;
          e.totalQty += lv.qty;
          persist.set(k, e);
        }
        for (const lv of d.asks) {
          totalQ += lv.qty;
          n++;
          const k = lv.price.toFixed(2) + "_a";
          const e = persist.get(k) || { side: "ask" as const, count: 0, totalQty: 0, price: lv.price };
          e.count++;
          e.totalQty += lv.qty;
          persist.set(k, e);
        }
      }

      const avg = n ? totalQ / n : 1;
      const lastT = this._depth[this._depth.length - 1].time;
      const xR = ts.timeToCoordinate(lastT as Time);

      if (xR !== null) {
        ctx.font = `${10 * hpr}px Inter,Arial`;
        ctx.textBaseline = "middle";

        for (const e of persist.values()) {
          if (e.count < N * 0.6) continue;
          const avgQ = e.totalQty / e.count;
          if (avgQ < avg * 2.2) continue;

          const y = this._series!.priceToCoordinate(e.price);
          if (y === null) continue;
          const yPx = Math.round(y * vpr);
          const xPx = Math.round(xR * hpr);
          const col = e.side === "bid" ? "38,166,154" : "239,83,80";

          // Dashed line across the pane
          ctx.setLineDash([6 * hpr, 4 * hpr]);
          ctx.strokeStyle = `rgba(${col},0.85)`;
          ctx.lineWidth = 1 * hpr;
          ctx.beginPath();
          ctx.moveTo(0, yPx);
          ctx.lineTo(xPx, yPx);
          ctx.stroke();
          ctx.setLineDash([]);

          // Label pill
          const label = `WALL ${e.price.toFixed(2)} · ${(avgQ / 1000).toFixed(1)}k`;
          const w = ctx.measureText(label).width + 10 * hpr;
          ctx.fillStyle = `rgba(${col},0.95)`;
          ctx.fillRect(xPx - w - 2 * hpr, yPx - 7 * hpr, w, 14 * hpr);
          ctx.fillStyle = "#fff";
          ctx.fillText(label, xPx - w + 3 * hpr, yPx);
        }
      }

      ctx.restore();
    });
  }
}

// ── Pane View ───────────────────────────────────────────────────────

class WallsPaneView implements IPrimitivePaneView {
  private _renderer: WallsRenderer;

  constructor(renderer: WallsRenderer) {
    this._renderer = renderer;
  }

  zOrder(): "top" {
    return "top";
  }

  renderer(): IPrimitivePaneRenderer {
    return this._renderer;
  }
}

// ── Primitive Implementation ────────────────────────────────────────

interface WallsPrimitiveOptions {
  walls: Wall[];
  depth: DepthSnapshot[];
  bars: BarData[];
  config: WallsConfig;
}

class WallsPrimitiveImpl implements ISeriesPrimitive<Time> {
  private _views: IPrimitivePaneView[];
  private _renderer: WallsRenderer;
  private _options: WallsPrimitiveOptions;

  constructor(options: WallsPrimitiveOptions) {
    this._options = options;
    this._renderer = new WallsRenderer(
      options.walls,
      options.depth,
      options.bars,
      options.config,
    );
    this._views = [new WallsPaneView(this._renderer)];
  }

  applyOptions(options: Partial<WallsPrimitiveOptions>): void {
    this._options = { ...this._options, ...options };
  }

  attached(param: SeriesAttachedParameter<Time>): void {
    this._renderer.update(
      this._options.walls,
      this._options.depth,
      this._options.bars,
      this._options.config,
      param.series as ISeriesApi<"Line", Time>,
      param.chart,
    );
  }

  detached(): void {
    this._renderer.update(
      this._options.walls,
      this._options.depth,
      this._options.bars,
      this._options.config,
      null,
      null,
    );
  }

  updateAllViews(): void {
    this._renderer.update(
      this._options.walls,
      this._options.depth,
      this._options.bars,
      this._options.config,
      null,
      null,
    );
  }

  paneViews(): readonly IPrimitivePaneView[] {
    return this._views;
  }
}

// ── React Component ─────────────────────────────────────────────────

interface LiquidityWallsProps {
  walls: Wall[];
  depth: DepthSnapshot[];
  bars: BarData[];
  config: WallsConfig;
  primitiveRef?: React.MutableRefObject<WallsPrimitiveImpl | null>;
}

export function LiquidityWalls({ walls, depth, bars, config, primitiveRef }: LiquidityWallsProps) {
  const implRef = useRef<WallsPrimitiveImpl | null>(null);

  useEffect(() => {
    if (implRef.current) {
      implRef.current.applyOptions({ walls, depth, bars, config });
    }
  }, [walls, depth, bars, config]);

  if (primitiveRef) {
    primitiveRef.current = implRef.current;
  }

  return null;
}

/** Factory: creates a primitive that can be attached to a series */
export function createWallsPrimitive(
  walls: Wall[],
  depth: DepthSnapshot[],
  bars: BarData[],
  config: WallsConfig,
): WallsPrimitiveImpl {
  return new WallsPrimitiveImpl({ walls, depth, bars, config });
}
