
import { 
    MarketState, QuantScannerOutput, SMCOutput, NewsSentinelOutput, FlowWhaleOutput, 
    PressureState, DecisionSynthesis, MarketRegime, ConfluenceStatus 
} from "../types";

export class PressureNormalizationEngine {
    public static normalize(
        quant: QuantScannerOutput,
        smc: SMCOutput,
        news: NewsSentinelOutput,
        flow: FlowWhaleOutput,
        state: MarketState
    ): PressureState {
        // 1. Calculate Buy Pressure (0.0 - 1.0)
        let buyPressure = 0;
        if (quant.structureState === 'BULL') buyPressure += 0.3 * quant.trendStrength;
        if (smc.liquiditySweep && smc.displacementStrength > 0.5) buyPressure += 0.4;
        if (flow.positioningBias === 'LONG') buyPressure += 0.2 * flow.flowImbalance;
        if (news.eventType === 'MACRO' && news.impactScore > 0.5) buyPressure += 0.1;
        
        // 2. Calculate Sell Pressure (0.0 - 1.0)
        let sellPressure = 0;
        if (quant.structureState === 'BEAR') sellPressure += 0.3 * quant.trendStrength;
        if (smc.liquiditySweep && smc.displacementStrength > 0.5) sellPressure += 0.1; // Counter-bias
        if (flow.positioningBias === 'SHORT') sellPressure += 0.2 * flow.flowImbalance;
        if (news.eventType === 'SHOCK') sellPressure += 0.4;

        // 3. Volatility Risk
        let volatilityRisk: 'LOW' | 'MID' | 'HIGH' = 'MID';
        if (state.volatility === 'HIGH' || news.impactScore > 0.8) volatilityRisk = 'HIGH';
        else if (state.volatility === 'LOW') volatilityRisk = 'LOW';

        // 4. Liquidity Condition
        const liquidityCondition = state.liquidity;

        // 5. Confidence Score
        const confidenceScore = Math.min(
            (quant.trendStrength + smc.displacementStrength + (1 - news.directionalUncertainty)) / 3,
            1.0
        );

        return {
            buyPressure: Math.min(buyPressure, 1.0),
            sellPressure: Math.min(sellPressure, 1.0),
            volatilityRisk,
            liquidityCondition,
            confidenceScore
        };
    }
}

export class DecisionSynthesisEngine {
    public static synthesize(
        state: MarketState,
        pressures: PressureState,
        lastPrice: number
    ): DecisionSynthesis {
        // --- CONFLUENCE DECISION TABLE (BLUEPRINT 6) ---
        const allowedRegimes: MarketRegime[] = ['TRENDING', 'RANGE'];
        
        const isRegimeAllowed = allowedRegimes.includes(state.regime);
        const isPressureValid = (pressures.buyPressure > 0.7 || pressures.sellPressure > 0.7);
        const isVolSafe = pressures.volatilityRisk !== 'HIGH';
        const isConfidenceHigh = pressures.confidenceScore > 0.6;
        
        const isAllowed = isRegimeAllowed && isPressureValid && isVolSafe && isConfidenceHigh;
        
        let action: 'BUY' | 'SELL' | 'HOLD' | 'WAIT' = 'WAIT';
        if (isAllowed) {
            action = pressures.buyPressure > pressures.sellPressure ? 'BUY' : 'SELL';
        } else if (state.regime === 'NO_TRADE' || state.regime === 'PANIC') {
            action = 'HOLD';
        }

        const confluence: ConfluenceStatus = {
            isAllowed,
            score: pressures.confidenceScore,
            reason: !isRegimeAllowed ? 'Invalid Regime' : 
                    !isPressureValid ? 'Insufficient Pressure' :
                    !isVolSafe ? 'High Volatility Risk' :
                    !isConfidenceHigh ? 'Low Confidence' : 'All layers passed'
        };

        // --- ENTRY ENGINE (BLUEPRINT 7) ---
        let entryParameters;
        if (isAllowed) {
            const atr = lastPrice * 0.01; // Simple fallback if ATR not passed
            const side = action === 'BUY' ? 1 : -1;
            
            entryParameters = {
                location: action === 'BUY' ? 'Discount Zone' : 'Premium Zone',
                trigger: 'Liquidity Sweep + BOS',
                execution: 'LIMIT' as const,
                entry: lastPrice,
                sl: lastPrice - (side * atr * 2), // Structural Invalidation
                tp: [
                    lastPrice + (side * atr * 2), // TP1: Nearest Liquidity
                    lastPrice + (side * atr * 4), // TP2: HTF Imbalance
                    lastPrice + (side * atr * 6)  // TP3: Volatility Extension
                ]
            };
        }

        return {
            regime: state.regime,
            pressures,
            confluence,
            entryParameters,
            riskClearance: isAllowed ? 'CLEAR' : 'BLOCKED',
            action
        };
    }
}

// Legacy compatibility for now
export const quantumEngine = {
    getLiveMetrics: () => ({
        coherence: "0.9841",
        qubitsActive: 1536,
        synapticLoad: "42.15%",
        nexusStatus: 'OPERATIONAL'
    })
};
