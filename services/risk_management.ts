
import { CandleData, PortfolioPosition, TechnicalIndicators, MarketTicker } from "../types";
import { CorrelationMonitor } from "./correlation_monitor";

export interface RiskProfile {
    accountEquity: number;
    riskPerTrade: number; // Percent (e.g., 0.02 for 2%)
    maxDrawdown: number;
}

export const RiskManagement = {
    
    // --- CONSTITUTIONAL HARD CONSTRAINTS ---
    CONSTITUTION: {
        MAX_LEVERAGE: 5,
        MAX_CORRELATION: 0.7,
        MAX_EXPOSURE_PER_ASSET: 0.2, // 20%
        DAILY_DRAWDOWN_KILL_SWITCH: 0.04, // 4%
    },

    // --- KILL SWITCH (DETERMINISTIC) ---
    checkKillSwitch: (dailyPnLPercent: number): boolean => {
        if (dailyPnLPercent <= -RiskManagement.CONSTITUTION.DAILY_DRAWDOWN_KILL_SWITCH) {
            console.error("!!! RISK GUARDIAN: KILL SWITCH TRIGGERED !!!");
            // In a real OS-level implementation, this would trigger a process exit or API block
            return true; // BLOCKED
        }
        return false; // CLEAR
    },

    // --- BLUEPRINT FINAL: RISK GUARDIAN DETERMINISTIC RULES ---
    validateTrade: (
        dailyPnL: number, 
        currentSymbol: string,
        tickers: MarketTicker[],
        priceHistory: { [symbol: string]: number[] },
        isMacroEventImminent: boolean
    ): 'CLEAR' | 'BLOCKED' | 'PAUSE' => {
        // 1. Daily Drawdown Kill-Switch
        if (RiskManagement.checkKillSwitch(dailyPnL)) {
            return 'BLOCKED';
        }
        
        // 2. Correlation Filter
        const matrix = CorrelationMonitor.calculateMatrix(tickers, priceHistory);
        let maxCorr = 0;
        for (const otherSym in matrix[currentSymbol]) {
            if (otherSym !== currentSymbol) {
                maxCorr = Math.max(maxCorr, Math.abs(matrix[currentSymbol][otherSym]));
            }
        }

        if (maxCorr > RiskManagement.CONSTITUTION.MAX_CORRELATION) {
            console.warn(`!!! RISK GUARDIAN: CORRELATION LIMIT EXCEEDED (${maxCorr.toFixed(2)}) !!!`);
            return 'BLOCKED';
        }
        
        // 3. Macro Event Pause
        if (isMacroEventImminent) {
            console.info("!!! RISK GUARDIAN: MACRO EVENT IMMINENT - PAUSED !!!");
            return 'PAUSE';
        }

        return 'CLEAR';
    },

    // --- POSITION SIZING (DETERMINISTIC) ---
    calculatePositionSize: (equity: number, riskPct: number, entry: number, stopLoss: number): { size: number, totalRisk: number } => {
        const amountToRisk = equity * riskPct;
        const riskPerShare = Math.abs(entry - stopLoss);
        
        if (riskPerShare === 0) return { size: 0, totalRisk: 0 };
        
        const size = amountToRisk / riskPerShare;
        return {
            size,
            totalRisk: amountToRisk
        };
    },

    // --- KELLY CRITERION (Optimal Bet Size) ---
    calculateKelly: (winRate: number, profitFactor: number): number => {
        // Kelly % = W - (1 - W) / R
        // W = Win rate, R = Win/Loss ratio
        const kelly = winRate - (1 - winRate) / profitFactor;
        return Math.max(0, Math.min(0.2, kelly)); // Cap at 20% for safety (Fractional Kelly)
    },

    // --- ATR-BASED STOP LOSS ---
    calculateATRStop: (entry: number, atr: number, multiplier: number = 2, direction: 'BUY' | 'SELL'): number => {
        if (direction === 'BUY') return entry - (atr * multiplier);
        return entry + (atr * multiplier);
    },

    // --- PORTFOLIO EXPOSURE SCAN ---
    analyzeExposure: (positions: PortfolioPosition[]): { totalValue: number, concentrationRisk: boolean } => {
        const totalValue = positions.reduce((acc, p) => acc + (p.amount * p.currentPrice), 0);
        
        // Flag if any single position is > 25% of portfolio
        const concentrationRisk = positions.some(p => (p.amount * p.currentPrice) / totalValue > 0.25);
        
        return {
            totalValue,
            concentrationRisk
        };
    }
};
