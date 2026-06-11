
export interface StorageAdapter {
    name: string;
    isAvailable(): Promise<boolean>;
    getItem(key: string): Promise<string | null>;
    setItem(key: string, value: string): Promise<void>;
    removeItem(key: string): Promise<void>;
    clear(): Promise<void>;
    keys(): Promise<string[]>;
}

export class LocalStorageAdapter implements StorageAdapter {
    name = "Browser LocalStorage";

    async isAvailable(): Promise<boolean> {
        return typeof window !== 'undefined' && !!window.localStorage;
    }

    async getItem(key: string): Promise<string | null> {
        return localStorage.getItem(key);
    }

    async setItem(key: string, value: string): Promise<void> {
        localStorage.setItem(key, value);
    }

    async removeItem(key: string): Promise<void> {
        localStorage.removeItem(key);
    }

    async clear(): Promise<void> {
        localStorage.clear();
    }

    async keys(): Promise<string[]> {
        return Object.keys(localStorage);
    }
}

export class IndexedDBAdapter implements StorageAdapter {
    name = "IndexedDB (Persistent Local Storage)";
    private dbName = "QuantNanggroeDB";
    private storeName = "kv_store";
    private db: IDBDatabase | null = null;

    private async getDB(): Promise<IDBDatabase> {
        if (this.db) return this.db;
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, 1);
            request.onupgradeneeded = () => {
                request.result.createObjectStore(this.storeName);
            };
            request.onsuccess = () => {
                this.db = request.result;
                resolve(this.db);
            };
            request.onerror = () => reject(request.error);
        });
    }

    async isAvailable(): Promise<boolean> {
        return typeof indexedDB !== 'undefined';
    }

    async getItem(key: string): Promise<string | null> {
        const db = await this.getDB();
        return new Promise((resolve, reject) => {
            const transaction = db.transaction(this.storeName, 'readonly');
            const store = transaction.objectStore(this.storeName);
            const request = store.get(key);
            request.onsuccess = () => resolve(request.result || null);
            request.onerror = () => reject(request.error);
        });
    }

    async setItem(key: string, value: string): Promise<void> {
        const db = await this.getDB();
        return new Promise((resolve, reject) => {
            const transaction = db.transaction(this.storeName, 'readwrite');
            const store = transaction.objectStore(this.storeName);
            const request = store.put(value, key);
            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    }

    async removeItem(key: string): Promise<void> {
        const db = await this.getDB();
        return new Promise((resolve, reject) => {
            const transaction = db.transaction(this.storeName, 'readwrite');
            const store = transaction.objectStore(this.storeName);
            const request = store.delete(key);
            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    }

    async clear(): Promise<void> {
        const db = await this.getDB();
        return new Promise((resolve, reject) => {
            const transaction = db.transaction(this.storeName, 'readwrite');
            const store = transaction.objectStore(this.storeName);
            const request = store.clear();
            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    }

    async keys(): Promise<string[]> {
        const db = await this.getDB();
        return new Promise((resolve, reject) => {
            const transaction = db.transaction(this.storeName, 'readonly');
            const store = transaction.objectStore(this.storeName);
            const request = store.getAllKeys();
            request.onsuccess = () => resolve(request.result.map(k => k.toString()));
            request.onerror = () => reject(request.error);
        });
    }
}
