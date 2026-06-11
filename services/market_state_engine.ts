import { CandleData, MarketState, MarketRegime } from "../types";
import { MathEngine } from "./math_engine";
import { AuditLogger } from "./audit_logger";

export const MarketStateEngine = {
    /**
     * MASTER REGIME ENGINE
     * Located above all agents. If output is NO_TRADE, all agents must remain idle.
     */
    analyze: (candles: CandleData[]): MarketState => {
        AuditLogger.log('MARKET', 'Analyzing Market State', { candleCount: candles?.length });
        if (!candles || candles.length < 50) {
            const state: MarketState = {
                regime: 'NO_TRADE',
                volatility: 'NORMAL',
                liquidity: 'NORMAL',
                timestamp: Date.now()
            };
            AuditLogger.log('MARKET', 'Market State Result', state, 'WARNING');
            return state;
        }

        const closes = candles.map(c => c.close);
        const lastPrice = closes[closes.length - 1];

        // 1. Regime Detection (Deterministic)
        let regime: MarketRegime = 'RANGE';
        
        const adx = MathEngine.calculateADX(candles);
        const rsi = MathEngine.calculateRSI(closes);
        
        // Trending vs Range
        const isTrending = adx > 25;
        if (isTrending) {
            regime = 'TRENDING';
        } else if (rsi > 70 || rsi < 30) {
            regime = 'MEAN_REVERT';
        }

        // Risk-Off / Panic detection (Fast drop)
        const priceChangeShort = (lastPrice - closes[closes.length - 5]) / closes[closes.length - 5];
        if (priceChangeShort < -0.05) {
            regime = 'PANIC';
        } else if (priceChangeShort < -0.02) {
            regime = 'RISK_OFF';
        }

        // 2. Volatility State (ATR based)
        let volatility: 'LOW' | 'NORMAL' | 'HIGH' = 'NORMAL';
        const atr = MathEngine.calculateATR(candles);
        const atrPercent = (atr / lastPrice) * 100;
        
        if (atrPercent > 2.5) volatility = 'HIGH';
        else if (atrPercent < 0.5) volatility = 'LOW';

        // 3. Liquidity State (Volume based)
        let liquidity: 'THIN' | 'NORMAL' | 'DEEP' = 'NORMAL';
        const avgVol = candles.reduce((a, b) => a + (b.volume || 0), 0) / candles.length;
        const lastVol = candles[candles.length - 1].volume || 0;
        
        if (lastVol < avgVol * 0.4) liquidity = 'THIN';
        else if (lastVol > avgVol * 1.8) liquidity = 'DEEP';

        const state: MarketState = {
            regime,
            volatility,
            liquidity,
            timestamp: Date.now()
        };

        AuditLogger.log('MARKET', 'Market State Result', state);
        return state;
    }
};
