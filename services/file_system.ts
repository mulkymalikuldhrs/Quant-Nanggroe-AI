
import { VirtualFile, PortfolioPosition, DataSource, SystemConfiguration, KnowledgeItem, TradeHistoryItem } from "../types";
import { MarketService } from "./market"; 
import { storageManager } from "./storage_manager";

// The "Hard Drive" of the OS
const STORAGE_KEY_VFS = 'manus_vfs_data';
const STORAGE_KEY_CORE_INSTRUCTIONS = 'manus_core_instructions';
const STORAGE_KEY_PORTFOLIO = 'manus_portfolio_data';
const STORAGE_KEY_TRADE_HISTORY = 'manus_trade_history';
const STORAGE_KEY_DATASOURCES = 'manus_data_sources';
const STORAGE_KEY_CONFIG = 'manus_system_config';
const STORAGE_KEY_MEMORY = 'manus_long_term_memory';

const DEFAULT_DATA_SOURCES: DataSource[] = [
    // ... same as before
];

// In-memory cache for synchronous access, synced with StorageManager
const syncCache: Record<string, string> = {};

export const BrowserFS = {
    
    /**
     * Initialize the file system by loading all data from StorageManager into sync cache
     */
    init: async () => {
        const keys = [
            STORAGE_KEY_VFS, 
            STORAGE_KEY_CORE_INSTRUCTIONS, 
            STORAGE_KEY_PORTFOLIO, 
            STORAGE_KEY_TRADE_HISTORY, 
            STORAGE_KEY_DATASOURCES, 
            STORAGE_KEY_CONFIG, 
            STORAGE_KEY_MEMORY
        ];
        
        for (const key of keys) {
            const val = await storageManager.getItem(key);
            if (val) syncCache[key] = val;
        }
        console.log("[FileSystem] Synchronized with StorageManager.");
    },

    // --- Internal Helpers ---
    _get: (key: string): string | null => syncCache[key] || null,
    
    _set: (key: string, value: string) => {
        syncCache[key] = value;
        // Fire and forget storage update (async)
        storageManager.setItem(key, value).catch(console.error);
    },

    // --- File Operations ---

    listFiles: (): VirtualFile[] => {
        const raw = BrowserFS._get(STORAGE_KEY_VFS);
        return raw ? JSON.parse(raw) : [];
    },

    writeFile: (name: string, content: string, type: string = 'text/plain') => {
        const files = BrowserFS.listFiles();
        const existingIndex = files.findIndex(f => f.name === name);
        const newFile: VirtualFile = { name, content, type, lastModified: Date.now() };

        if (existingIndex >= 0) {
            files[existingIndex] = newFile;
        } else {
            files.push(newFile);
        }
        BrowserFS._set(STORAGE_KEY_VFS, JSON.stringify(files));
        return `File '${name}' written successfully to VFS.`;
    },

    readFile: (name: string): string => {
        const files = BrowserFS.listFiles();
        const file = files.find(f => f.name === name);
        if (!file) throw new Error(`File '${name}' not found in VFS.`);
        return file.content;
    },

    // --- System Boot Sync ---
    initializeSystemFiles: (files: Record<string, string>) => {
        const currentFiles = BrowserFS.listFiles();
        let updated = false;
        
        Object.entries(files).forEach(([name, content]) => {
            const existing = currentFiles.find(f => f.name === name);
            if (!existing || existing.content !== content) {
                BrowserFS.writeFile(name, content, 'text/markdown');
                updated = true;
            }
        });
        
        BrowserFS.initializeDataSources();
        
        if (updated) console.log("[FileSystem] System files synced/updated to VFS.");
    },

    // --- System Config Management ---

    saveSystemConfig: (config: SystemConfiguration) => {
        BrowserFS._set(STORAGE_KEY_CONFIG, JSON.stringify(config));
    },

    loadSystemConfig: (): SystemConfiguration | null => {
        const raw = BrowserFS._get(STORAGE_KEY_CONFIG);
        return raw ? JSON.parse(raw) : null;
    },

    // --- Data Source Management ---

    initializeDataSources: () => {
        const raw = BrowserFS._get(STORAGE_KEY_DATASOURCES);
        if (!raw) {
            console.log("[FileSystem] Bootstrapping Default Data Sources...");
            BrowserFS._set(STORAGE_KEY_DATASOURCES, JSON.stringify(DEFAULT_DATA_SOURCES));
        }
    },

    getDataSources: (): DataSource[] => {
        const raw = BrowserFS._get(STORAGE_KEY_DATASOURCES);
        return raw ? JSON.parse(raw) : DEFAULT_DATA_SOURCES;
    },

    addDataSource: (source: DataSource) => {
        const sources = BrowserFS.getDataSources();
        const index = sources.findIndex(s => s.id === source.id || s.endpoint === source.endpoint);
        if (index >= 0) {
            sources[index] = { ...sources[index], ...source }; 
        } else {
            sources.push(source);
        }
        BrowserFS._set(STORAGE_KEY_DATASOURCES, JSON.stringify(sources));
        return `Data Source '${source.name}' added to Neural Registry.`;
    },

    removeDataSource: (id: string) => {
        let sources = BrowserFS.getDataSources();
        sources = sources.filter(s => s.id !== id);
        BrowserFS._set(STORAGE_KEY_DATASOURCES, JSON.stringify(sources));
        return `Data Source removed from registry.`;
    },

    // --- Core System Evolution ---

    getCoreInstructions: (): string => {
        return BrowserFS._get(STORAGE_KEY_CORE_INSTRUCTIONS) || 
`<ROLE>
... [Same Core Instructions] ...
`;
    },

    updateCoreInstructions: (newInstructions: string) => {
        BrowserFS._set(STORAGE_KEY_CORE_INSTRUCTIONS, newInstructions);
    },

    applySystemPatch: (patchCode: string, description: string) => {
        const current = BrowserFS.getCoreInstructions();
        const updated = `${current}\n\n[SYSTEM PATCH ${Date.now()}]: ${description}\nRULE: ${patchCode}`;
        BrowserFS.updateCoreInstructions(updated);
        return "Kernel updated. Memory re-calibrated with new behavioral protocols.";
    },

    // --- LONG TERM MEMORY (VECTOR-LITE) ---
    
    saveMemory: (content: string, tags: string[], agentId?: string) => {
        const raw = BrowserFS._get(STORAGE_KEY_MEMORY);
        const memories: KnowledgeItem[] = raw ? JSON.parse(raw) : [];
        
        if (memories.length > 200) memories.shift();

        memories.push({
            id: `mem-${Date.now()}`,
            category: 'memory',
            content: content,
            sourceAgentId: agentId || 'Alpha Prime',
            timestamp: Date.now(),
            confidence: 100,
            tags: tags
        });
        BrowserFS._set(STORAGE_KEY_MEMORY, JSON.stringify(memories));
    },

    loadMemoryByAgent: (agentId: string): string => {
        const raw = BrowserFS._get(STORAGE_KEY_MEMORY);
        if (!raw) return "";
        const memories: KnowledgeItem[] = JSON.parse(raw);
        
        const agentMemories = memories.filter(m => m.sourceAgentId === agentId);
        if (agentMemories.length === 0) return "";
        
        return agentMemories.slice(-5).map(h => 
            `[AGENT MEMORY - ${new Date(h.timestamp).toLocaleDateString()}]: ${h.content}`
        ).join('\n');
    },

    searchMemory: (query: string): string => {
        const raw = BrowserFS._get(STORAGE_KEY_MEMORY);
        if (!raw) return "";
        const memories: KnowledgeItem[] = JSON.parse(raw);
        
        const terms = query.toLowerCase().split(' ').filter(w => w.length > 3);
        
        const hits = memories.filter(m => {
            const contentLower = m.content.toLowerCase();
            return terms.some(t => contentLower.includes(t) || m.tags.includes(t));
        });

        if (hits.length === 0) return "";
        
        return hits.slice(-3).map(h => 
            `[PAST MEMORY - ${new Date(h.timestamp).toLocaleDateString()}]: ${h.content.substring(0, 200)}...`
        ).join('\n');
    },

    // --- Portfolio Management ---

    getPortfolio: (): PortfolioPosition[] => {
        const raw = BrowserFS._get(STORAGE_KEY_PORTFOLIO);
        return raw ? JSON.parse(raw) : [
            { ticker: 'USD', amount: 100000, avgPrice: 1, currentPrice: 1, pnl: 0, lastUpdated: Date.now() } 
        ];
    },

    getTradeHistory: (): TradeHistoryItem[] => {
        const raw = BrowserFS._get(STORAGE_KEY_TRADE_HISTORY);
        return raw ? JSON.parse(raw) : [];
    },

    updatePortfolioPrices: (updates: Record<string, number>) => {
        const portfolio = BrowserFS.getPortfolio();
        let changed = false;

        const updatedPortfolio = portfolio.map(pos => {
            if (pos.ticker !== 'USD' && updates[pos.ticker]) {
                const newPrice = updates[pos.ticker];
                const pnl = (newPrice - pos.avgPrice) * pos.amount;
                changed = true;
                return { ...pos, currentPrice: newPrice, pnl, lastUpdated: Date.now() };
            }
            return pos;
        });

        if (changed) {
            BrowserFS._set(STORAGE_KEY_PORTFOLIO, JSON.stringify(updatedPortfolio));
        }
    },

    executeTrade: async (ticker: string, action: 'BUY' | 'SELL', amount: number, price: number) => {
        const portfolio = BrowserFS.getPortfolio();
        const history = BrowserFS.getTradeHistory();
        
        const cashIndex = portfolio.findIndex(p => p.ticker === 'USD');
        let cash = portfolio[cashIndex];
        
        let positionIndex = portfolio.findIndex(p => p.ticker === ticker);
        let position = positionIndex >= 0 ? portfolio[positionIndex] : { ticker, amount: 0, avgPrice: 0, currentPrice: price, pnl: 0, lastUpdated: Date.now() };

        const FEE_RATE = 0.001; 
        const SLIPPAGE = 0.0005; 
        
        const execPrice = action === 'BUY' ? price * (1 + SLIPPAGE) : price * (1 - SLIPPAGE);
        const rawValue = amount * execPrice;
        const fee = rawValue * FEE_RATE;
        const totalCost = rawValue + fee;
        const totalProceeds = rawValue - fee;

        let tradeNote = "";
        let realizedPnL = 0;

        let activeSignalNames: string[] = [];
        try {
            const marketData = await MarketService.getPrice(ticker);
            if (marketData && marketData.activeSignals) {
                activeSignalNames = marketData.activeSignals
                    .filter(s => s.type === action)
                    .map(s => s.name);
            }
        } catch(e) { console.warn("Failed to snapshot signals for ML"); }

        if (action === 'BUY') {
            if (cash.amount < totalCost) return `Trade Rejected: Insufficient USD. Req: $${totalCost.toFixed(2)}`;
            
            const prevValue = position.amount * position.avgPrice;
            const newValue = prevValue + rawValue; 
            position.avgPrice = newValue / (position.amount + amount);
            position.amount += amount;
            
            cash.amount -= totalCost;
            tradeNote = `BOUGHT ${amount} ${ticker} @ $${execPrice.toFixed(2)} (Fee: $${fee.toFixed(2)})`;

        } else if (action === 'SELL') {
            if (position.amount < amount) return `Trade Rejected: Insufficient Holdings.`;
            
            const costBasis = amount * position.avgPrice;
            realizedPnL = totalProceeds - costBasis;

            position.amount -= amount;
            cash.amount += totalProceeds;
            tradeNote = `SOLD ${amount} ${ticker} @ $${execPrice.toFixed(2)} (PnL: $${realizedPnL.toFixed(2)})`;
        }

        position.currentPrice = price;
        position.lastUpdated = Date.now();

        if (position.amount < 0.000001) {
            if (positionIndex >= 0) portfolio.splice(positionIndex, 1); 
        } else {
            if (positionIndex >= 0) portfolio[positionIndex] = position;
            else portfolio.push(position);
        }
        portfolio[cashIndex] = cash; 

        const tradeRecord: TradeHistoryItem = {
            id: `trd-${Date.now()}`,
            timestamp: Date.now(),
            ticker, action, amount,
            price: execPrice,
            totalValue: rawValue,
            fees: fee,
            realizedPnL: action === 'SELL' ? realizedPnL : undefined,
            triggeredBySignals: activeSignalNames
        };
        history.unshift(tradeRecord);

        BrowserFS._set(STORAGE_KEY_PORTFOLIO, JSON.stringify(portfolio));
        BrowserFS._set(STORAGE_KEY_TRADE_HISTORY, JSON.stringify(history));
        
        return `✅ EXECUTION CONFIRMED: ${tradeNote}`;
    }
};
