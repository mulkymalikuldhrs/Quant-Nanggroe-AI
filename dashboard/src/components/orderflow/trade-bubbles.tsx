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
import type { Trade, BubbleConfig } from "./types";

// ── Bubbles Renderer (ported from OrderFlowMap BubblesPrimitive) ─────

class BubblesRenderer implements IPrimitivePaneRenderer {
  private _trades: Trade[];
  private _config: BubbleConfig;
  private _series: ISeriesApi<"Line", Time> | null = null;
  private _chart: IChartApi | null = null;

  constructor(trades: Trade[], config: BubbleConfig) {
    this._trades = trades;
    this._config = config;
  }

  update(
    trades: Trade[],
    config: BubbleConfig,
    series: ISeriesApi<"Line", Time> | null,
    chart: IChartApi | null,
  ) {
    this._trades = trades;
    this._config = config;
    this._series = series;
    this._chart = chart;
  }

  draw(target: CanvasRenderingTarget2D): void {
    target.useBitmapCoordinateSpace((scope: BitmapCoordinatesRenderingScope) => {
      if (!this._config.visible || !this._series || !this._chart) return;
      if (this._trades.length === 0) return;

      const { context: ctx, bitmapSize, horizontalPixelRatio: hpr, verticalPixelRatio: vpr } = scope;
      const ts = this._chart.timeScale();

      // Find max qty for normalization
      const start = Math.max(0, this._trades.length - 3000);
      let gMax = 1;
      for (let i = start; i < this._trades.length; i++) {
        if (this._trades[i].qty > gMax) gMax = this._trades[i].qty;
      }

      const minR = this._config.minRadius * hpr;
      const maxR = this._config.maxRadius * hpr;
      const { scale, largeQty, minTrade, hollowSmall } = this._config;

      const sizeFn = (q: number): number => {
        let t: number;
        if (scale === "log") t = Math.log10(1 + q) / Math.log10(1 + gMax);
        else if (scale === "linear") t = q / gMax;
        else t = Math.sqrt(q / gMax); // sqrt default
        return minR + Math.max(0, Math.min(1, t)) * (maxR - minR);
      };

      ctx.save();

      // Pass 1: small/hollow trades
      for (let i = 0; i < this._trades.length; i++) {
        const tr = this._trades[i];
        if (tr.qty < minTrade) continue;
        if (tr.qty >= largeQty) continue;

        const x = ts.timeToCoordinate(tr.time as Time);
        if (x === null) continue;
        const y = this._series.priceToCoordinate(tr.price);
        if (y === null) continue;

        const xPx = x * hpr;
        const yPx = y * vpr;
        if (xPx < -50 || xPx > bitmapSize.width + 50) continue;

        const r = sizeFn(tr.qty);
        const fb = tr.side === "B" ? "38,166,154" : "239,83,80";

        if (hollowSmall) {
          ctx.beginPath();
          ctx.arc(xPx, yPx, r, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(${fb},0.16)`;
          ctx.fill();
          ctx.lineWidth = 1 * hpr;
          ctx.strokeStyle = `rgba(${fb},0.8)`;
          ctx.stroke();
        } else {
          const grd = ctx.createRadialGradient(xPx, yPx, r * 0.1, xPx, yPx, r);
          grd.addColorStop(0, `rgba(${fb},0.85)`);
          grd.addColorStop(0.7, `rgba(${fb},0.45)`);
          grd.addColorStop(1, `rgba(${fb},0.04)`);
          ctx.fillStyle = grd;
          ctx.beginPath();
          ctx.arc(xPx, yPx, r, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      // Pass 2: large trades with halo
      for (let i = 0; i < this._trades.length; i++) {
        const tr = this._trades[i];
        if (tr.qty < largeQty) continue;

        const x = ts.timeToCoordinate(tr.time as Time);
        if (x === null) continue;
        const y = this._series.priceToCoordinate(tr.price);
        if (y === null) continue;

        const xPx = x * hpr;
        const yPx = y * vpr;
        if (xPx < -60 || xPx > bitmapSize.width + 60) continue;

        const r = sizeFn(tr.qty);
        const fb = tr.side === "B" ? "38,166,154" : "239,83,80";
        const halo = tr.side === "B" ? "159,247,233" : "255,180,177";

        // Halo glow
        const hg = ctx.createRadialGradient(xPx, yPx, r * 0.4, xPx, yPx, r * 1.6);
        hg.addColorStop(0, `rgba(${halo},0.35)`);
        hg.addColorStop(1, `rgba(${halo},0)`);
        ctx.fillStyle = hg;
        ctx.beginPath();
        ctx.arc(xPx, yPx, r * 1.6, 0, Math.PI * 2);
        ctx.fill();

        // Solid core
        const grd = ctx.createRadialGradient(xPx, yPx, r * 0.1, xPx, yPx, r);
        grd.addColorStop(0, `rgba(${fb},1)`);
        grd.addColorStop(0.7, `rgba(${fb},0.65)`);
        grd.addColorStop(1, `rgba(${fb},0.1)`);
        ctx.fillStyle = grd;
        ctx.beginPath();
        ctx.arc(xPx, yPx, r, 0, Math.PI * 2);
        ctx.fill();

        // Border
        ctx.lineWidth = 1.5 * hpr;
        ctx.strokeStyle = `rgb(${halo})`;
        ctx.stroke();
      }

      ctx.restore();
    });
  }
}

// ── Pane View ───────────────────────────────────────────────────────

class BubblesPaneView implements IPrimitivePaneView {
  private _renderer: BubblesRenderer;

  constructor(renderer: BubblesRenderer) {
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

interface BubblesPrimitiveOptions {
  trades: Trade[];
  config: BubbleConfig;
}

class BubblesPrimitiveImpl implements ISeriesPrimitive<Time> {
  private _views: IPrimitivePaneView[];
  private _renderer: BubblesRenderer;
  private _options: BubblesPrimitiveOptions;

  constructor(options: BubblesPrimitiveOptions) {
    this._options = options;
    this._renderer = new BubblesRenderer(options.trades, options.config);
    this._views = [new BubblesPaneView(this._renderer)];
  }

  applyOptions(options: Partial<BubblesPrimitiveOptions>): void {
    this._options = { ...this._options, ...options };
  }

  attached(param: SeriesAttachedParameter<Time>): void {
    this._renderer.update(
      this._options.trades,
      this._options.config,
      param.series as ISeriesApi<"Line", Time>,
      param.chart,
    );
  }

  detached(): void {
    this._renderer.update(this._options.trades, this._options.config, null, null);
  }

  updateAllViews(): void {
    this._renderer.update(
      this._options.trades,
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

interface TradeBubblesProps {
  trades: Trade[];
  config: BubbleConfig;
  primitiveRef?: React.MutableRefObject<BubblesPrimitiveImpl | null>;
}

export function TradeBubbles({ trades, config, primitiveRef }: TradeBubblesProps) {
  const implRef = useRef<BubblesPrimitiveImpl | null>(null);

  useEffect(() => {
    if (implRef.current) {
      implRef.current.applyOptions({ trades, config });
    }
  }, [trades, config]);

  if (primitiveRef) {
    primitiveRef.current = implRef.current;
  }

  return null;
}

/** Factory: creates a primitive that can be attached to a series */
export function createBubblesPrimitive(
  trades: Trade[],
  config: BubbleConfig,
): BubblesPrimitiveImpl {
  return new BubblesPrimitiveImpl({ trades, config });
}
