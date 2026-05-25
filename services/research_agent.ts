
import { KnowledgeBase } from "./knowledge_base";
import { KnowledgeItem, ResearchSource } from "../types";
import { MarketService } from "./market";

const RESEARCH_SOURCES: ResearchSource[] = [
    { id: 'src-news', name: 'Global News Hub', url: 'https://finnhub.io/api/v1/news?category=general', type: 'news' },
    { id: 'src-market', name: 'Market Intelligence', url: 'https://api.coincap.io/v2/assets', type: 'market' },
    { id: 'src-geo', name: 'Geopolitical Data', url: 'https://restcountries.com/v3.1/all', type: 'geo' },
    { id: 'src-sentiment', name: 'Social Sentiment', url: 'https://cryptopanic.com/api/v1/posts/', type: 'sentiment' },
    { id: 'src-institutional', name: 'Institutional Tracker', url: 'https://api.whale-alert.io/v1/transaction', type: 'institutional' },
    { id: 'src-ai', name: 'AI Models Update', url: 'https://huggingface.co/api/models', type: 'ai' },
];

export const ResearchAgent = {
    isAutonomouslyRunning: false,
    intervalId: null as any,
    logs: [] as string[],

    getLogs: () => ResearchAgent.logs,

    startAutonomousResearch: (intervalMs: number = 60000) => {
        if (ResearchAgent.isAutonomouslyRunning) return;
        ResearchAgent.isAutonomouslyRunning = true;
        ResearchAgent.addLog("Autonomous Research Agent v11.4 started.");
        
        ResearchAgent.executeRound();
        ResearchAgent.intervalId = setInterval(() => {
            ResearchAgent.executeRound();
        }, intervalMs);
    },

    stopAutonomousResearch: () => {
        if (ResearchAgent.intervalId) {
            clearInterval(ResearchAgent.intervalId);
            ResearchAgent.intervalId = null;
        }
        ResearchAgent.isAutonomouslyRunning = false;
        ResearchAgent.addLog("Autonomous Research Agent stopped.");
    },

    addLog: (msg: string) => {
        const log = `[${new Date().toLocaleTimeString()}] ${msg}`;
        ResearchAgent.logs = [log, ...ResearchAgent.logs].slice(0, 100);
        console.log(log);
    },

    executeRound: async () => {
        ResearchAgent.addLog("--- NEW INTELLIGENCE HARVEST ROUND ---");
        
        for (const source of RESEARCH_SOURCES) {
            try {
                ResearchAgent.addLog(`Analyzing ${source.name}...`);
                await ResearchAgent.processSource(source);
                source.lastScanned = Date.now();
            } catch (error) {
                ResearchAgent.addLog(`!! Error at ${source.name}: ${error}`);
            }
        }
        
        ResearchAgent.addLog("Intelligence round synced to Disk C:.");
    },

    processSource: async (source: ResearchSource) => {
        let content = "";
        let path = `C:/${source.type.toUpperCase()}/${source.name.replace(/\s+/g, '_')}`;

        switch (source.type) {
            case 'news': {
                const news = await MarketService.getNews();
                if (news && news.length > 0) {
                    content = `TOP HEADLINES (${new Date().toLocaleDateString()}):\n` + 
                              news.slice(0, 5).map(n => `- ${n.headline} (${n.source})`).join('\n');
                    path += `/NEWS_${Date.now()}.txt`;
                } else {
                    // No API key configured — skip rather than fabricate data
                    ResearchAgent.addLog(`Skipped ${source.name}: Finnhub API key not configured`);
                    return;
                }
                break;
            }
            case 'market': {
                const btc = await MarketService.getPrice('BTC');
                const eth = await MarketService.getPrice('ETH');
                if (btc || eth) {
                    content = `MARKET SNAPSHOT:\nBTC: $${btc?.current_price || 'N/A'} (${btc?.price_change_percentage_24h || 0}%)\nETH: $${eth?.current_price || 'N/A'} (${eth?.price_change_percentage_24h || 0}%)`;
                    path += `/SNAPSHOT_${Date.now()}.txt`;
                } else {
                    ResearchAgent.addLog(`Skipped ${source.name}: Market data unavailable`);
                    return;
                }
                break;
            }
            case 'geo': {
                // Free public API: RestCountries
                try {
                    const res = await fetch('https://restcountries.com/v3.1/region/southeast%20asia');
                    const data = await res.json();
                    content = `REGIONAL INTEL (SEA):\n` + data.slice(0, 5).map((c: any) => `- ${c.name.common}: Population ${c.population?.toLocaleString() || 'N/A'}`).join('\n');
                    path += `/GEO_REPORT_${Date.now()}.txt`;
                } catch (e) {
                    ResearchAgent.addLog(`Skipped ${source.name}: Geo API unavailable`);
                    return;
                }
                break;
            }
            case 'sentiment': {
                // TODO: Integrate with CryptoPanic API or similar sentiment provider
                // Requires API key for real social sentiment data
                ResearchAgent.addLog(`Skipped ${source.name}: Sentiment API not configured (requires CryptoPanic API key)`);
                return;
            }
            case 'institutional': {
                // TODO: Integrate with WhaleAlert API for real institutional flow data
                // Requires API key — see https://whale-alert.io/
                ResearchAgent.addLog(`Skipped ${source.name}: Institutional API not configured (requires WhaleAlert API key)`);
                return;
            }
            case 'ai': {
                // Fetch real AI model data from HuggingFace
                try {
                    const res = await fetch('https://huggingface.co/api/models?sort=downloads&direction=-1&limit=5');
                    const data = await res.json();
                    content = `AI ECOSYSTEM UPDATE:\n` + data.map((m: any) => `- ${m.id} (Downloads: ${m.downloads?.toLocaleString() || 'N/A'})`).join('\n');
                    path += `/AI_CORE_${Date.now()}.txt`;
                } catch (e) {
                    ResearchAgent.addLog(`Skipped ${source.name}: HuggingFace API unavailable`);
                    return;
                }
                break;
            }
            default:
                content = `Data collected from ${source.name} at ${new Date().toISOString()}`;
                path += `/DATA_${Date.now()}.txt`;
        }

        if (content) {
            const item: KnowledgeItem = {
                id: `res-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`,
                category: 'research',
                content,
                sourceAgentId: 'ResearchAgent',
                timestamp: Date.now(),
                confidence: source.type === 'news' || source.type === 'market' ? 0.9 : 0.7,
                tags: [source.type, 'autonomous-intel'],
                path
            };
            KnowledgeBase.saveToDisk(item);
            ResearchAgent.addLog(`Stored Intel: ${path}`);
        }
    }
};
