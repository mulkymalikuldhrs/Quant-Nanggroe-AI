
import { AuditLogger } from "./audit_logger";
import { StrategyLifecycleManager } from "./strategy_lifecycle";

export const EvolutionMonitor = {
    analyzeEvolution: () => {
        const report: string[] = [];
        StrategyLifecycleManager.strategies.forEach((strat, id) => {
            const status = strat.status;
            const perf = strat.metrics.expectancy;
            
            report.push(`[${status}] ${strat.name}: Expectancy ${perf.toFixed(4)}, WinRate ${(strat.metrics.winRate * 100).toFixed(2)}%`);
            
            if (status === 'KILLED') {
                AuditLogger.log('DECISION', `Evolution Alert: Strategy ${strat.name} has been removed from the pool due to poor performance.`, 'HIGH');
            }
        });
        
        return report;
    }
};
