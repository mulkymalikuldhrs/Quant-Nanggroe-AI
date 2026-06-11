
import { VirtualFile } from "../types";

// --- BROWSER CORE ENGINE ---
// Handles the "Motor Cortex" of web interaction: Fetching, Parsing, and Sanitizing.

const PROXIES = [
    (url: string) => `https://corsproxy.io/?${encodeURIComponent(url)}`,
    (url: string) => `https://api.allorigins.win/raw?url=${encodeURIComponent(url)}`,
    // Fallback to a simple text extractor if direct HTML fails
    (url: string) => `https://r.jina.ai/${url}` 
];

export interface PageResult {
    url: string;
    title: string;
    content: string; // Clean text for Agent
    html: string; // Raw HTML for Reader View
    markdown: string; // Markdown for Agent
    mode: 'proxy' | 'reader' | 'direct' | 'error';
    loading: boolean;
}

export const BrowserCore = {

    /**
     * Determines if a string is a URL or a Search Query
     */
    processInput: (input: string): string => {
        if (!input) return "about:blank";
        if (input.startsWith('http')) return input;
        if (input.includes('.') && !input.includes(' ')) return `https://${input}`;
        return `https://duckduckgo.com/?q=${encodeURIComponent(input)}`;
    },

    /**
     * Fetches a page using the Neural Proxy Network (Rotation of CORS Proxies)
     */
    fetchPage: async (url: string): Promise<PageResult> => {
        // 1. Check for Search Engine or Special Protocols
        if (url.includes('duckduckgo.com') || url.includes('google.com')) {
            // These allow embedding usually, or we just let them be
            return {
                url,
                title: 'Search',
                content: 'Search Engine Interface Active',
                html: '',
                markdown: 'Search Engine Interface Active',
                mode: 'direct',
                loading: false
            };
        }

        // 2. Try Fetching via Proxies
        let rawHtml = '';
        let usedProxy = '';

        for (const proxyGen of PROXIES) {
            try {
                const target = proxyGen(url);
                const res = await fetch(target);
                if (res.ok) {
                    rawHtml = await res.text();
                    usedProxy = target;
                    break;
                }
            } catch (e) {
                console.warn("Proxy Failed, trying next node...", e);
            }
        }

        if (!rawHtml) {
            return {
                url,
                title: 'Access Denied',
                content: 'Could not fetch content via Neural Proxy Network.',
                html: '<div style="padding:20px; text-align:center;"><h3>Connection Failed</h3><p>Target refused all proxy connections.</p></div>',
                markdown: 'Connection Failed',
                mode: 'error',
                loading: false
            };
        }

        // 3. Parse & Sanitize (Simulated Readability)
        const parser = new DOMParser();
        const doc = parser.parseFromString(rawHtml, 'text/html');
        
        // Remove scripts/styles for safety
        doc.querySelectorAll('script, style, iframe, svg, nav, footer, header').forEach(el => el.remove());

        const title = doc.querySelector('title')?.innerText || 'Untitled Page';
        
        // Extract Main Text (Naive Readability)
        const bodyText = doc.body.innerText.replace(/\s+/g, ' ').trim().substring(0, 5000); // Cap at 5k chars for LLM
        
        // Clean HTML for Reader View
        // Inject a base tag so relative links work
        const base = doc.createElement('base');
        base.href = url;
        doc.head.prepend(base);
        
        // Add basic styling for Reader Mode
        const style = doc.createElement('style');
        style.innerHTML = `
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; padding: 20px; max-width: 800px; margin: 0 auto; color: #333; }
            img { max-width: 100%; height: auto; border-radius: 8px; margin: 10px 0; }
            h1, h2, h3 { color: #111; margin-top: 1.5em; }
            a { color: #007AFF; }
            blockquote { border-left: 4px solid #ccc; padding-left: 1em; color: #666; }
        `;
        doc.head.appendChild(style);

        return {
            url,
            title,
            content: bodyText, // Plain text for the Agent
            html: doc.documentElement.outerHTML, // HTML for the User UI
            markdown: `## ${title}\n\n${bodyText}`, // Markdown for storage
            mode: 'reader',
            loading: false
        };
    }
};
