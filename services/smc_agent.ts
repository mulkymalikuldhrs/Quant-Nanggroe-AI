import { CandleData, SMCOutput } from "../types";
import { AuditLogger } from "./audit_logger";

export const SMCAgent = {
    /**
     * SMC / PRICE ACTION AGENT (Sensor)
     * Treats SMC concepts as data points. No execution logic here.
     */
    analyze: (candles: CandleData[]): SMCOutput => {
        AuditLogger.log('SENSOR', 'SMCAgent: Analyzing Price Action', { candleCount: candles?.length });
        if (candles.length < 20) {
            const output: SMCOutput = {
                liquiditySweep: false,
                displacementStrength: 0,
                poiValidity: 0
            };
            AuditLogger.log('SENSOR', 'SMCAgent: Insufficient Data', output, 'WARNING');
            return output;
        }
        
        const lastCandle = candles[candles.length - 1];
        const prevCandles = candles.slice(-20, -1);
        
        const highestHigh = Math.max(...prevCandles.map(c => c.high));
        const lowestLow = Math.min(...prevCandles.map(c => c.low));
        
        // Liquidity Sweep: Price breaks high/low then reverses
        const liquiditySweep = (lastCandle.high > highestHigh && lastCandle.close < highestHigh) || 
                               (lastCandle.low < lowestLow && lastCandle.close > lowestLow);
                               
        // Displacement: Strong candle (Marubozu-like)
        const bodySize = Math.abs(lastCandle.close - lastCandle.open);
        const totalSize = lastCandle.high - lastCandle.low;
        const displacementStrength = totalSize === 0 ? 0 : bodySize / totalSize;
        
        // POI Validity: Simplified POI near extremes
        const poiValidity = (lastCandle.close > highestHigh * 0.98 || lastCandle.close < lowestLow * 1.02) ? 0.8 : 0.2;

        const output: SMCOutput = {
            liquiditySweep,
            displacementStrength,
            poiValidity
        };

        AuditLogger.log('SENSOR', 'SMCAgent: SMC Analysis Complete', output);
        return output;
    }
};
