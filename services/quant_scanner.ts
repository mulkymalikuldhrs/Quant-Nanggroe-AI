import { CandleData, QuantScannerOutput } from "../types";
import { MathEngine } from "./math_engine";
import { AuditLogger } from "./audit_logger";

export const QuantScanner = {
    /**
     * QUANT-SCANNER (Technical Sensor)
     * Output: Numeric & State-based only. No "Buy/Sell" opinions.
     */
    analyze: (candles: CandleData[]): QuantScannerOutput => {
        AuditLogger.log('SENSOR', 'QuantScanner: Starting Technical Analysis', { candleCount: candles?.length });
        if (!candles || candles.length < 50) {
            const output: QuantScannerOutput = {
                trendStrength: 0,
                structureState: 'NEUTRAL',
                volatilityExpansion: false
            };
            AuditLogger.log('SENSOR', 'QuantScanner: Insufficient Data', output, 'WARNING');
            return output;
        }

        const closes = candles.map(c => c.close);
        const adx = MathEngine.calculateADX(candles);
        const sma50 = MathEngine.calculateSMA(closes, 50);
        const sma200 = MathEngine.calculateSMA(closes, 200);
        
        const trendStrength = Math.min(adx / 50, 1.0);
        let structureState: 'BULL' | 'BEAR' | 'NEUTRAL' = 'NEUTRAL';
        
        const lastPrice = closes[closes.length - 1];
        if (lastPrice > sma50 && sma50 > sma200) structureState = 'BULL';
        else if (lastPrice < sma50 && sma50 < sma200) structureState = 'BEAR';
        
        const bb = MathEngine.calculateBollingerBands(closes);
        const volatilityExpansion = (bb.upper - bb.lower) > (MathEngine.calculateSMA(closes, 20) * 0.05);

        const output: QuantScannerOutput = {
            trendStrength,
            structureState,
            volatilityExpansion
        };

        AuditLogger.log('SENSOR', 'QuantScanner: Analysis Complete', output);
        return output;
    }
};
