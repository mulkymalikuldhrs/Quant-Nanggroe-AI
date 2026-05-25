import { 
    MarketState, 
    PressureState, 
    DecisionSynthesis, 
    DecisionTableEntry,
    MarketRegime,
    ConfluenceStatus,
    CandleData,
    QuantScannerOutput,
    SMCOutput
} from "../types";
import { RiskManagement } from "./risk_management";
import { EntryRiskEngine } from "./entry_risk_engine";
import { AuditLogger } from "./audit_logger";

export const DecisionSynthesisEngine = {
    /**
     * DECISION TABLE (Machine-Readable)
     * Defines strict rules for entry.
     */
    DECISION_TABLE: [
        {
            regime: ['TRENDING', 'RANGE', 'MEAN_REVERT'],
            minBuyPressure: 0.7,
            maxSellPressure: 0.3,
            allowedVolatility: ['LOW', 'NORMAL'],
            minConfidence: 0.6,
            action: 'ALLOW_ENTRY'
        },
        {
            regime: ['PANIC', 'RISK_OFF', 'NO_TRADE'],
            minBuyPressure: 1.1, // Impossible
            maxSellPressure: 1.1,
            allowedVolatility: [],
            minConfidence: 1.1,
            action: 'NO_TRADE'
        }
    ] as DecisionTableEntry[],

    /**
     * DECISION SYNTHESIS ENGINE (The "Compiler")
     * Compresses hundreds of signals into ONE final decision.
     */
    synthesize: (
        market: MarketState,
        pressures: PressureState,
        candles: CandleData[],
        smc: SMCOutput,
        quant: QuantScannerOutput,
        dailyPnL: number
    ): DecisionSynthesis => {
        AuditLogger.log('DECISION', 'Starting Decision Synthesis', { market, pressures, dailyPnL });
        
        // 1. Regime Guard (Top Level)
        if (market.regime === 'NO_TRADE') {
            const result: DecisionSynthesis = { regime: market.regime, pressures, confluence: { isAllowed: false, reason: 'REGIME_NO_TRADE', score: 0 }, riskClearance: 'CLEAR', action: 'WAIT' };
            AuditLogger.log('DECISION', 'Regime Guard Blocked', result, 'WARNING');
            return result;
        }

        // 2. Confluence Evaluation (Decision Table)
        const rules = DecisionSynthesisEngine.DECISION_TABLE.find(r => r.regime.includes(market.regime));
        let confluence: ConfluenceStatus = { isAllowed: false, reason: 'CONFLUENCE_FAILED', score: pressures.confidenceScore };

        if (rules) {
            const buyAllowed = pressures.buyPressure >= rules.minBuyPressure && rules.allowedVolatility.includes(market.volatility);
            const sellAllowed = pressures.sellPressure >= rules.minBuyPressure && rules.allowedVolatility.includes(market.volatility);
            
            if (buyAllowed || sellAllowed) {
                confluence.isAllowed = true;
                confluence.reason = 'CONFLUENCE_MET';
            }
        }
        
        AuditLogger.log('DECISION', 'Confluence Status', confluence);

        // 3. Risk Clearance (The "Law")
        // TODO: Replace hardcoded correlation score (0.5) with real correlation monitor data
        const riskClearance = RiskManagement.validateTrade(dailyPnL, 0.5, false);
        AuditLogger.log('RISK', 'Risk Clearance Result', { riskClearance });

        // 4. Action Determination
        let action: 'BUY' | 'SELL' | 'HOLD' | 'WAIT' = 'WAIT';
        if (confluence.isAllowed && riskClearance === 'CLEAR') {
            action = pressures.buyPressure > pressures.sellPressure ? 'BUY' : 'SELL';
        }

        // 5. Entry Parameters (Geometric)
        let entryParameters;
        if (action !== 'WAIT') {
            const geom = EntryRiskEngine.calculateGeometry(candles, smc, quant, action);
            entryParameters = {
                location: geom.location,
                trigger: geom.trigger,
                execution: geom.execution,
                entry: geom.entry,
                sl: geom.sl,
                tp: geom.tp
            };
        }

        const finalDecision: DecisionSynthesis = {
            regime: market.regime,
            pressures,
            confluence,
            entryParameters,
            riskClearance: riskClearance === 'CLEAR' ? 'CLEAR' : 'BLOCKED',
            action
        };

        AuditLogger.log('DECISION', 'Final Decision Object', finalDecision);
        return finalDecision;
    }
};
