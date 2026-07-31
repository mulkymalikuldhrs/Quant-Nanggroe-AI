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
import type { HeatmapPrimitiveData, HeatmapConfig, ColorMapName, DepthLevel } from "./types";

// ── Color Maps (ported from OrderFlowMap) ────────────────────────────

type RGB = [number, number, number];

function rampStops(stops: RGB[], t: number): RGB {
  const clamped = Math.max(0, Math.min(1, t));
  const n = stops.length - 1;
  const i = Math.floor(clamped * n);
  if (i >= n) return stops[n];
  const frac = clamped * n - i;
  const a = stops[i];
  const b = stops[i + 1];
  return [
    a[0] + (b[0] - a[0]) * frac,
    a[1] + (b[1] - a[1]) * frac,
    a[2] + (b[2] - a[2]) * frac,
  ];
}

const CMAPS: Record<ColorMapName, { bid: (t: number) => RGB; ask: (t: number) => RGB }> = {
  bookmap: {
    bid: (t) => rampStops([[6, 10, 16], [6, 55, 65], [20, 140, 135], [125, 225, 210], [235, 255, 250]], t),
    ask: (t) => rampStops([[6, 10, 16], [60, 18, 18], [170, 40, 40], [245, 140, 90], [255, 235, 200]], t),
  },
  mono: {
    bid: (t) => rampStops([[8, 10, 14], [55, 60, 72], [135, 145, 160], [220, 225, 235], [255, 255, 255]], t),
    ask: (t) => rampStops([[8, 10, 14], [55, 60, 72], [135, 145, 160], [220, 225, 235], [255, 255, 255]], t),
  },
  inferno: {
    bid: (t) => rampStops([[0, 0, 4], [40, 11, 84], [120, 28, 109], [200, 55, 85], [252, 135, 40], [252, 255, 164]], t),
    ask: (t) => rampStops([[0, 0, 4], [40, 11, 84], [120, 28, 109], [200, 55, 85], [252, 135, 40], [252, 255, 164]], t),
  },
  viridis: {
    bid: (t) => rampStops([[68, 1, 84], [59, 82, 139], [33, 144, 141], [93, 201, 99], [253, 231, 37]], t),
    ask: (t) => rampStops([[68, 1, 84], [59, 82, 139], [33, 144, 141], [93, 201, 99], [253, 231, 37]], t),
  },
};

function rgba(c: RGB, a: number): string {
  return `rgba(${c[0] | 0},${c[1] | 0},${c[2] | 0},${a})`;
}

function roundTick(p: number, tick: number): number {
  return Math.round(p / tick) * tick;
}

// ── Primitive Renderer ──────────────────────────────────────────────

class HeatmapRenderer implements IPrimitivePaneRenderer {
  private _data: HeatmapPrimitiveData;
  private _config: HeatmapConfig;
  private _series: ISeriesApi<"Line", Time> | null = null;
  private _chart: IChartApi | null = null;
  private _tick: number;

  constructor(
    data: HeatmapPrimitiveData,
    config: HeatmapConfig,
    series: ISeriesApi<"Line", Time> | null,
    chart: IChartApi | null,
    tick: number,
  ) {
    this._data = data;
    this._config = config;
    this._series = series;
    this._chart = chart;
    this._tick = tick;
  }

  update(
    data: HeatmapPrimitiveData,
    config: HeatmapConfig,
    series: ISeriesApi<"Line", Time> | null,
    chart: IChartApi | null,
    tick: number,
  ) {
    this._data = data;
    this._config = config;
    this._series = series;
    this._chart = chart;
    this._tick = tick;
  }

