
import { BrowserFS } from "./file_system";
import { TradeHistoryItem, NeuralWeights, EvolutionState } from "../types";

const STORAGE_KEY_EVOLUTION = 'manus_evolution_state';

// --- HYPERPARAMETERS ---
const LEARNING_RATE = 0.1; // How much to adjust weights per trade
const MIN_WEIGHT = 0.5;
const MAX_WEIGHT = 10.0;

export const MLEngine = {
    
    getEvolutionState: (): EvolutionState => {
        const raw = localStorage.getItem(STORAGE_KEY_EVOLUTION);
        if (raw) return JSON.parse(raw);
        
        // Default Weights (Generation 0)
        return {
            generation: 0,
            lastOptimization: Date.now(),
            bestStrategies: [],
            weights: {
                "Golden Cross (EMA 20/50)": 5,
                "RSI Dip Buy (Trend Following)": 4,
                "Bollinger Breakout": 3,
                "Full Bullish Alignment (Price > All MAs)": 6
            }
        };
    },

    saveEvolutionState: (state: EvolutionState) => {
        localStorage.setItem(STORAGE_KEY_EVOLUTION, JSON.stringify(state));
    },

    // --- REINFORCEMENT LEARNING LOOP ---
    optimize: (): string => {
        const history = BrowserFS.getTradeHistory();
        const state = MLEngine.getEvolutionState();
        const weights = { ...state.weights };
        let learnedSomething = false;

        // Filter for closed trades (trades with realized PnL)
        const closedTrades = history.filter(t => t.realizedPnL !== undefined && t.triggeredBySignals);

        if (closedTrades.length === 0) return "No closed trades available for back-propagation.";

        closedTrades.forEach(trade => {
            const isWin = (trade.realizedPnL || 0) > 0;
            const signals = trade.triggeredBySignals || [];

            signals.forEach(sigName => {
                const currentWeight = weights[sigName] || 3.0; // Default weight if new signal
                
                let delta = 0;
                if (isWin) {
                    delta = LEARNING_RATE; // Reward
                } else {
                    delta = -LEARNING_RATE; // Punishment
                }

                // Apply update
                let newWeight = currentWeight + delta;
                newWeight = Math.max(MIN_WEIGHT, Math.min(MAX_WEIGHT, newWeight)); // Clamp
                
                if (Math.abs(newWeight - currentWeight) > 0.01) {
                    weights[sigName] = newWeight;
                    learnedSomething = true;
                }
            });
        });

        if (learnedSomething) {
            state.generation += 1;
            state.lastOptimization = Date.now();
            state.weights = weights;
            
            // Determine "Best Strategies"
            state.bestStrategies = Object.entries(weights)
                .sort(([, a], [, b]) => b - a)
                .slice(0, 3)
                .map(([k]) => k);

            MLEngine.saveEvolutionState(state);
            return `Evolution Complete (Gen ${state.generation}). Optimized weights for ${Object.keys(weights).length} strategies based on ${closedTrades.length} trades.`;
        }

        return "Optimization run completed. No significant weight adjustments needed.";
    },

    getWeight: (signalName: string): number => {
        const state = MLEngine.getEvolutionState();
        return state.weights[signalName] || 3.0; // Default for unknown signals
    }
};
