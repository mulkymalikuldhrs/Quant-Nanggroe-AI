import { NewsItem, NewsSentinelOutput } from "../types";
import { AuditLogger } from "./audit_logger";

export const NewsSentinel = {
    /**
     * NEWS & MACRO SENTINEL (Sensor)
     * Output must be state & score based. Time decay is mandatory.
     */
    analyze: (news: NewsItem[]): NewsSentinelOutput => {
        AuditLogger.log('SENSOR', 'NewsSentinel: Analyzing Market News', { newsCount: news?.length });
        
        if (!news || news.length === 0) {
            const output: NewsSentinelOutput = {
                eventType: 'NOISE',
                impactScore: 0.1,
                directionalUncertainty: 0.5,
                timeDecay: 0
            };
            AuditLogger.log('SENSOR', 'NewsSentinel: No News Data', output, 'WARNING');
            return output;
        }
        
        const headlines = news.map(n => n.headline.toLowerCase());
        const macroKeywords = ['fed', 'cpi', 'fomc', 'gdp', 'inflation', 'rates', 'jobs', 'payrolls', 'interest', 'boe', 'ecb'];
        const scheduledKeywords = ['report', 'calendar', 'upcoming', 'forecast', 'expected', 'release'];
        const shockKeywords = ['war', 'crash', 'collapse', 'halt', 'hack', 'crisis', 'emergency', 'black swan', 'sanction'];
        
        let rawImpact = 0.2;
        let eventType: 'MACRO' | 'SCHEDULED' | 'SHOCK' | 'NOISE' = 'NOISE';
        
        // 1. Classification & Raw Impact
        for (const h of headlines) {
            if (shockKeywords.some(k => h.includes(k))) {
                eventType = 'SHOCK';
                rawImpact = 1.0; // Max raw impact for shock
                break;
            }
            if (macroKeywords.some(k => h.includes(k))) {
                eventType = 'MACRO';
                rawImpact = Math.max(rawImpact, 0.85);
            } else if (scheduledKeywords.some(k => h.includes(k))) {
                eventType = 'SCHEDULED';
                rawImpact = Math.max(rawImpact, 0.55);
            }
        }
        
        // 2. Directional Uncertainty
        // Higher for shocks because direction is often chaotic initially
        const directionalUncertainty = eventType === 'SHOCK' ? 0.85 : eventType === 'MACRO' ? 0.45 : 0.25;
        
        // 3. Time Decay (Mandatory by Blueprint)
        // Decay formula: Impact = RawImpact * e^(-lambda * t)
        // Or simpler linear decay for simulation: 
        const latestTimestamp = Math.max(...news.map(n => n.timestamp));
        const timeDecaySeconds = Math.floor((Date.now() - latestTimestamp) / 1000);
        
        // Decay constants: SHOCK decays slower (stays relevant), NOISE decays instantly
        const decayHalflife = {
            'SHOCK': 3600 * 4,    // 4 hours
            'MACRO': 3600 * 2,    // 2 hours
            'SCHEDULED': 3600,    // 1 hour
            'NOISE': 300          // 5 minutes
        }[eventType];

        const impactScore = Number((rawImpact * Math.pow(0.5, timeDecaySeconds / decayHalflife)).toFixed(3));

        const output: NewsSentinelOutput = {
            eventType,
            impactScore,
            directionalUncertainty,
            timeDecay: timeDecaySeconds
        };

        AuditLogger.log('SENSOR', 'NewsSentinel: Analysis Complete', { 
            ...output, 
            rawImpact, 
            decayHalflife 
        });
        
        return output;
    }
};
