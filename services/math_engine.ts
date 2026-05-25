
import { CandleData, TechnicalIndicators } from "../types";

// --- QUANTITATIVE MATH ENGINE ---
// Performs pure mathematical analysis on time-series data.
// 100% Deterministic. No AI Hallucinations here.

export const MathEngine = {

    calculateRSI: (closes: number[], period: number = 14): number => {
        if (closes.length < period + 1) return 50;

        let gains = 0;
        let losses = 0;

        // First average
        for (let i = 1; i <= period; i++) {
            const change = closes[i] - closes[i - 1];
            if (change > 0) gains += change;
            else losses += Math.abs(change);
        }

        let avgGain = gains / period;
        let avgLoss = losses / period;

        // Smooth
        for (let i = period + 1; i < closes.length; i++) {
            const change = closes[i] - closes[i - 1];
            const gain = change > 0 ? change : 0;
            const loss = change < 0 ? Math.abs(change) : 0;

            avgGain = ((avgGain * (period - 1)) + gain) / period;
            avgLoss = ((avgLoss * (period - 1)) + loss) / period;
        }

        if (avgLoss === 0) return 100;
        const rs = avgGain / avgLoss;
        return 100 - (100 / (1 + rs));
    },

    calculateSMA: (data: number[], period: number): number => {
        if (data.length < period) return data[data.length - 1];
        const slice = data.slice(-period);
        const sum = slice.reduce((a, b) => a + b, 0);
        return sum / period;
    },

    calculateEMA: (data: number[], period: number): number[] => {
        const k = 2 / (period + 1);
        const emaArray = [data[0]];
        for (let i = 1; i < data.length; i++) {
            emaArray.push(data[i] * k + emaArray[i - 1] * (1 - k));
        }
        return emaArray;
    },

    calculateMACD: (closes: number[]): { macdLine: number, signalLine: number, histogram: number } => {
        if (closes.length < 26) return { macdLine: 0, signalLine: 0, histogram: 0 };
        
        const ema12 = MathEngine.calculateEMA(closes, 12);
        const ema26 = MathEngine.calculateEMA(closes, 26);
        
        const macdLineArray: number[] = [];
        for(let i=0; i<closes.length; i++) {
            macdLineArray.push(ema12[i] - ema26[i]);
        }

        const signalLineArray = MathEngine.calculateEMA(macdLineArray, 9);
        
        const currentMACD = macdLineArray[macdLineArray.length - 1];
        const currentSignal = signalLineArray[signalLineArray.length - 1];

        return {
            macdLine: currentMACD,
            signalLine: currentSignal,
            histogram: currentMACD - currentSignal
        };
    },

    calculateBollingerBands: (closes: number[], period: number = 20, multiplier: number = 2) => {
        if (closes.length < period) return { upper: 0, middle: 0, lower: 0 };

        const sma = MathEngine.calculateSMA(closes, period);
        const slice = closes.slice(-period);
        
        const squaredDiffs = slice.map(val => Math.pow(val - sma, 2));
        const variance = squaredDiffs.reduce((a, b) => a + b, 0) / period;
        const stdDev = Math.sqrt(variance);

        return {
            upper: sma + (multiplier * stdDev),
            middle: sma,
            lower: sma - (multiplier * stdDev)
        };
    },

    calculateATR: (candles: CandleData[], period: number = 14): number => {
        if (candles.length < period + 1) return 0;
        
        const trs = [];
        for(let i=1; i<candles.length; i++) {
            const high = candles[i].high;
            const low = candles[i].low;
            const prevClose = candles[i-1].close;
            
            const tr = Math.max(high - low, Math.abs(high - prevClose), Math.abs(low - prevClose));
            trs.push(tr);
        }

        // Simple SMA of TR for ATR
        const slice = trs.slice(-period);
        return slice.reduce((a,b) => a+b, 0) / period;
    },

    calculateVWAP: (candles: CandleData[]): number => {
        let cumVolume = 0;
        let cumPV = 0;
        
        for (const c of candles) {
            const typicalPrice = (c.high + c.low + c.close) / 3;
            const vol = c.volume || 1;
            cumPV += typicalPrice * vol;
            cumVolume += vol;
        }
        
        return cumVolume === 0 ? 0 : cumPV / cumVolume;
    },

    calculateVWAPBands: (candles: CandleData[], vwap: number, multiplier: number = 2): { upper: number, lower: number } => {
        if (candles.length === 0) return { upper: vwap, lower: vwap };
        
        let sumSquaredDiff = 0;
        let sumVolume = 0;
        
        for (const c of candles) {
            const typicalPrice = (c.high + c.low + c.close) / 3;
            const vol = c.volume || 1;
            sumSquaredDiff += vol * Math.pow(typicalPrice - vwap, 2);
            sumVolume += vol;
        }
        
        const vwapStdDev = Math.sqrt(sumSquaredDiff / sumVolume);
        return {
            upper: vwap + (multiplier * vwapStdDev),
            lower: vwap - (multiplier * vwapStdDev)
        };
    },

    // Identify High Volume Nodes (Simplified Volume Profile)
    calculateVolumeProfile: (candles: CandleData[], bins: number = 20): { price: number, volume: number }[] => {
        if (candles.length === 0) return [];
        
        const prices = candles.map(c => c.close);
        const minPrice = Math.min(...prices);
        const maxPrice = Math.max(...prices);
        const binSize = (maxPrice - minPrice) / bins;
        
        const profile: Record<number, number> = {};
        
        for (const c of candles) {
            const binIndex = Math.floor((c.close - minPrice) / binSize);
            const binPrice = minPrice + (binIndex * binSize) + (binSize / 2);
            profile[binPrice] = (profile[binPrice] || 0) + (c.volume || 1);
        }
        
        return Object.entries(profile)
            .map(([price, volume]) => ({ price: parseFloat(price), volume }))
            .sort((a, b) => b.volume - a.volume);
    },

    // --- NEW INDICATORS ---

    calculateStochastic: (candles: CandleData[], period: number = 14, smoothK: number = 3, smoothD: number = 3): { k: number, d: number } => {
        if (candles.length < period) return { k: 50, d: 50 };

        const closes = candles.map(c => c.close);
        const highs = candles.map(c => c.high);
        const lows = candles.map(c => c.low);

        const rawK = [];
        for(let i = period - 1; i < candles.length; i++) {
            const currentClose = closes[i];
            const periodLows = lows.slice(i - period + 1, i + 1);
            const periodHighs = highs.slice(i - period + 1, i + 1);
            const lowestLow = Math.min(...periodLows);
            const highestHigh = Math.max(...periodHighs);
            
            const k = ((currentClose - lowestLow) / (highestHigh - lowestLow)) * 100;
            rawK.push(k);
        }

        const k = MathEngine.calculateSMA(rawK, smoothK);
        // D is SMA of K
        const d = MathEngine.calculateSMA(rawK.slice(-smoothD * 2), smoothD); 

        return { k, d };
    },

    calculateCCI: (candles: CandleData[], period: number = 20): number => {
        if (candles.length < period) return 0;

        const typicalPrices = candles.map(c => (c.high + c.low + c.close) / 3);
        const smaTP = MathEngine.calculateSMA(typicalPrices, period);
        
        const slice = typicalPrices.slice(-period);
        const meanDev = slice.reduce((acc, val) => acc + Math.abs(val - smaTP), 0) / period;

        const currentTP = typicalPrices[typicalPrices.length - 1];
        return (currentTP - smaTP) / (0.015 * meanDev);
    },

    calculateADX: (candles: CandleData[], period: number = 14): number => {
        // TODO: Implement full Wilders Smoothing ADX algorithm
        // Current implementation is a simplified approximation using SMA slope as trend proxy
        // For production accuracy, implement: +DI, -DI, DX, then ADX via Wilders smoothing
        if (candles.length < period * 2) return 25;
        const closes = candles.map(c => c.close);
        const sma20 = MathEngine.calculateSMA(closes, 20);
        const sma20Prev = MathEngine.calculateSMA(closes.slice(0, closes.length - 5), 20);
        const diff = Math.abs(sma20 - sma20Prev) / sma20Prev;
        return Math.min(diff * 1000, 100); // Scale factor approximation
    },

    // MASTER FUNCTION: Generate Institutional Technical Sheet
    analyzeSequence: (candles: CandleData[]): TechnicalIndicators => {
        const closes = candles.map(c => c.close);
        
        return {
            rsi: MathEngine.calculateRSI(closes),
            stoch: MathEngine.calculateStochastic(candles),
            cci: MathEngine.calculateCCI(candles),
            adx: MathEngine.calculateADX(candles),
            macd: MathEngine.calculateMACD(closes),
            bollinger: MathEngine.calculateBollingerBands(closes),
            vwap: MathEngine.calculateVWAP(candles),
            atr: MathEngine.calculateATR(candles),
            sma: {
                ma10: MathEngine.calculateSMA(closes, 10),
                ma20: MathEngine.calculateSMA(closes, 20),
                ma50: MathEngine.calculateSMA(closes, 50),
                ma100: MathEngine.calculateSMA(closes, 100),
                ma200: MathEngine.calculateSMA(closes, 200)
            }
        };
    }
};
