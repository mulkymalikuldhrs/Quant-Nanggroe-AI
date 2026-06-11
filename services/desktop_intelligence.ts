import { WindowState, SystemAction } from "../types";

export const DesktopIntelligence = {
    /**
     * Captures a textual "screenshot" of the current OS state for the AI
     */
    getSystemSnapshot: (windows: Record<string, any>): string => {
        const activeWindows = Object.values(windows)
            .filter(w => w.isOpen && !w.isMinimized)
            .map(w => `- [${w.title}] at pos(${w.defaultPos.x}, ${w.defaultPos.y}) size(${w.defaultSize.width}x${w.defaultSize.height})`);
        
        return `
SYSTEM DESKTOP SNAPSHOT:
Total Open Windows: ${activeWindows.length}
Windows List:
${activeWindows.join('\n')}

CAPABILITIES:
- You can move windows.
- You can focus windows.
- You can read content from 'browser' or 'portfolio'.
- You can execute trades via 'trading_terminal'.
        `.trim();
    },

    /**
     * Translates high-level agent intents into SystemActions
     */
    parseIntent: (intent: string): SystemAction[] => {
        const actions: SystemAction[] = [];
        
        if (intent.includes('open') || intent.includes('show')) {
            const targets = ['portfolio', 'market', 'browser', 'settings', 'terminal', 'trading_terminal'];
            targets.forEach(t => {
                if (intent.toLowerCase().includes(t)) {
                    actions.push({ type: 'OPEN_WINDOW', payload: t });
                }
            });
        }

        if (intent.includes('navigate') || intent.includes('go to')) {
            const urlMatch = intent.match(/https?:\/\/[^\s]+/);
            if (urlMatch) {
                actions.push({ type: 'NAVIGATE_BROWSER', payload: urlMatch[0] });
            }
        }

        return actions;
    }
};
