import { 
    QuantScannerOutput, 
    SMCOutput, 
    NewsSentinelOutput, 
    FlowWhaleOutput, 
    PressureState,
    MarketState
} from "../types";
import { AuditLogger } from "./audit_logger";

export const PressureNormalizationEngine = {
    /**
     * PRESSURE NORMALIZATION ENGINE
     * Converts all agent sensor outputs into numerical pressures (0.0 - 1.0).
     */
    normalize: (
        market: MarketState,
        quant: QuantScannerOutput,
        smc: SMCOutput,
        news: NewsSentinelOutput,
        flow: FlowWhaleOutput
    ): PressureState => {
        AuditLogger.log('PRESSURE', 'Starting Pressure Normalization', { market, quant, smc, news, flow });
        let buyPressure = 0;
        let sellPressure = 0;
        
        // Weight allocation per Blueprint Final Specification:
        // QuantScanner: 25%, SMCAgent: 30%, NewsSentinel: 20%, FlowAgent: 25%

        // 1. Quant Scanner Influence (Technical) — 25%
        if (quant.structureState === 'BULL') buyPressure += 0.25 * quant.trendStrength;
        if (quant.structureState === 'BEAR') sellPressure += 0.25 * quant.trendStrength;
        
        // 2. SMC Influence (Liquidity) — 30%
        if (smc.liquiditySweep) {
            // Sweep high -> Sell pressure, Sweep low -> Buy pressure
            // This is simplified; real logic would check direction of sweep
            buyPressure += 0.30 * smc.displacementStrength;
            sellPressure += 0.30 * smc.displacementStrength;
        }
        
        // 3. News Sentinel Influence (Macro) — 20%
        if (news.impactScore > 0.5) {
            const newsImpact = news.impactScore * (1 - news.directionalUncertainty);
            // News sentiment would ideally provide direction, here we use directionalUncertainty as a risk factor
            buyPressure += 0.20 * newsImpact;
            sellPressure += 0.20 * newsImpact;
        }
        
        // 4. Flow Influences (Whales) — 25%
        if (flow.positioningBias === 'LONG') buyPressure += 0.25 * flow.flowImbalance;
        if (flow.positioningBias === 'SHORT') sellPressure += 0.25 * flow.flowImbalance;

        // 5. Normalization
        const total = buyPressure + sellPressure || 1;
        buyPressure = buyPressure / total;
        sellPressure = sellPressure / total;

        // Confidence Score based on confluence of directions
        const confidenceScore = Math.max(buyPressure, sellPressure);

        const state: PressureState = {
            buyPressure,
            sellPressure,
            volatilityRisk: market.volatility,
            liquidityCondition: market.liquidity,
            confidenceScore
        };

        AuditLogger.log('PRESSURE', 'Normalization Result', state);
        return state;
    }
};