  draw(target: CanvasRenderingTarget2D): void {
    target.useBitmapCoordinateSpace((scope: BitmapCoordinatesRenderingScope) => {
      if (!this._config.visible || !this._series || !this._chart) return;
      const { context: ctx, bitmapSize, horizontalPixelRatio: hpr, verticalPixelRatio: vpr } = scope;
      if (this._data.depth.length === 0) return;

      const ts = this._chart.timeScale();
      const lr = ts.getVisibleLogicalRange();
      if (!lr) return;

      const barSpacing = ts.options().barSpacing || 6;
      const colW = Math.max(1, Math.floor(barSpacing * hpr));
      const rowH = Math.max(2, Math.floor(this._config.rowHeight * hpr));
      const { intensity, gamma, minQty, colorMap } = this._config;

      // Compute global max qty for normalization
      const bars = this._data.bars;
      const startTime = bars[Math.max(0, Math.floor(lr.from))]?.time ?? this._data.depth[0].time;
      const endTime = bars[Math.min(bars.length - 1, Math.ceil(lr.to))]?.time ?? this._data.depth[this._data.depth.length - 1].time;

      let gMax = 1;
      for (let i = 0; i < this._data.depth.length; i++) {
        const d = this._data.depth[i];
        if (d.time < startTime - 30 || d.time > endTime + 30) continue;
        for (const lv of d.bids) if (lv.qty > gMax) gMax = lv.qty;
        for (const lv of d.asks) if (lv.qty > gMax) gMax = lv.qty;
      }
      const norm = 1 / gMax;

      ctx.save();
      for (let i = 0; i < this._data.depth.length; i++) {
        const d = this._data.depth[i];
        const x = ts.timeToCoordinate(d.time as Time);
        if (x === null) continue;
        const xPx = Math.round(x * hpr) - Math.floor(colW / 2);
        if (xPx + colW < 0 || xPx > bitmapSize.width) continue;

        for (let s = 0; s < 2; s++) {
          const arr = s === 0 ? d.bids : d.asks;
          const side: "bid" | "ask" = s === 0 ? "bid" : "ask";

          // Group levels into same tick bucket and sum
          const bucketed: Record<number, number> = {};
          for (const lv of arr) {
            const roundedPrice = roundTick(lv.price, this._tick);
            bucketed[roundedPrice] = (bucketed[roundedPrice] || 0) + lv.qty;
          }

          for (const bp in bucketed) {
            const bQty = bucketed[bp];
            if (bQty < minQty) continue;
            const y = this._series.priceToCoordinate(parseFloat(bp));
            if (y === null) continue;
            let t = bQty * norm * intensity;
            t = Math.pow(Math.max(0, Math.min(1, t)), gamma);
            if (t <= 0.02) continue;
            ctx.fillStyle = rgba(CMAPS[colorMap][side](t), 0.92);
            const yPx = Math.round(y * vpr) - Math.floor(rowH / 2);
            ctx.fillRect(xPx, yPx, colW, rowH);
          }
        }
      }
      ctx.restore();
    });
  }
}

// ── Primitive View + Implementation ─────────────────────────────────

class HeatmapPaneView implements IPrimitivePaneView {
  private _renderer: HeatmapRenderer;

  constructor(renderer: HeatmapRenderer) {
    this._renderer = renderer;
  }

  zOrder(): "bottom" {
    return "bottom";
  }

  renderer(): IPrimitivePaneRenderer {
    return this._renderer;
  }
}

interface HeatmapPrimitiveOptions {
  data: HeatmapPrimitiveData;
  config: HeatmapConfig;
  tick?: number;
}

class HeatmapPrimitiveImpl implements ISeriesPrimitive<Time> {
  private _views: IPrimitivePaneView[] = [];
  private _renderer: HeatmapRenderer;
  private _options: HeatmapPrimitiveOptions;
  private _requestUpdate: (() => void) | null = null;

  constructor(options: HeatmapPrimitiveOptions) {
    this._options = options;
    this._renderer = new HeatmapRenderer(
      options.data,
      options.config,
      null,
      null,
      options.tick ?? 0.1,
    );
    this._views = [new HeatmapPaneView(this._renderer)];
  }

  applyOptions(options: Partial<HeatmapPrimitiveOptions>): void {
    this._options = { ...this._options, ...options };
    this._renderer.update(
      this._options.data,
      this._options.config,
      null,
      null,
      this._options.tick ?? 0.1,
    );
  }

  attached(param: SeriesAttachedParameter<Time>): void {
    this._requestUpdate = param.requestUpdate;
    this._renderer.update(
      this._options.data,
      this._options.config,
      param.series as ISeriesApi<"Line", Time>,
      param.chart,
      this._options.tick ?? 0.1,
    );
  }

  detached(): void {
    this._requestUpdate = null;
  }

  updateAllViews(): void {
    this._renderer.update(
      this._options.data,
      this._options.config,
      null,
      null,
      this._options.tick ?? 0.1,
    );
  }

  paneViews(): readonly IPrimitivePaneView[] {
    return this._views;
  }
}

// ── React Component ─────────────────────────────────────────────────

interface OrderflowHeatmapProps {
  data: HeatmapPrimitiveData;
  config: HeatmapConfig;
  tick?: number;
  /** Expose primitive for external update */
  primitiveRef?: React.MutableRefObject<HeatmapPrimitiveImpl | null>;
}

export function OrderflowHeatmap({ data, config, tick = 0.1, primitiveRef }: OrderflowHeatmapProps) {
  const implRef = useRef<HeatmapPrimitiveImpl | null>(null);

  // Store/update options on the primitive
  useEffect(() => {
    if (implRef.current) {
      implRef.current.applyOptions({ data, config, tick });
    }
  }, [data, config, tick]);

  if (primitiveRef) {
    primitiveRef.current = implRef.current;
  }

  // The primitive is created and needs to be attached by the parent chart component.
  // We export the factory so the chart component can call attachPrimitive(impl).
  // For standalone usage, the parent creates the primitive and attaches it.
  return null;
}

/** Factory: creates a primitive that can be attached to a series */
export function createHeatmapPrimitive(
  data: HeatmapPrimitiveData,
  config: HeatmapConfig,
  tick = 0.1,
): HeatmapPrimitiveImpl {
  return new HeatmapPrimitiveImpl({ data, config, tick });
}
