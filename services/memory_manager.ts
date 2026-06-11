
import { SwarmAgent, SystemConfiguration } from '../types';
import { storageManager } from './storage_manager';

interface AgentMemory {
    id: string;
    messages: { role: string; parts: { text: string }[] }[];
    summary: string;
    lastState: Record<string, unknown>;
    timestamp: number;
}

// Internal sync cache for MemoryManager
let memoryCache: Record<string, AgentMemory> = {};
let isInit = false;

export class MemoryManager {
    private static STORAGE_KEY = 'NANGGROE_AGENT_MEMORY';
    private static SYSTEM_STATE_KEY = 'NANGGROE_SYSTEM_STATE';

    static async init() {
        if (isInit) return;
        const stored = await storageManager.getItem(this.STORAGE_KEY);
        if (stored) {
            try {
                memoryCache = JSON.parse(stored);
            } catch {
                memoryCache = {};
            }
        }
        isInit = true;
    }

    static saveAgentMemory(agentId: string, memory: Partial<AgentMemory>) {
        memoryCache[agentId] = {
            ...(memoryCache[agentId] || {}),
            ...memory,
            id: agentId,
            timestamp: Date.now()
        } as AgentMemory;
        
        storageManager.setItem(this.STORAGE_KEY, JSON.stringify(memoryCache)).catch(console.error);
    }

    static getAgentMemory(agentId: string): AgentMemory | null {
        return memoryCache[agentId] || null;
    }

    static getAllMemory(): Record<string, AgentMemory> {
        return memoryCache;
    }

    static clearMemory(agentId?: string) {
        if (agentId) {
            delete memoryCache[agentId];
            storageManager.setItem(this.STORAGE_KEY, JSON.stringify(memoryCache)).catch(console.error);
        } else {
            memoryCache = {};
            storageManager.removeItem(this.STORAGE_KEY).catch(console.error);
        }
    }
    
    static saveSystemState(state: Record<string, unknown>) {
        storageManager.setItem(this.SYSTEM_STATE_KEY, JSON.stringify({
            ...state,
            timestamp: Date.now()
        })).catch(console.error);
    }
    
    static async loadSystemState(): Promise<Record<string, unknown> | null> {
        const stored = await storageManager.getItem(this.SYSTEM_STATE_KEY);
        if (!stored) return null;
        try {
            return JSON.parse(stored);
        } catch {
            return null;
        }
    }
}
