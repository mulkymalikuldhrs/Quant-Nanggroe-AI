"use client";

import type { IChartApi, ISeriesApi, Time } from "lightweight-charts";
import type { CvdBar } from "./types";

// ── CVD Pane (Cumulative Volume Delta as BaselineSeries) ────────────
// Ported from OrderFlowMap: cvdSeries with BaselineSeries on pane index 1.
//
// This is a utility module, not a visual component — lightweight-charts series
// must live on the chart instance, not in React's render tree.
//
// Usage:
//   import { BaselineSeries } from 'lightweight-charts';
//   import { addCvdSeries, setCvdData } from './orderflow';
//   const cvdSeries = addCvdSeries(chart, BaselineSeries);
//   setCvdData(cvdSeries, cvdBarArray);

/** Add CVD BaselineSeries to chart's second pane (pane index 1) */
export function addCvdSeries(
  chart: IChartApi,
  BaselineSeriesDef: Parameters<IChartApi["addSeries"]>[0],
): ISeriesApi<"Baseline", Time> {
  const series = chart.addSeries(BaselineSeriesDef, {
    baseValue: { type: "price" as const, price: 0 },
    topLineColor: "#26a69a",
    topFillColor1: "rgba(38,166,154,.4)",
    topFillColor2: "rgba(38,166,154,.02)",
    bottomLineColor: "#ef5350",
    bottomFillColor1: "rgba(239,83,80,.02)",
    bottomFillColor2: "rgba(239,83,80,.4)",
    lineWidth: 2,
    priceLineVisible: true,
    lastValueVisible: true,
    priceFormat: { type: "price" as const, precision: 0, minMove: 1 },
    title: "CVD",
    priceScaleId: "cvd",
  }, 1) as unknown as ISeriesApi<"Baseline", Time>;

  chart.priceScale("cvd").applyOptions({
    scaleMargins: { top: 0.1, bottom: 0.1 },
    visible: true,
  });

  return series;
}

/** Set CVD series data from bar array */
export function setCvdData(series: ISeriesApi<"Baseline", Time>, data: CvdBar[]): void {
  series.setData(data.map((d) => ({ time: d.time as Time, value: d.value })));
}
