
import { MathEngine } from './math_engine';
import { MLEngine } from './ml_engine';
import { CandleData, StrategySignal, ConsensusReport, TechnicalIndicators } from '../types';

export const StrategyEngine = {
    
    // --- 0. MARKET REGIME DETECTION ---
    detectRegime: (t: TechnicalIndicators): 'TRENDING_BULL' | 'TRENDING_BEAR' | 'RANGING' | 'VOLATILE' => {
        const adx = t.adx;
        const maFast = t.sma.ma20;
        const maSlow = t.sma.ma50;
        const atr = t.atr;
        const price = t.sma.ma10;

        if (atr > (price * 0.05)) return 'VOLATILE'; 

        if (adx > 25) {
            if (maFast > maSlow) return 'TRENDING_BULL';
            return 'TRENDING_BEAR';
        }
        
        return 'RANGING';
    },

    // --- 1. SMART MONEY CONCEPTS (SMC) ---
    
    scanSMC: (candles: CandleData[]): StrategySignal[] => {
        const signals: StrategySignal[] = [];
        if (candles.length < 20) return signals;

        const latest = candles[candles.length - 1];
        
        // A. Fair Value Gaps (FVG)
        // Bullish FVG: Low of candle 3 > High of candle 1
        for (let i = candles.length - 3; i >= candles.length - 10; i--) {
            const c1 = candles[i-2];
            const c2 = candles[i-1];
            const c3 = candles[i];
            
            if (c3.low > c1.high && c2.close > c2.open) {
                signals.push({
                    name: "Bullish Fair Value Gap",
                    category: 'SMC',
                    type: 'BUY',
                    strength: 85,
                    weight: 8,
                    description: "Price left an imbalance. Expect a return to this zone for support."
                });
                break;
            }
            if (c3.high < c1.low && c2.close < c2.open) {
                signals.push({
                    name: "Bearish Fair Value Gap",
                    category: 'SMC',
                    type: 'SELL',
                    strength: 85,
                    weight: 8,
                    description: "Price left an imbalance. Expect a return to this zone for resistance."
                });
                break;
            }
        }

        // B. Order Blocks (OB)
        // Simplified: Last down candle before a strong up move
        const last10 = candles.slice(-10);
        const maxHigh = Math.max(...last10.map(c => c.high));
        const minLow = Math.min(...last10.map(c => c.low));
        
        if (latest.close > maxHigh * 0.98) {
            signals.push({
                name: "Bullish Order Block (Accumulation)",
                category: 'SMC',
                type: 'BUY',
                strength: 75,
                weight: 7,
                description: "Institutional buy orders detected in recent consolidation."
            });
        } else if (latest.close < minLow * 1.02) {
            signals.push({
                name: "Bearish Order Block (Distribution)",
                category: 'SMC',
                type: 'SELL',
                strength: 75,
                weight: 7,
                description: "Institutional sell orders detected in recent consolidation."
            });
        }

        return signals;
    },

    // --- 2. SUPPORT & RESISTANCE (S/R) ---
    
    scanSupportResistance: (candles: CandleData[]): StrategySignal[] => {
        const signals: StrategySignal[] = [];
        if (candles.length < 50) return signals;

        const closes = candles.map(c => c.close);
        const currentPrice = closes[closes.length - 1];
        
        // Find Pivot Points
        const pivots = [];
        for (let i = 5; i < candles.length - 5; i++) {
            const prev = candles.slice(i - 5, i);
            const next = candles.slice(i + 1, i + 6);
            const curr = candles[i];
            
            if (curr.high > Math.max(...prev.map(c => c.high)) && curr.high > Math.max(...next.map(c => c.high))) {
                pivots.push({ type: 'resistance', price: curr.high });
            }
            if (curr.low < Math.min(...prev.map(c => c.low)) && curr.low < Math.min(...next.map(c => c.low))) {
                pivots.push({ type: 'support', price: curr.low });
            }
        }

        // Check proximity to pivots
        pivots.forEach(p => {
            const diff = Math.abs(currentPrice - p.price) / p.price;
            if (diff < 0.005) { // Within 0.5%
                signals.push({
                    name: `Major ${p.type === 'support' ? 'Support' : 'Resistance'} Level`,
                    category: 'STRUCTURE',
                    type: p.type === 'support' ? 'BUY' : 'SELL',
                    strength: 80,
                    weight: 6,
                    description: `Price is testing a historical ${p.type} zone at ${p.price.toFixed(2)}.`
                });
            }
        });

        return signals;
    },

    // --- 3. RETAIL TECHNICAL ANALYSIS ---
    
    scanRetail: (t: TechnicalIndicators, regime: string): StrategySignal[] => {
        const signals: StrategySignal[] = [];
        
        // A. Trendlines / MAs
        if (t.sma.ma50 > t.sma.ma200) {
            signals.push({
                name: "Golden Cross (Macro Trend)",
                category: 'RETAIL',
                type: 'BUY',
                strength: 70,
                weight: 5,
                description: "Classic bullish trend confirmation."
            });
        }
        
        // B. RSI / Overbought-Oversold
        if (t.rsi < 30) {
            signals.push({
                name: "RSI Oversold",
                category: 'RETAIL',
                type: 'BUY',
                strength: 65,
                weight: 4,
                description: "Market may be overextended to the downside."
            });
        } else if (t.rsi > 70) {
            signals.push({
                name: "RSI Overbought",
                category: 'RETAIL',
                type: 'SELL',
                strength: 65,
                weight: 4,
                description: "Market may be overextended to the upside."
            });
        }

        return signals;
    },

    // --- MASTER EVALUATION ---

    evaluate: (candles: CandleData[], technicals: TechnicalIndicators): StrategySignal[] => {
        const regime = StrategyEngine.detectRegime(technicals);
        
        let allSignals: StrategySignal[] = [];
        
        allSignals = [
            ...allSignals,
            ...StrategyEngine.scanSMC(candles),
            ...StrategyEngine.scanSupportResistance(candles),
            ...StrategyEngine.scanRetail(technicals, regime)
        ];

        return allSignals;
    },

    generateConsensus: (signals: StrategySignal[]): ConsensusReport => {
        let bullScore = 0;
        let bearScore = 0;
        let totalWeights = 0;

        signals.forEach(s => {
            if (s.type === 'BUY') bullScore += (s.strength * s.weight);
            if (s.type === 'SELL') bearScore += (s.strength * s.weight);
            totalWeights += s.weight;
        });

        const rawScore = (bullScore - bearScore); 
        const maxPossible = totalWeights * 100 || 1; 
        const normalizedScore = (rawScore / maxPossible) * 100;

        let verdict: ConsensusReport['verdict'] = 'NEUTRAL';
        if (normalizedScore > 50) verdict = 'STRONG BUY';
        else if (normalizedScore > 20) verdict = 'BUY';
        else if (normalizedScore < -50) verdict = 'STRONG SELL';
        else if (normalizedScore < -20) verdict = 'SELL';

        return {
            score: Math.round(normalizedScore),
            verdict,
            totalSignals: signals.length,
            bullishCount: signals.filter(s => s.type === 'BUY').length,
            bearishCount: signals.filter(s => s.type === 'SELL').length,
            topFactors: signals.sort((a,b) => (b.strength * b.weight) - (a.strength * a.weight)).slice(0, 3).map(s => s.name)
        };
    }
};
