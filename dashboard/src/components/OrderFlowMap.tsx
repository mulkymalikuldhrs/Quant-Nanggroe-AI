"use client";

import { useEffect, useRef, useState, useCallback } from "react";

/* =====================================================================
   OrderFlowMap — Bookmap-style visualization for Quant-Nanggroe-AI
   Adapted from vanilla JS OrderFlowMap to React/TypeScript
   Supports crypto/forex instruments with configurable tick sizes
   ===================================================================== */

interface DepthLevel { p: number; q: number; o: number; }
interface DepthSnapshot { time: number; bids: DepthLevel[]; asks: DepthLevel[]; }
interface BarSnapshot { time: number; mid: number; bbid: number; bask: number; vwap: number; _vN: number; _vD: number; }
interface Trade { time: number; price: number; qty: number; side: "B" | "S"; }
interface CvBar { time: number; value: number; }

function clamp(x: number, a: number, b: number) { return x < a ? a : (x > b ? b : x); }
function mix(a: number[], b: number[], t: number) {
  return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
}
function rgba(c: number[], a: number) { return `rgba(${c[0] | 0},${c[1] | 0},${c[2] | 0},${a})`; }
function gauss() {
  let u = 0, v = 0;
  while (u === 0) u = Math.random();
  while (v === 0) v = Math.random();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

function rampStops(stops: number[][], t: number) {
  t = clamp(t, 0, 1);
  const n = stops.length - 1;
  const i = Math.floor(t * n);
  if (i >= n) return stops[n];
  return mix(stops[i], stops[i + 1], t * n - i);
}

const CMAPS: Record<string, { bid: (t: number) => number[]; ask: (t: number) => number[] }> = {
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

export default function OrderFlowMap({
  symbol = "BTC-USD",
  tick = 0.01,
  initialMid = 67500,
}: {
  symbol?: string;
  tick?: number;
  initialMid?: number;
}) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const [running, setRunning] = useState(true);
  const [speed, setSpeed] = useState(250);
  const [lastPrice, setLastPrice] = useState(initialMid);
  const [spread, setSpread] = useState(0);
  const [cvd, setCvd] = useState(0);
  const [imbalance, setImbalance] = useState("--");
  const [fps, setFps] = useState(0);
  const [tradesCount, setTradesCount] = useState(0);
  const [barsCount, setBarsCount] = useState(0);
  const [snapshotsCount, setSnapshotsCount] = useState(0);
  const [microStats, setMicroStats] = useState({ tradesPerSec: 0, avgSize: 0, buyPct: 50, sellPct: 50 });
  const [tapeEntries, setTapeEntries] = useState<Trade[]>([]);
  const [domLevels, setDomLevels] = useState<{ bid: DepthLevel; ask: DepthLevel; spread: number }[]>([]);
  const [heatmapCfg, setHeatmapCfg] = useState({ intensity: 1.2, gamma: 0.65, rowH: 5, visible: true, colorMap: "bookmap" });
  const [bubbleCfg, setBubbleCfg] = useState({ visible: true, minPx: 2, maxPx: 26, scale: "sqrt", largeQty: 500, hollowSmall: true });
  const [overlayCfg, setOverlayCfg] = useState({ showBBA: true, showVWAP: true, showVP: true, showCVD: true, showWalls: true });

  const TICK = tick;
  const DEPTH_LEVELS = 5;
  const LEVEL_SPACE = 5;

  const barsRef = useRef<BarSnapshot[]>([]);
  const depthRef = useRef<DepthSnapshot[]>([]);
  const tradesRef = useRef<Trade[]>([]);
  const cvdBarsRef = useRef<CvBar[]>([]);
  const cvdRef = useRef(0);
  const tradeVolByPriceRef = useRef<Map<number, number>>(new Map());
  const midRef = useRef(initialMid);
  const regimeRef = useRef({ drift: 0, vol: 0.6, sweep: 0, sweepDir: 0, sweepLeft: 0, iceberg: null as any });
  const fpsRef = useRef({ frames: 0, last: performance.now() });

  const roundTick = useCallback((p: number) => {
    if (TICK >= 1) return Math.round(p / TICK) * TICK;
    const decimals = Math.max(0, Math.ceil(-Math.log10(TICK)));
    return parseFloat((Math.round(p / TICK) * TICK).toFixed(decimals));
  }, [TICK]);

  // Chart Setup
  useEffect(() => {
    if (!chartContainerRef.current) return;
    let disposed = false;

    import("lightweight-charts").then((LWC) => {
      if (disposed || !chartContainerRef.current) return;
      const { createChart, LineSeries, BaselineSeries, CrosshairMode } = LWC;

      const chart = createChart(chartContainerRef.current, {
        layout: { background: { type: "solid", color: "#080b10" }, textColor: "#aab3c1" },
        grid: { vertLines: { color: "rgba(35,45,60,.3)" }, horzLines: { color: "rgba(35,45,60,.3)" } },
        crosshair: { mode: CrosshairMode.Normal },
        rightPriceScale: { borderColor: "#1c2533", scaleMargins: { top: 0.08, bottom: 0.08 } },
        timeScale: { borderColor: "#1c2533", timeVisible: true, secondsVisible: true, rightOffset: 3, barSpacing: 6 },
        autoSize: true,
      });

      const fmt = TICK < 1 ? Math.max(0, Math.ceil(-Math.log10(TICK))) : TICK < 10 ? 2 : 0;
      const midSeries = chart.addSeries(LineSeries, { color: "rgba(255,255,255,0)", lineWidth: 1, priceLineVisible: false, lastValueVisible: false, priceFormat: { type: "price", precision: fmt, minMove: TICK } });
      const bidSeries = chart.addSeries(LineSeries, { color: "#26a69a", lineWidth: 1, priceLineVisible: false, lastValueVisible: false, priceFormat: { type: "price", precision: fmt, minMove: TICK } });
      const askSeries = chart.addSeries(LineSeries, { color: "#ef5350", lineWidth: 1, priceLineVisible: false, lastValueVisible: false, priceFormat: { type: "price", precision: fmt, minMove: TICK } });
      const vwapSeries = chart.addSeries(LineSeries, { color: "#f5c542", lineWidth: 2, priceLineVisible: false, lastValueVisible: true, priceFormat: { type: "price", precision: fmt, minMove: TICK }, title: "VWAP" });
      const cvdSeries = chart.addSeries(BaselineSeries, {
        baseValue: { type: "price", price: 0 },
        topLineColor: "#26a69a", topFillColor1: "rgba(38,166,154,.4)", topFillColor2: "rgba(38,166,154,.02)",
        bottomLineColor: "#ef5350", bottomFillColor1: "rgba(239,83,80,.02)", bottomFillColor2: "rgba(239,83,80,.4)",
        lineWidth: 2, priceLineVisible: true, lastValueVisible: true,
        priceFormat: { type: "price", precision: 0, minMove: 1 }, title: "CVD", priceScaleId: "cvd",
      } as any);
      chart.priceScale("cvd").applyOptions({ scaleMargins: { top: 0.1, bottom: 0.1 }, visible: true });

      chartRef.current = { chart, midSeries, bidSeries, askSeries, vwapSeries, cvdSeries };
      seedHistory();
    });

    return () => { disposed = true; chartRef.current?.chart?.remove(); chartRef.current = null; };
  }, []);

  const seedHistory = useCallback(() => {
    const now = Math.floor(Date.now() / 1000);
    const bars = barsRef.current;
    const depth = depthRef.current;
    const trades = tradesRef.current;
    const cvdBars = cvdBarsRef.current;
    let cvdVal = 0;

    for (let i = 300; i > 0; i--) {
      const t = now - i;
      const drift = gauss() * (TICK < 1 ? TICK * 10 : TICK * 0.5);
      midRef.current = roundTick(midRef.current + drift);
      const halfSpread = Math.max(TICK, roundTick(TICK * 5));
      const bbid = roundTick(midRef.current - halfSpread);
      const bask = roundTick(midRef.current + halfSpread);

      const bidsL: DepthLevel[] = [];
      const asksL: DepthLevel[] = [];
      for (let j = 0; j < DEPTH_LEVELS; j++) {
        bidsL.push({ p: roundTick(bbid - j * TICK * LEVEL_SPACE), q: Math.round(180 + j * 120 + Math.random() * 100), o: 1 + (Math.random() * 8 | 0) });
        asksL.push({ p: roundTick(bask + j * TICK * LEVEL_SPACE), q: Math.round(180 + j * 120 + Math.random() * 100), o: 1 + (Math.random() * 8 | 0) });
      }
      depth.push({ time: t, bids: bidsL, asks: asksL });

      const side: "B" | "S" = Math.random() < 0.5 ? "B" : "S";
      const price = side === "B" ? bask : bbid;
      const qty = Math.max(1, Math.round(Math.exp(2.4 + Math.abs(gauss()) * 1.1)));
      trades.push({ time: t, price, qty, side });
      cvdVal += side === "B" ? qty : -qty;
      cvdBars.push({ time: t, value: cvdVal });
      tradeVolByPriceRef.current.set(price, (tradeVolByPriceRef.current.get(price) || 0) + qty);

      const vN = (bars.length ? bars[bars.length - 1]._vN : 0) + price * qty;
      const vD = (bars.length ? bars[bars.length - 1]._vD : 0) + qty;
      bars.push({ time: t, mid: midRef.current, bbid, bask, vwap: vN / vD, _vN: vN, _vD: vD });
    }

    if (chartRef.current) {
      const { midSeries, bidSeries, askSeries, vwapSeries, cvdSeries } = chartRef.current;
      midSeries.setData(bars.map(b => ({ time: b.time as any, value: b.mid })));
      bidSeries.setData(bars.map(b => ({ time: b.time as any, value: b.bbid })));
      askSeries.setData(bars.map(b => ({ time: b.time as any, value: b.bask })));
      vwapSeries.setData(bars.map(b => ({ time: b.time as any, value: b.vwap })));
      cvdSeries.setData(cvdBars.map(c => ({ time: c.time as any, value: c.value })));
    }

    setBarsCount(bars.length);
    setTradesCount(trades.length);
    setSnapshotsCount(depth.length);
    setLastPrice(midRef.current);
    setCvd(cvdVal);
  }, [roundTick, TICK, DEPTH_LEVELS, LEVEL_SPACE]);

  // Tick Loop
  useEffect(() => {
    if (!running) return;
    const interval = setInterval(() => {
      if (!chartRef.current) return;
      const now = Math.floor(Date.now() / 1000);
      simulateTick(now);

      fpsRef.current.frames++;
      const elapsed = performance.now() - fpsRef.current.last;
      if (elapsed >= 1000) {
        setFps(Math.round(fpsRef.current.frames * 1000 / elapsed));
        fpsRef.current.frames = 0;
        fpsRef.current.last = performance.now();
      }
    }, speed);
    return () => clearInterval(interval);
  }, [running, speed]);

  const simulateTick = useCallback((now: number) => {
    const regime = regimeRef.current;
    const bars = barsRef.current;
    const depth = depthRef.current;
    const trades = tradesRef.current;
    const cvdBars = cvdBarsRef.current;

    regime.drift += gauss() * 0.0008 - regime.drift * 0.02;
    regime.vol = clamp(regime.vol + gauss() * 0.04, 0.3, 1.6);
    if (regime.sweepLeft <= 0 && Math.random() < 0.012) {
      regime.sweepDir = Math.random() < 0.5 ? -1 : 1;
      regime.sweepLeft = 8 + (Math.random() * 22) | 0;
      regime.sweep = (0.4 + Math.random() * 0.8) * regime.sweepDir;
    } else if (regime.sweepLeft > 0) {
      regime.sweepLeft--;
      if (regime.sweepLeft === 0) regime.sweep = 0;
    }

    const step = (regime.drift + regime.sweep * 0.6 + gauss() * regime.vol) * TICK;
    midRef.current = roundTick(midRef.current + step);
    const halfSpread = Math.max(TICK, roundTick(TICK * 5));
    const bbid = roundTick(midRef.current - halfSpread);
    const bask = roundTick(midRef.current + halfSpread);

    const bidsL: DepthLevel[] = [];
    const asksL: DepthLevel[] = [];
    for (let i = 0; i < DEPTH_LEVELS; i++) {
      const pB = roundTick(bbid - i * TICK * LEVEL_SPACE);
      const pA = roundTick(bask + i * TICK * LEVEL_SPACE);
      let qB = (180 + i * 120) * (0.6 + Math.random() * 0.8);
      let qA = (180 + i * 120) * (0.6 + Math.random() * 0.8);
      if (regime.sweepDir > 0) qA *= 0.5 + Math.random() * 0.4;
      if (regime.sweepDir < 0) qB *= 0.5 + Math.random() * 0.4;
      bidsL.push({ p: pB, q: Math.round(qB), o: 1 + (Math.random() * 8 | 0) });
      asksL.push({ p: pA, q: Math.round(qA), o: 1 + (Math.random() * 8 | 0) });
    }
    depth.push({ time: now, bids: bidsL, asks: asksL });

    const nTrades = Math.random() < 0.85 ? 1 : 2;
    for (let k = 0; k < nTrades; k++) {
      const topBidQ = bidsL[0].q, topAskQ = asksL[0].q;
      const imb = (topBidQ - topAskQ) / (topBidQ + topAskQ);
      const pBuy = clamp(0.5 + 0.25 * regime.sweep + 0.2 * imb + 0.3 * regime.drift * 100, 0.05, 0.95);
      const side: "B" | "S" = Math.random() < pBuy ? "B" : "S";
      const price = side === "B" ? bask : bbid;
      let qty = Math.max(1, Math.round(Math.exp(2.4 + Math.abs(gauss()) * 1.1)));
      if (Math.random() < 0.04) qty *= (3 + (Math.random() * 8 | 0));
      trades.push({ time: now, price, qty, side });
      cvdRef.current += side === "B" ? qty : -qty;
      tradeVolByPriceRef.current.set(price, (tradeVolByPriceRef.current.get(price) || 0) + qty);
    }

    const vN = bars.length ? bars[bars.length - 1]._vN : 0;
    const vD = bars.length ? bars[bars.length - 1]._vD : 0;
    const lastTrades = trades.filter(t => t.time === now);
    let secVN = vN, secVD = vD;
    for (const tr of lastTrades) { secVN += tr.price * tr.qty; secVD += tr.qty; }
    const vwap = secVD > 0 ? secVN / secVD : midRef.current;
    bars.push({ time: now, mid: midRef.current, bbid, bask, vwap, _vN: secVN, _vD: secVD });
    cvdBars.push({ time: now, value: cvdRef.current });

    if (chartRef.current) {
      const { midSeries, bidSeries, askSeries, vwapSeries, cvdSeries } = chartRef.current;
      midSeries.update({ time: now as any, value: midRef.current });
      bidSeries.update({ time: now as any, value: bbid });
      askSeries.update({ time: now as any, value: bask });
      vwapSeries.update({ time: now as any, value: vwap });
      cvdSeries.update({ time: now as any, value: cvdRef.current });
    }

    setLastPrice(midRef.current);
    setSpread(bask - bbid);
    setCvd(cvdRef.current);
    setImbalance(`${((bidsL[0].q - asksL[0].q) / (bidsL[0].q + asksL[0].q) * 100).toFixed(1)}%`);
    setBarsCount(bars.length);
    setTradesCount(trades.length);
    setSnapshotsCount(depth.length);

    const newDom: typeof domLevels = [];
    for (let i = 0; i < DEPTH_LEVELS; i++) newDom.push({ bid: bidsL[i], ask: asksL[i], spread: i === 0 ? bask - bbid : 0 });
    setDomLevels(newDom);

    const recentTrades = trades.slice(-80);
    setTapeEntries(recentTrades);

    // Micro stats
    const recent = trades.filter(t => t.time >= now - 60);
    const buyQty = recent.filter(t => t.side === "B").reduce((s, t) => s + t.qty, 0);
    const sellQty = recent.filter(t => t.side === "S").reduce((s, t) => s + t.qty, 0);
    const total = buyQty + sellQty;
    setMicroStats({
      tradesPerSec: recent.length > 0 ? +(recent.length / Math.min(60, now - (recent[0]?.time || now) + 1)).toFixed(1) : 0,
      avgSize: recent.length > 0 ? Math.round(total / recent.length) : 0,
      buyPct: total > 0 ? Math.round(buyQty / total * 100) : 50,
      sellPct: total > 0 ? Math.round(sellQty / total * 100) : 50,
    });
  }, [roundTick, TICK, DEPTH_LEVELS, LEVEL_SPACE]);

  // Keyboard
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement) return;
      switch (e.code) {
        case "Space": e.preventDefault(); setRunning(r => !r); break;
        case "KeyH": setHeatmapCfg(c => ({ ...c, visible: !c.visible })); break;
        case "KeyB": setBubbleCfg(c => ({ ...c, visible: !c.visible })); break;
        case "KeyV": setOverlayCfg(c => ({ ...c, showVWAP: !c.showVWAP })); break;
        case "KeyC": setOverlayCfg(c => ({ ...c, showCVD: !c.showCVD })); break;
        case "KeyF": chartRef.current?.chart?.timeScale().fitContent(); break;
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const fmtPrice = (p: number) => TICK < 1 ? p.toFixed(Math.max(0, Math.ceil(-Math.log10(TICK)))) : p.toLocaleString();

  return (
    <div className="h-full flex flex-col bg-[#080b10] text-[#d6dde8] font-sans text-xs overflow-hidden">
      {/* Header */}
      <header className="h-11 flex items-center gap-3 px-3 bg-gradient-to-b from-[#10161f] to-[#0a0f17] border-b border-[#1c2533]">
        <div className="font-extrabold text-sm tracking-wide text-white">
          Order<span className="bg-gradient-to-r from-[#3aa0ff] to-[#7c5cff] bg-clip-text text-transparent">Flow</span>
        </div>
        <div className="px-2 py-1 bg-[#1a2433] border border-[#263246] rounded font-bold text-white">{symbol}</div>
        <div className="font-bold text-sm font-mono min-w-[70px]">{fmtPrice(lastPrice)}</div>
        <div className="w-px h-5 bg-[#1c2533]" />
        <div className="flex flex-col leading-tight">
          <span className="text-[9px] uppercase tracking-wider text-[#7a8597]">CVD</span>
          <b className={`font-semibold font-mono text-xs ${cvd >= 0 ? "text-[#7fdcd0]" : "text-[#ff8a87]"}`}>{cvd.toLocaleString()}</b>
        </div>
        <div className="flex flex-col leading-tight">
          <span className="text-[9px] uppercase tracking-wider text-[#7a8597]">Imbalance</span>
          <b className="text-white font-semibold font-mono text-xs">{imbalance}</b>
        </div>
        <div className="ml-auto flex items-center gap-1.5">
          <button onClick={() => setRunning(r => !r)} className="px-2 py-1 bg-[#1a2433] border border-[#263246] rounded text-xs hover:bg-[#243149] transition-colors">
            {running ? "⏸ Pause" : "▶ Play"}
          </button>
          <select value={speed} onChange={e => setSpeed(+e.target.value)} className="px-2 py-1 bg-[#1a2433] border border-[#263246] rounded text-xs appearance-none cursor-pointer">
            <option value={1000}>1×</option>
            <option value={500}>2×</option>
            <option value={250}>4×</option>
            <option value={100}>10×</option>
          </select>
        </div>
      </header>

      <div className="flex-1 flex min-h-0">
        {/* Left Controls */}
        <aside className="w-52 bg-[#0e131b] border-r border-[#1c2533] overflow-y-auto p-2 space-y-2">
          <div className="bg-[#131923] border border-[#1c2533] rounded-md overflow-hidden">
            <h4 className="m-0 text-[10px] uppercase tracking-wider text-[#9aa6b8] font-bold px-2.5 py-1.5 bg-[#0d121a]">
              Heatmap <span className="text-[#3aa0ff]">●</span>
            </h4>
            <div className="p-2 space-y-1.5">
              <label className="flex items-center gap-1.5 cursor-pointer text-[11px] text-[#aab3c1]">
                <input type="checkbox" checked={heatmapCfg.visible} onChange={e => setHeatmapCfg(c => ({ ...c, visible: e.target.checked }))} className="accent-[#3aa0ff]" />
                Visible
              </label>
              <div className="flex items-center justify-between gap-2">
                <label className="text-[11px] text-[#aab3c1]">Intensity</label>
                <input type="range" min={0.1} max={3} step={0.05} value={heatmapCfg.intensity} onChange={e => setHeatmapCfg(c => ({ ...c, intensity: +e.target.value }))} className="flex-1 accent-[#3aa0ff] h-3" />
                <span className="text-[11px] font-mono text-white font-semibold min-w-[30px] text-right">{heatmapCfg.intensity}</span>
              </div>
              <div className="flex items-center justify-between gap-2">
                <label className="text-[11px] text-[#aab3c1]">Gamma</label>
                <input type="range" min={0.3} max={2.5} step={0.05} value={heatmapCfg.gamma} onChange={e => setHeatmapCfg(c => ({ ...c, gamma: +e.target.value }))} className="flex-1 accent-[#3aa0ff] h-3" />
                <span className="text-[11px] font-mono text-white font-semibold min-w-[30px] text-right">{heatmapCfg.gamma}</span>
              </div>
            </div>
          </div>

          <div className="bg-[#131923] border border-[#1c2533] rounded-md overflow-hidden">
            <h4 className="m-0 text-[10px] uppercase tracking-wider text-[#9aa6b8] font-bold px-2.5 py-1.5 bg-[#0d121a]">
              Overlays
            </h4>
            <div className="p-2 space-y-1.5">
              {(["showBBA", "showVWAP", "showVP", "showCVD", "showWalls"] as const).map(key => (
                <label key={key} className="flex items-center gap-1.5 cursor-pointer text-[11px] text-[#aab3c1]">
                  <input type="checkbox" checked={overlayCfg[key]} onChange={e => setOverlayCfg(c => ({ ...c, [key]: e.target.checked }))} className="accent-[#3aa0ff]" />
                  {key === "showBBA" ? "Best Bid/Ask" : key === "showVWAP" ? "VWAP" : key === "showVP" ? "Volume Profile" : key === "showCVD" ? "CVD" : "Liquidity Walls"}
                </label>
              ))}
            </div>
          </div>

          <div className="bg-[#131923] border border-[#1c2533] rounded-md overflow-hidden">
            <h4 className="m-0 text-[10px] uppercase tracking-wider text-[#9aa6b8] font-bold px-2.5 py-1.5 bg-[#0d121a]">Shortcuts</h4>
            <div className="p-2 text-[10px] text-[#7a8597] leading-relaxed">
              Space → Play/Pause · F → Fit<br />
              H → Heatmap · B → Bubbles<br />
              V → VWAP · C → CVD
            </div>
          </div>
        </aside>

        {/* Center Chart */}
        <div className="flex-1 relative min-w-0">
          <div ref={chartContainerRef} className="w-full h-full" />
          <div className="absolute top-2.5 left-3 bg-[rgba(8,11,16,.8)] border border-[#1c2533] px-2.5 py-2 rounded-md backdrop-blur text-[11px] z-10 pointer-events-none leading-relaxed">
            <div className="font-bold text-white text-[10px] uppercase tracking-wider mb-1">Order Flow</div>
            <div>
              <span className="inline-block w-2 h-2 rounded-full bg-[#26a69a] mr-1" />Best Bid{" "}
              <span className="inline-block w-2 h-2 rounded-full bg-[#ef5350] mr-1" />Best Ask{" "}
              <span className="inline-block w-2 h-2 rounded-full bg-[#f5c542] mr-1" />VWAP
            </div>
          </div>
        </div>

        {/* Right: DOM + Tape */}
        <aside className="w-56 bg-[#0e131b] border-l border-[#1c2533] flex flex-col gap-2 p-2 overflow-hidden">
          <div className="bg-[#131923] border border-[#1c2533] rounded-md overflow-hidden flex-shrink-0">
            <h4 className="m-0 text-[10px] uppercase tracking-wider text-[#9aa6b8] font-bold px-2.5 py-1.5 bg-[#0d121a]">L2 Depth · {DEPTH_LEVELS}</h4>
            <div className="p-1.5">
              <div className="font-mono text-[11px] border border-[#1c2533] rounded overflow-hidden bg-[#0a0f17]">
                <div className="grid grid-cols-[1fr_60px_1fr] text-[#7a8597] text-[9px] uppercase tracking-wider px-1 py-1 bg-[#0d121a] text-center font-bold">
                  <div>BID</div><div>PRICE</div><div>ASK</div>
                </div>
                {domLevels.length === 0 ? (
                  <div className="p-2 text-center text-[#7a8597] italic text-[10px]">Waiting…</div>
                ) : (
                  <>
                    {domLevels.slice().reverse().map((lvl, i) => (
                      <div key={`a-${i}`} className="grid grid-cols-[1fr_60px_1fr] h-[18px] items-center border-b border-[#11161f]">
                        <div />
                        <div className="text-center font-bold text-[#ffb4b1] bg-[#0a0f17] text-[11px]">{fmtPrice(lvl.ask.p)}</div>
                        <div className="text-left px-2 text-[#dde3ee] text-[11px]">{lvl.ask.q}</div>
                      </div>
                    ))}
                    <div className="grid grid-cols-[1fr_60px_1fr] text-center py-0.5 border-y border-[#1c2533]">
                      <div />
                      <div className="text-[#3aa0ff] bg-[#0d1622] text-[10px] font-semibold">{fmtPrice(spread)}</div>
                      <div />
                    </div>
                    {domLevels.map((lvl, i) => (
                      <div key={`b-${i}`} className="grid grid-cols-[1fr_60px_1fr] h-[18px] items-center border-b border-[#11161f]">
                        <div className="text-right px-2 text-[#dde3ee] text-[11px]">{lvl.bid.q}</div>
                        <div className="text-center font-bold text-[#7fdcd0] bg-[#0a0f17] text-[11px]">{fmtPrice(lvl.bid.p)}</div>
                        <div />
                      </div>
                    ))}
                  </>
                )}
              </div>
            </div>
          </div>

          <div className="bg-[#131923] border border-[#1c2533] rounded-md overflow-hidden flex-shrink-0">
            <h4 className="m-0 text-[10px] uppercase tracking-wider text-[#9aa6b8] font-bold px-2.5 py-1.5 bg-[#0d121a]">Microstructure</h4>
            <div className="p-1.5 grid grid-cols-2 gap-1">
              {[
                { label: "Trades/s", value: microStats.tradesPerSec },
                { label: "Avg size", value: microStats.avgSize },
                { label: "Buy %", value: `${microStats.buyPct}%`, cls: "text-[#7fdcd0]" },
                { label: "Sell %", value: `${microStats.sellPct}%`, cls: "text-[#ff8a87]" },
              ].map(s => (
                <div key={s.label} className="bg-[#0a0f17] border border-[#1c2533] rounded px-1.5 py-1">
                  <div className="text-[9px] uppercase text-[#7a8597]">{s.label}</div>
                  <div className={`text-[13px] font-bold font-mono ${s.cls || "text-white"}`}>{s.value}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="flex-1 bg-[#131923] border border-[#1c2533] rounded-md overflow-hidden flex flex-col min-h-0">
            <h4 className="m-0 text-[10px] uppercase tracking-wider text-[#9aa6b8] font-bold px-2.5 py-1.5 bg-[#0d121a] flex-shrink-0">Time & Sales</h4>
            <div className="p-1.5 flex-1 min-h-0">
              <div className="font-mono text-[11px] h-full overflow-y-auto border border-[#1c2533] rounded bg-[#0a0f17]">
                <div className="grid grid-cols-[45px_1fr_45px] gap-1 px-1.5 py-1 bg-[#0d121a] text-[#7a8597] text-[9px] uppercase font-bold sticky top-0 z-10 border-b border-[#1c2533]">
                  <div>Time</div><div className="text-right">Price</div><div className="text-right">Qty</div>
                </div>
                {tapeEntries.length === 0 ? (
                  <div className="p-3 text-center text-[#7a8597] italic">Waiting…</div>
                ) : (
                  tapeEntries.slice().reverse().map((t, i) => (
                    <div key={i} className={`grid grid-cols-[45px_1fr_45px] gap-1 px-1.5 border-b border-[#11161f] leading-relaxed ${
                      t.side === "B" ? "bg-[rgba(38,166,154,.07)] text-[#7fdcd0]" : "bg-[rgba(239,83,80,.07)] text-[#f1a4a2]"
                    }`}>
                      <div>{new Date(t.time * 1000).toLocaleTimeString("en", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</div>
                      <div className="text-right font-semibold">{fmtPrice(t.price)}</div>
                      <div className="text-right text-[#aab3c1]">{t.qty}</div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </aside>
      </div>

      {/* Footer */}
      <footer className="h-6 flex items-center gap-3.5 px-3 bg-[#0a0f17] border-t border-[#1c2533] text-[#7a8597] text-[10px] font-mono">
        <div>
          <span className={`inline-block w-[7px] h-[7px] rounded-full mr-1 ${running ? "bg-[#3acf6f] shadow-[0_0_6px_#3acf6f] animate-pulse" : "bg-[#555]"}`} />
          {running ? "Streaming…" : "Paused"}
        </div>
        <div>Bars <b className="text-white font-semibold">{barsCount}</b> · Trades <b className="text-white font-semibold">{tradesCount}</b></div>
        <div className="ml-auto">FPS <b className="text-white font-semibold">{fps}</b></div>
      </footer>
    </div>
  );
}
