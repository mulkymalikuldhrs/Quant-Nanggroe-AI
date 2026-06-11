
import { KnowledgeItem, VirtualDiskNode } from "../types";
import { BrowserFS } from "./file_system";
import { storageManager } from "./storage_manager";

const STORAGE_KEY_DISK_NODES = 'manus_disk_c_nodes';

// Sync cache for internal use
let cachedRoot: VirtualDiskNode | null = null;

export const KnowledgeBase = {
    
    // Initialize Disk C: structure if it doesn't exist
    initDisk: async () => {
        const raw = await storageManager.getItem(STORAGE_KEY_DISK_NODES);
        if (!raw) {
            const root: VirtualDiskNode = {
                id: 'root-c',
                name: 'C:',
                type: 'folder',
                path: 'C:',
                children: [
                    { id: 'dir-market', name: 'Market', type: 'folder', path: 'C:/Market', children: [], lastModified: Date.now() },
                    { id: 'dir-news', name: 'News', type: 'folder', path: 'C:/News', children: [], lastModified: Date.now() },
                    { id: 'dir-geo', name: 'Geo', type: 'folder', path: 'C:/Geo', children: [], lastModified: Date.now() },
                    { id: 'dir-sentiment', name: 'Sentiment', type: 'folder', path: 'C:/Sentiment', children: [], lastModified: Date.now() },
                    { id: 'dir-institutional', name: 'Institutional', type: 'folder', path: 'C:/Institutional', children: [], lastModified: Date.now() },
                    { id: 'dir-ai', name: 'AI_Updates', type: 'folder', path: 'C:/AI_Updates', children: [], lastModified: Date.now() },
                    { id: 'dir-system', name: 'System', type: 'folder', path: 'C:/System', children: [], lastModified: Date.now() },
                ],
                lastModified: Date.now()
            };
            await storageManager.setItem(STORAGE_KEY_DISK_NODES, JSON.stringify(root));
            cachedRoot = root;
        } else {
            cachedRoot = JSON.parse(raw);
        }
    },

    getRoot: (): VirtualDiskNode => {
        if (!cachedRoot) {
            // This is a fallback for sync access if init hasn't finished, 
            // though in v15.1.0 we should ensure init is called at boot.
            return { id: 'root-c', name: 'C:', type: 'folder', path: 'C:', children: [], lastModified: Date.now() };
        }
        return cachedRoot;
    },

    saveNodes: (root: VirtualDiskNode) => {
        cachedRoot = root;
        storageManager.setItem(STORAGE_KEY_DISK_NODES, JSON.stringify(root)).catch(console.error);
    },

    // Add a file to Disk C:
    saveToDisk: (item: KnowledgeItem) => {
        const root = KnowledgeBase.getRoot();
        const pathParts = (item.path || 'C:/Research').split('/');
        
        let current = root;
        const folders = pathParts[0] === 'C:' ? pathParts.slice(1, -1) : pathParts.slice(0, -1);
        const fileName = pathParts[pathParts.length - 1];

        folders.forEach(folderName => {
            let next = current.children?.find(c => c.name === folderName && c.type === 'folder');
            if (!next) {
                next = {
                    id: `dir-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`,
                    name: folderName,
                    type: 'folder',
                    path: `${current.path}/${folderName}`,
                    children: [],
                    lastModified: Date.now()
                };
                current.children = current.children || [];
                current.children.push(next);
            }
            current = next;
        });

        const fileNode: VirtualDiskNode = {
            id: `file-${item.id}`,
            name: fileName,
            type: 'file',
            path: item.path || `C:/Research/${fileName}`,
            contentId: item.id,
            lastModified: Date.now()
        };

        current.children = current.children || [];
        const existingIndex = current.children.findIndex(c => c.name === fileName && c.type === 'file');
        if (existingIndex >= 0) {
            current.children[existingIndex] = fileNode;
        } else {
            current.children.push(fileNode);
        }

        KnowledgeBase.saveNodes(root);
        BrowserFS.saveMemory(item.content, item.tags, item.sourceAgentId);
        
        return fileNode;
    },

    readFile: (path: string): KnowledgeItem | null => {
        const root = KnowledgeBase.getRoot();
        const findNode = (node: VirtualDiskNode, targetPath: string): VirtualDiskNode | null => {
            if (node.path === targetPath) return node;
            if (node.children) {
                for (const child of node.children) {
                    const found = findNode(child, targetPath);
                    if (found) return found;
                }
            }
            return null;
        };

        const node = findNode(root, path);
        if (node && node.type === 'file' && node.contentId) {
            const rawMemory = BrowserFS._get('manus_long_term_memory');
            const memories: KnowledgeItem[] = rawMemory ? JSON.parse(rawMemory) : [];
            return memories.find(m => m.id === node.contentId) || null;
        }
        return null;
    }
};

