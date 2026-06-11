import { CandleData, SMCOutput, QuantScannerOutput } from "../types";

export const EntryRiskEngine = {
    /**
     * ENTRY & RISK ENGINE
     * Calculates Entry, SL, and TP based on market geometry.
     * Rule: Invalidation > RR.
     */
    calculateGeometry: (
        candles: CandleData[],
        smc: SMCOutput,
        quant: QuantScannerOutput,
        direction: 'BUY' | 'SELL'
    ) => {
        const lastCandle = candles[candles.length - 1];
        const lastPrice = lastCandle.close;
        
        // 1. SL: Structural Invalidation Level
        // Buy: Below recent swing low or liquidity sweep low
        // Sell: Above recent swing high or liquidity sweep high
        const recentHighs = candles.slice(-10).map(c => c.high);
        const recentLows = candles.slice(-10).map(c => c.low);
        
        let sl = direction === 'BUY' ? Math.min(...recentLows) : Math.max(...recentHighs);
        
        // Buffer SL by 0.5%
        sl = direction === 'BUY' ? sl * 0.995 : sl * 1.005;

        // 2. TP: Liquidity Objectives
        // TP1: Nearest liquidity (recent high/low)
        // TP2: Volatility extension (1.5x SL distance)
        const slDistance = Math.abs(lastPrice - sl);
        
        const tp1 = direction === 'BUY' ? Math.max(...recentHighs) : Math.min(...recentLows);
        const tp2 = direction === 'BUY' ? lastPrice + (slDistance * 1.5) : lastPrice - (slDistance * 1.5);
        const tp3 = direction === 'BUY' ? lastPrice + (slDistance * 3) : lastPrice - (slDistance * 3);

        return {
            location: direction === 'BUY' ? 'DISCOUNT_ZONE' : 'PREMIUM_ZONE',
            trigger: smc.liquiditySweep ? 'LIQUIDITY_SWEEP_BOS' : 'MOMENTUM_BREAKOUT',
            execution: 'MARKET' as const,
            entry: lastPrice,
            sl,
            tp: [tp1, tp2, tp3]
        };
    }
};
