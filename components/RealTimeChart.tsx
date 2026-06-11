
import React, { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, CrosshairMode, IChartApi, ISeriesApi } from 'lightweight-charts';
import { ChartPoint, CandleData } from '../types';
import { MathEngine } from '../services/math_engine';

interface Props {
    data: (ChartPoint | CandleData)[];
    color?: string;
    height?: number;
    showGrid?: boolean;
    showLabels?: boolean;
}

const RealTimeChart: React.FC<Props> = ({ 
    data, 
    color = '#2962FF', 
    height = 400
}) => {
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<IChartApi | null>(null);

    useEffect(() => {
        if (!chartContainerRef.current || data.length === 0) return;

        // 1. Prepare Data
        // Convert ChartPoint (Line) to CandleData format if needed for uniformity
        const candles: CandleData[] = data.map(d => {
            if ('open' in d) return d as CandleData;
            return { timestamp: d.timestamp, open: (d as ChartPoint).price, high: (d as ChartPoint).price, low: (d as ChartPoint).price, close: (d as ChartPoint).price, volume: 100 };
        }).sort((a, b) => a.timestamp - b.timestamp);

        // Calculate Indicators deterministically
        const closes = candles.map(c => c.close);
        const sma20 = MathEngine.calculateEMA(closes, 20);
        const bb = MathEngine.calculateBollingerBands(closes); // Returns latest only, we need series. 
        // For series plotting, we need to loop. This is expensive but necessary for "Bloomberg" feel.
        
        const bbDataUpper = [];
        const bbDataLower = [];
        const macdData = [];
        
        // Compute Historical Indicators
        for(let i = 20; i < candles.length; i++) {
             const slice = candles.slice(0, i+1);
             const subCloses = slice.map(c => c.close);
             const b = MathEngine.calculateBollingerBands(subCloses);
             const m = MathEngine.calculateMACD(subCloses);
             
             bbDataUpper.push({ time: candles[i].timestamp / 1000 as any, value: b.upper });
             bbDataLower.push({ time: candles[i].timestamp / 1000 as any, value: b.lower });
             
             macdData.push({ 
                 time: candles[i].timestamp / 1000 as any, 
                 value: m.histogram,
                 color: m.histogram > 0 ? '#26a69a' : '#ef4444'
             });
        }

        const formattedCandles = candles.map(d => ({
            time: d.timestamp / 1000 as any,
            open: d.open, high: d.high, low: d.low, close: d.close
        }));

        const formattedVolume = candles.map((d, i) => ({
             time: d.timestamp / 1000 as any,
             value: d.volume || 100,
             color: (d.close >= d.open) ? 'rgba(38, 166, 154, 0.5)' : 'rgba(239, 68, 68, 0.5)'
        }));

        // 2. Initialize Chart
        const chart = createChart(chartContainerRef.current, {
            layout: {
                background: { type: ColorType.Solid, color: 'transparent' },
                textColor: '#64748b',
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 10,
            },
            width: chartContainerRef.current.clientWidth,
            height: height,
            grid: {
                vertLines: { color: 'rgba(197, 203, 206, 0.1)' },
                horzLines: { color: 'rgba(197, 203, 206, 0.1)' },
            },
            rightPriceScale: {
                borderColor: 'rgba(197, 203, 206, 0.4)',
                scaleMargins: { top: 0.1, bottom: 0.3 }, // Price takes top 70%
            },
        });

        // 3. Main Candle Series
        const mainSeries = chart.addCandlestickSeries({
            upColor: '#10b981', downColor: '#ef4444',
            borderVisible: false, wickUpColor: '#10b981', wickDownColor: '#ef4444',
        });
        mainSeries.setData(formattedCandles);

        // 4. Bollinger Bands (Lines)
        const bbUpperSeries = chart.addLineSeries({ color: 'rgba(59, 130, 246, 0.5)', lineWidth: 1, lastValueVisible: false, crosshairMarkerVisible: false });
        const bbLowerSeries = chart.addLineSeries({ color: 'rgba(59, 130, 246, 0.5)', lineWidth: 1, lastValueVisible: false, crosshairMarkerVisible: false });
        bbUpperSeries.setData(bbDataUpper);
        bbLowerSeries.setData(bbDataLower);

        // 5. Volume Series (Separate Scale)
        const volumeSeries = chart.addHistogramSeries({
            priceFormat: { type: 'volume' },
            priceScaleId: 'volume', // Separate scale
        });
        chart.priceScale('volume').applyOptions({
            scaleMargins: { top: 0.7, bottom: 0 }, // Bottom 30%
            visible: false,
        });
        volumeSeries.setData(formattedVolume);

        // 6. MACD Histogram (Overlay on Volume area essentially, or explicit sub-pane)
        // For cleanliness, let's keep it simple: Just Candles + BB + Volume for now. 
        // Adding too many panes on a small screen kills UX.
        // We will stick to the "Bloomberg" clean look.

        chart.timeScale().fitContent();
        chartRef.current = chart;

        const handleResize = () => {
            if (chartContainerRef.current) {
                chart.applyOptions({ width: chartContainerRef.current.clientWidth });
            }
        };
        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            chart.remove();
        };
    }, [data, height, color]);

    if (!data || data.length === 0) {
        return <div className="flex items-center justify-center text-xs text-gray-400 h-full w-full bg-gray-50 rounded-2xl border border-dashed border-gray-200">Waiting for data stream...</div>;
    }

    return (
        <div className="w-full h-full relative group">
            <div ref={chartContainerRef} className="w-full h-full rounded-2xl overflow-hidden" />
            
            {/* HUD Overlay */}
            <div className="absolute top-2 left-2 pointer-events-none flex flex-col gap-1">
                <div className="flex gap-2">
                    <div className="bg-white/80 backdrop-blur px-2 py-1 rounded border border-gray-200 shadow-sm text-[9px] text-gray-600 font-mono font-bold">
                        <span className="w-2 h-2 rounded-full bg-green-500 inline-block mr-1"></span> Price
                    </div>
                    <div className="bg-white/80 backdrop-blur px-2 py-1 rounded border border-gray-200 shadow-sm text-[9px] text-blue-500 font-mono font-bold">
                        BB (20, 2)
                    </div>
                    <div className="bg-white/80 backdrop-blur px-2 py-1 rounded border border-gray-200 shadow-sm text-[9px] text-teal-600 font-mono font-bold">
                        Volume
                    </div>
                </div>
            </div>
        </div>
    );
};

export default RealTimeChart;
