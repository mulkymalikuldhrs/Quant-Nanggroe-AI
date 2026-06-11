
import { StorageAdapter, LocalStorageAdapter, IndexedDBAdapter } from "./storage_adapter";

export type StorageMode = 'local' | 'cloud' | 'hybrid';

/**
 * Cloud Adapter Template (to be implemented with Supabase/Firebase/S3)
 */
class CloudAdapterPlaceholder implements StorageAdapter {
    name = "Cloud Storage (Placeholder)";
    async isAvailable() { return false; }
    async getItem() { return null; }
    async setItem() { }
    async removeItem() { }
    async clear() { }
    async keys() { return []; }
}

export class StorageManager {
    private static instance: StorageManager;
    private adapters: Map<string, StorageAdapter> = new Map();
    private currentMode: StorageMode = 'local';
    private primaryAdapterName: string = 'indexed-db';

    private constructor() {
        // Register adapters
        this.registerAdapter('local-storage', new LocalStorageAdapter());
        this.registerAdapter('indexed-db', new IndexedDBAdapter());
        this.registerAdapter('cloud-storage', new CloudAdapterPlaceholder());
        
        // Default to IndexedDB for larger capacity "Local File Storage" feel
        this.primaryAdapterName = 'indexed-db';
    }

    static getInstance(): StorageManager {
        if (!StorageManager.instance) {
            StorageManager.instance = new StorageManager();
        }
        return StorageManager.instance;
    }

    registerAdapter(name: string, adapter: StorageAdapter) {
        this.adapters.set(name, adapter);
    }

    setMode(mode: StorageMode, primaryAdapter?: string) {
        this.currentMode = mode;
        if (primaryAdapter) {
            this.primaryAdapterName = primaryAdapter;
        }
    }

    getMode(): StorageMode {
        return this.currentMode;
    }

    private getPrimaryAdapter(): StorageAdapter {
        const adapter = this.adapters.get(this.primaryAdapterName);
        if (!adapter) throw new Error(`Primary adapter ${this.primaryAdapterName} not found`);
        return adapter;
    }

    async getItem(key: string): Promise<string | null> {
        const primary = this.getPrimaryAdapter();
        let value = await primary.getItem(key);

        // In hybrid mode, if not in primary, check others
        if (!value && this.currentMode === 'hybrid') {
            for (const [name, adapter] of this.adapters) {
                if (name === this.primaryAdapterName) continue;
                value = await adapter.getItem(key);
                if (value) {
                    // Sync back to primary if found elsewhere
                    await primary.setItem(key, value);
                    break;
                }
            }
        }
        return value;
    }

    async setItem(key: string, value: string): Promise<void> {
        const primary = this.getPrimaryAdapter();
        await primary.setItem(key, value);

        // In hybrid mode, sync to all available adapters
        if (this.currentMode === 'hybrid' || this.currentMode === 'cloud') {
            const syncPromises = Array.from(this.adapters.entries())
                .filter(([name]) => name !== this.primaryAdapterName)
                .map(([_, adapter]) => adapter.setItem(key, value).catch(e => console.error(`Sync error to ${adapter.name}:`, e)));
            await Promise.all(syncPromises);
        }
    }

    async removeItem(key: string): Promise<void> {
        const primary = this.getPrimaryAdapter();
        await primary.removeItem(key);

        if (this.currentMode === 'hybrid' || this.currentMode === 'cloud') {
            const syncPromises = Array.from(this.adapters.entries())
                .filter(([name]) => name !== this.primaryAdapterName)
                .map(([_, adapter]) => adapter.removeItem(key).catch(e => console.error(`Sync error to ${adapter.name}:`, e)));
            await Promise.all(syncPromises);
        }
    }

    async clear(): Promise<void> {
        const primary = this.getPrimaryAdapter();
        await primary.clear();

        if (this.currentMode === 'hybrid' || this.currentMode === 'cloud') {
            const syncPromises = Array.from(this.adapters.entries())
                .filter(([name]) => name !== this.primaryAdapterName)
                .map(([_, adapter]) => adapter.clear().catch(e => console.error(`Sync error to ${adapter.name}:`, e)));
            await Promise.all(syncPromises);
        }
    }

    async keys(): Promise<string[]> {
        return this.getPrimaryAdapter().keys();
    }

    /**
     * Export all data from primary adapter as a JSON object
     */
    async exportData(): Promise<Record<string, string>> {
        const primary = this.getPrimaryAdapter();
        const allKeys = await primary.keys();
        const data: Record<string, string> = {};
        
        for (const key of allKeys) {
            const val = await primary.getItem(key);
            if (val) data[key] = val;
        }
        return data;
    }

    /**
     * Import data into primary adapter
     */
    async importData(data: Record<string, string>) {
        for (const [key, value] of Object.entries(data)) {
            await this.setItem(key, value);
        }
    }
}

export const storageManager = StorageManager.getInstance();
