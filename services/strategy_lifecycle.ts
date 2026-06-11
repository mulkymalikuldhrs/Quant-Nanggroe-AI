
import { StrategyLifecycle } from "../types";
import { AuditLogger } from "./audit_logger";

export const StrategyLifecycleManager = {
    strategies: new Map<string, StrategyLifecycle>(),

    registerStrategy: (id: string, name: string, deathThreshold: number) => {
        const strategy: StrategyLifecycle = {
            id,
            name,
            status: 'ACTIVE',
            metrics: {
                expectancy: 0,
                maxDrawdown: 0,
                sharpeRatio: 0,
                winRate: 0,
                sampleSize: 0
            },
            tradesCount: 0,
            deathThreshold
        };
        StrategyLifecycleManager.strategies.set(id, strategy);
    },

    updatePerformance: (id: string, pnl: number, isWin: boolean) => {
        const strat = StrategyLifecycleManager.strategies.get(id);
        if (!strat || strat.status === 'KILLED') return;

        strat.tradesCount++;
        const m = strat.metrics;
        m.sampleSize++;
        
        // Rolling Win Rate
        m.winRate = ((m.winRate * (m.sampleSize - 1)) + (isWin ? 1 : 0)) / m.sampleSize;
        
        // Simple Expectancy (Rolling Avg PnL)
        m.expectancy = ((m.expectancy * (m.sampleSize - 1)) + pnl) / m.sampleSize;

        // Death Threshold Check (Darwinism)
        if (strat.tradesCount >= 20 && m.expectancy < 0) {
            strat.status = 'KILLED';
            AuditLogger.log('EXECUTION', `STRATEGY KILLED: ${strat.name} (Expectancy: ${m.expectancy})`, 'HIGH');
        } else if (m.maxDrawdown > 0.15) { // Hard limit 15% DD
            strat.status = 'HIBERNATING';
            AuditLogger.log('EXECUTION', `STRATEGY HIBERNATING: ${strat.name} (DD: ${m.maxDrawdown})`, 'MEDIUM');
        }
    },

    getStatus: (id: string): 'ACTIVE' | 'HIBERNATING' | 'KILLED' => {
        return StrategyLifecycleManager.strategies.get(id)?.status || 'KILLED';
    }
};
