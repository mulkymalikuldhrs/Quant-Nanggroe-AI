
import { storageManager } from "./storage_manager";

export const BackupService = {
    /**
     * Exports the entire system state as a JSON file
     */
    exportToFile: async () => {
        const data = await storageManager.exportData();
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `nanggroe_ai_backup_${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    },

    /**
     * Imports system state from a JSON file
     */
    importFromFile: async (file: File): Promise<boolean> => {
        return new Promise((resolve) => {
            const reader = new FileReader();
            reader.onload = async (e) => {
                try {
                    const data = JSON.parse(e.target?.result as string);
                    await storageManager.importData(data);
                    // Force reload to apply changes
                    window.location.reload();
                    resolve(true);
                } catch (err) {
                    console.error("Import failed:", err);
                    resolve(false);
                }
            };
            reader.readAsText(file);
        });
    }
};
