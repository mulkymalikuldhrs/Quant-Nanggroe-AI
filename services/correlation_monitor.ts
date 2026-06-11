
import { MarketTicker } from "../types";
import { MathEngine } from "./math_engine";

export interface CorrelationMatrix {
    [symbol: string]: {
        [target: string]: number;
    };
}

export const CorrelationMonitor = {
    calculateMatrix: (tickers: MarketTicker[], priceHistory: { [symbol: string]: number[] }): CorrelationMatrix => {
        const matrix: CorrelationMatrix = {};
        const symbols = Object.keys(priceHistory);

        for (let i = 0; i < symbols.length; i++) {
            const symA = symbols[i];
            matrix[symA] = {};
            for (let j = 0; j < symbols.length; j++) {
                const symB = symbols[j];
                if (symA === symB) {
                    matrix[symA][symB] = 1.0;
                    continue;
                }
                
                const correlation = MathEngine.calculateCorrelation(
                    priceHistory[symA],
                    priceHistory[symB]
                );
                matrix[symA][symB] = correlation;
            }
        }
        return matrix;
    },

    isHighlyCorrelated: (matrix: CorrelationMatrix, symA: string, symB: string, threshold: number = 0.7): boolean => {
        if (!matrix[symA] || matrix[symA][symB] === undefined) return false;
        return Math.abs(matrix[symA][symB]) > threshold;
    }
};
