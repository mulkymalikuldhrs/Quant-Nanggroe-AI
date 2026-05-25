
import { MarketTicker, NewsItem, ChartPoint, CandleData, SystemConfiguration, MarketState, MarketRegime, QuantScannerOutput, SMCOutput } from "../types";
import { BrowserFS } from "./file_system";
import { MathEngine } from "./math_engine";
import { StrategyEngine } from "./strategy_engine";
import { AutoSwitch, AutoSwitchProvider } from "./autoswitch";
import { AuditLogger } from "./audit_logger";

// --- API ENDPOINTS ---
const AV_BASE_URL = "https://www.alphavantage.co/query";
const FH_BASE_URL = "https://finnhub.io/api/v1";
const POLY_BASE_URL = "https://api.polygon.io";
const DEX_BASE_URL = "https://api.dexscreener.com/latest/dex";
const FRANKFURTER_BASE_URL = "https://api.frankfurter.app";
const COINCAP_BASE_URL = "https://api.coincap.io/v2";

// Caching
const CACHE_DURATION = 15000;
const priceCache: Record<string, { data: any; timestamp: number }> = {};
let newsCache: { data: NewsItem[], timestamp: number } | null = null;

const getKeys = () => {
    const config = BrowserFS.loadSystemConfig();
    return config?.apiKeys || { alphaVantage: '', finnhub: '', fred: '', polygon: '' };
};

// --- CORS PROXY ROTATOR ---
const CORS_PROXIES = [
    "https://api.allorigins.win/get?url=",
    "https://corsproxy.io/?",
    "https://api.codetabs.com/v1/proxy?quest="
];

const fetchWithProxy = async (url: string) => {
    for (const proxy of CORS_PROXIES) {
        try {
            const proxyUrl = `${proxy}${encodeURIComponent(url)}`;
            const res = await fetch(proxyUrl);
            if (!res.ok) continue;
            const data = await res.json();
            
            // AllOrigins wraps content in .contents
            if (proxy.includes('allorigins')) return JSON.parse(data.contents);
            return data;
        } catch (e) {
            continue;
        }
    }
    throw new Error("All CORS proxies failed");
};

export const MarketService = {
    
    resolveId: (ticker: string): { type: 'crypto' | 'stock' | 'forex' | 'dex' | 'commodity' | 'index', id: string, name?: string } => {
        const clean = ticker.toUpperCase().replace('/', '').trim();
        
        if (['GOLD', 'XAU', 'XAUUSD'].includes(clean)) return { type: 'commodity', id: 'PAXG', name: 'Gold' }; 
        if (['OIL', 'WTI', 'CL=F'].includes(clean)) return { type: 'commodity', id: 'OIL', name: 'Crude Oil' };
        if (['SILVER', 'XAG'].includes(clean)) return { type: 'commodity', id: 'KAG', name: 'Silver' };

        if (['SPX', 'SP500', '^GSPC'].includes(clean)) return { type: 'index', id: 'SPY', name: 'S&P 500' }; 
        if (['NDX', 'NASDAQ'].includes(clean)) return { type: 'index', id: 'QQQ', name: 'Nasdaq 100' };
        if (['IHSG', '^JKSE', 'IDX'].includes(clean)) return { type: 'index', id: 'EIDO', name: 'MSCI Indonesia' }; 

        const fxPairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'USDCHF', 'NZDUSD'];
        if (fxPairs.includes(clean) || (clean.length === 6 && (clean.startsWith('USD') || clean.endsWith('USD')))) {
            return { type: 'forex', id: clean };
        }

        if (clean.startsWith('0X') || clean.length > 20) return { type: 'dex', id: clean };

        const CRYPTO_MAP: Record<string, string> = {
            'BTC': 'bitcoin', 'ETH': 'ethereum', 'SOL': 'solana', 'XRP': 'ripple',
            'DOGE': 'dogecoin', 'ADA': 'cardano', 'AVAX': 'avalanche-2', 'DOT': 'polkadot',
            'MATIC': 'matic-network', 'LINK': 'chainlink', 'USDT': 'tether', 'BNB': 'binancecoin',
            'PEPE': 'pepe', 'SHIB': 'shiba-inu', 'WIF': 'dogwifhat', 'BTCUSD': 'bitcoin', 'ETHUSD': 'ethereum'
        };
        if (CRYPTO_MAP[clean]) return { type: 'crypto', id: CRYPTO_MAP[clean] };

        return { type: 'stock', id: clean };
    },

    // --- HELPERS ---
    createMetadata: (source: string, domainType: string, latency: number = 100): DataMetadata => ({
        source,
        trustScore: source === 'Binance' || source === 'AlphaVantage' ? 0.9 : 0.7,
        latencyEstimate: latency,
        updateFrequency: 'Real-time',
        domainType
    }),

    getPrice: async (ticker: string): Promise<MarketTicker | null> => {
        const info = MarketService.resolveId(ticker);
        const { type, id } = info;
        const cacheKey = `${type}_${id}`;
        
        AuditLogger.log('MARKET', 'Fetching Price', { ticker, type, id });

        if (priceCache[cacheKey] && Date.now() - priceCache[cacheKey].timestamp < CACHE_DURATION) {
            AuditLogger.log('MARKET', 'Cache Hit', { ticker });
            return priceCache[cacheKey].data;
        }

        let result: MarketTicker | null = null;
        const config = BrowserFS.loadSystemConfig();
        const keys = config?.apiKeys || { alphaVantage: '', finnhub: '', fred: '', polygon: '' };
        const enableAutoSwitch = config?.enableAutoSwitch ?? true;

        try {
            switch (type) {
                case 'crypto': {
                    const cryptoProviders: AutoSwitchProvider<string, MarketTicker | null>[] = [
                        { name: 'Binance', id: 'binance', execute: (id) => MarketService.getBinancePrice(id) },
                        { name: 'CoinCap', id: 'coincap', execute: (id) => MarketService.getCoinCapPrice(id) }
                    ];
                    const switcher = new AutoSwitch(cryptoProviders, { enableAutoSwitch });
                    const res = await switcher.execute(id);
                    result = res.data;
                    break;
                }
                case 'dex':
                    result = await MarketService.getDexPrice(id);
                    break;
                case 'forex': {
                    const forexProviders: AutoSwitchProvider<string, MarketTicker | null>[] = [];
                    if (keys.alphaVantage) {
                        forexProviders.push({ name: 'AlphaVantage', id: 'av', execute: (id) => MarketService.getForexAlphaVantage(id, keys.alphaVantage) });
                    }
                    forexProviders.push({ name: 'Frankfurter', id: 'frankfurter', execute: (id) => MarketService.getForexFrankfurter(id) });
                    const switcher = new AutoSwitch(forexProviders, { enableAutoSwitch });
                    const res = await switcher.execute(id);
                    result = res.data;
                    break;
                }
                case 'commodity':
                case 'index':
                case 'stock': {
                    const stockProviders: AutoSwitchProvider<string, MarketTicker | null>[] = [];
                    if (keys.polygon) {
                        stockProviders.push({ name: 'Polygon', id: 'polygon', execute: (id) => MarketService.getPolygonPrice(id, keys.polygon) });
                    }
                    if (keys.alphaVantage) {
                        stockProviders.push({ name: 'AlphaVantage', id: 'av', execute: (id) => MarketService.getStockPrice(id, keys.alphaVantage) });
                    }
                    if (keys.finnhub) {
                        stockProviders.push({ name: 'Finnhub', id: 'finnhub', execute: (id) => MarketService.getFinnhubPrice(id, keys.finnhub) });
                    }
                    
                    if (stockProviders.length > 0) {
                        const switcher = new AutoSwitch(stockProviders, { enableAutoSwitch });
                        const res = await switcher.execute(id);
                        result = res.data;
                    }

                    if (!result && (id === 'PAXG' || id === 'KAG')) {
                        const cryptoId = id === 'PAXG' ? 'pax-gold' : 'kinesis-silver';
                        result = await MarketService.getBinancePrice(cryptoId);
                        if (result) {
                            result.name = info.name || result.name;
                        }
                    }
                    break;
                }
            }
        } catch (e) {
            console.error(`Market Fetch Error for ${ticker}:`, e);
        }

        if (result) {
            try {
                const history = await MarketService.getMarketChart(ticker, 60); 
                if (history && history.length > 50) {
                     const candles: CandleData[] = history.map(h => {
                         if ('open' in h) return h as CandleData;
                         return { 
                             timestamp: h.timestamp, open: (h as ChartPoint).price, high: (h as ChartPoint).price, low: (h as ChartPoint).price, close: (h as ChartPoint).price, volume: 100 
                         };
                     });
                     const technicals = MathEngine.analyzeSequence(candles);
                     result.technicals = technicals;
                }
            } catch (e) {
                console.warn("Strategy analysis failed for", ticker, e);
            }
            priceCache[cacheKey] = { data: result, timestamp: Date.now() };
        }
        return result;
    },

    getDexPrice: async (query: string): Promise<MarketTicker | null> => {
        const url = query.startsWith('0x') ? `${DEX_BASE_URL}/tokens/${query}` : `${DEX_BASE_URL}/search?q=${query}`;
        const data = await fetchWithProxy(url);
        if (data.pairs && data.pairs.length > 0) {
            const pair = data.pairs[0];
            return {
                id: pair.baseToken.address, symbol: pair.baseToken.symbol,
                currentPrice: parseFloat(pair.priceUsd),
                priceChange24h: pair.priceChange.h24,
                volume: pair.volume.h24,
                metadata: MarketService.createMetadata('DexScreener', 'dex')
            };
        }
        return null;
    },

    getForexFrankfurter: async (pair: string): Promise<MarketTicker | null> => {
        const from = pair.substring(0, 3);
        const to = pair.substring(3, 6);
        const data = await fetchWithProxy(`${FRANKFURTER_BASE_URL}/latest?from=${from}&to=${to}`);
        if (data.rates && data.rates[to]) {
             return {
                id: pair, symbol: pair, 
                currentPrice: data.rates[to],
                priceChange24h: 0,
                metadata: MarketService.createMetadata('Frankfurter (ECB)', 'forex')
             };
        }
        return null;
    },

    getForexAlphaVantage: async (pair: string, apiKey: string): Promise<MarketTicker | null> => {
        const from = pair.substring(0, 3);
        const to = pair.substring(3, 6);
        const data = await fetchWithProxy(`${AV_BASE_URL}?function=CURRENCY_EXCHANGE_RATE&from_currency=${from}&to_currency=${to}&apikey=${apiKey}`);
        const rate = data['Realtime Currency Exchange Rate'];
        if (rate) {
            return {
                id: pair, symbol: pair,
                currentPrice: parseFloat(rate['5. Exchange Rate']),
                priceChange24h: 0,
                metadata: MarketService.createMetadata('AlphaVantage', 'forex')
            };
        }
        return null;
    },

    getBinancePrice: async (id: string): Promise<MarketTicker | null> => {
        const BINANCE_MAP: Record<string, string> = {
            'bitcoin': 'BTCUSDT', 'ethereum': 'ETHUSDT', 'solana': 'SOLUSDT', 'ripple': 'XRPUSDT',
            'dogecoin': 'DOGEUSDT', 'cardano': 'ADAUSDT', 'avalanche-2': 'AVAXUSDT', 'polkadot': 'DOTUSDT',
            'matic-network': 'MATICUSDT', 'chainlink': 'LINKUSDT', 'tether': 'USDTUSDC', 'binancecoin': 'BNBUSDT',
            'pepe': 'PEPEUSDT', 'shiba-inu': 'SHIBUSDT', 'dogwifhat': 'WIFUSDT'
        };
        const symbol = BINANCE_MAP[id];
        if (!symbol) return null;

        try {
            const data = await fetchWithProxy(`https://api.binance.com/api/v3/ticker/24hr?symbol=${symbol}`);
            if (data && data.lastPrice) {
                return {
                    id: id, symbol: symbol.replace('USDT', ''), 
                    currentPrice: parseFloat(data.lastPrice),
                    priceChange24h: parseFloat(data.priceChangePercent),
                    volume: parseFloat(data.volume),
                    metadata: MarketService.createMetadata('Binance', 'crypto')
                };
            }
        } catch (e) { }
        return null;
    },

    getCoinCapPrice: async (id: string): Promise<MarketTicker | null> => {
        const json = await fetchWithProxy(`${COINCAP_BASE_URL}/assets/${id}`);
        const data = json.data;
        if (data) {
            return {
                id: data.id, symbol: data.symbol, name: data.name, 
                currentPrice: parseFloat(data.priceUsd),
                priceChange24h: parseFloat(data.changePercent24Hr),
                metadata: MarketService.createMetadata('CoinCap', 'crypto')
            };
        }
        return null;
    },

    getStockPrice: async (ticker: string, apiKey: string): Promise<MarketTicker | null> => {
        const data = await fetchWithProxy(`${AV_BASE_URL}?function=GLOBAL_QUOTE&symbol=${ticker}&apikey=${apiKey}`);
        const quote = data['Global Quote'];
        if (quote && quote['05. price']) {
            return {
                id: ticker, symbol: ticker, name: ticker, 
                currentPrice: parseFloat(quote['05. price']),
                priceChange24h: parseFloat(quote['10. change percent'].replace('%', '')),
                metadata: MarketService.createMetadata('AlphaVantage', 'stock')
            };
        }
        return null;
    },

    getFinnhubPrice: async (ticker: string, apiKey: string): Promise<MarketTicker | null> => {
        const data = await fetchWithProxy(`${FH_BASE_URL}/quote?symbol=${ticker}&token=${apiKey}`);
        if (data.c) {
            return {
                id: ticker, symbol: ticker, name: ticker, 
                currentPrice: data.c,
                priceChange24h: data.dp,
                metadata: MarketService.createMetadata('Finnhub', 'stock')
            };
        }
        return null;
    },

    getPolygonPrice: async (ticker: string, apiKey: string): Promise<MarketTicker | null> => {
        const data = await fetchWithProxy(`${POLY_BASE_URL}/v2/aggs/ticker/${ticker}/prev?adjusted=true&apiKey=${apiKey}`);
        if (data.results && data.results.length > 0) {
            const r = data.results[0];
            return {
                id: ticker, symbol: ticker, name: ticker, 
                currentPrice: r.c,
                priceChange24h: ((r.c - r.o) / r.o) * 100,
                metadata: MarketService.createMetadata('Polygon', 'stock')
            };
        }
        return null;
    },

    getMarketChart: async (ticker: string, days: number = 1): Promise<(ChartPoint | CandleData)[]> => {
        const info = MarketService.resolveId(ticker);
        const { type, id } = info;
        const keys = getKeys();

        if (type === 'crypto') {
            const BINANCE_MAP: Record<string, string> = {
                'bitcoin': 'BTCUSDT', 'ethereum': 'ETHUSDT', 'solana': 'SOLUSDT', 'ripple': 'XRPUSDT',
                'dogecoin': 'DOGEUSDT', 'cardano': 'ADAUSDT', 'avalanche-2': 'AVAXUSDT', 'polkadot': 'DOTUSDT',
                'matic-network': 'MATICUSDT', 'chainlink': 'LINKUSDT', 'tether': 'USDTUSDC', 'binancecoin': 'BNBUSDT',
                'pepe': 'PEPEUSDT', 'shiba-inu': 'SHIBUSDT', 'dogwifhat': 'WIFUSDT'
            };
            const symbol = BINANCE_MAP[id];
            if (symbol) {
                try {
                    const interval = days <= 1 ? '15m' : days <= 7 ? '1h' : '4h';
                    const apiUrl = `https://api.binance.com/api/v3/klines?symbol=${symbol}&interval=${interval}&limit=100`;
                    const data = await fetchWithProxy(apiUrl);
                    
                    if (Array.isArray(data)) {
                        return data.map((d: any) => ({
                            timestamp: d[0], open: parseFloat(d[1]), high: parseFloat(d[2]),
                            low: parseFloat(d[3]), close: parseFloat(d[4]), volume: parseFloat(d[5])
                        }));
                    }
                } catch (e) {}
            }
        }

        if (keys.polygon && type !== 'dex' && type !== 'forex') {
            try {
                const toDate = new Date();
                const fromDate = new Date();
                fromDate.setDate(toDate.getDate() - days);
                const toStr = toDate.toISOString().split('T')[0];
                const fromStr = fromDate.toISOString().split('T')[0];
                const url = `${POLY_BASE_URL}/v2/aggs/ticker/${id}/range/1/hour/${fromStr}/${toStr}?adjusted=true&sort=asc&limit=500&apiKey=${keys.polygon}`;
                const data = await fetchWithProxy(url);
                if (data.results) {
                    return data.results.map((r: any) => ({ timestamp: r.t, open: r.o, high: r.h, low: r.l, close: r.c, volume: r.v }));
                }
            } catch (e) {}
        }

        // Fallback: return empty dataset when no API is configured
        // Real data requires Binance, Polygon, or AlphaVantage API keys
        console.warn(`No market data API available for ${ticker}. Configure API keys for real data.`);
        return [];
    },

    getNews: async (): Promise<NewsItem[]> => {
        if (newsCache && Date.now() - newsCache.timestamp < 300000) return newsCache.data; 
        const keys = getKeys();
        if (!keys.finnhub) return [];
        try {
            const data = await fetchWithProxy(`${FH_BASE_URL}/news?category=general&token=${keys.finnhub}`);
            const items = data.slice(0, 10).map((item: any) => ({
                id: item.id, headline: item.headline, source: item.source, url: item.url,
                summary: item.summary, timestamp: item.datetime * 1000
            }));
            newsCache = { data: items, timestamp: Date.now() };
            return items;
        } catch (e) { return []; }
    },

    // --- BLUEPRINT FINAL: MARKET STATE ENGINE ---
    getMarketState: (candles: CandleData[]): MarketState => {
        if (candles.length < 50) return { regime: 'NO_TRADE', volatility: 'NORMAL', liquidity: 'NORMAL', timestamp: Date.now() };
        
        const closes = candles.map(c => c.close);
        const lastPrice = closes[closes.length - 1];
        
        // Technical Inputs
        const sma50 = MathEngine.calculateSMA(closes, 50);
        const sma200 = MathEngine.calculateSMA(closes, 200);
        const rsi = MathEngine.calculateRSI(closes);
        const atr = MathEngine.calculateATR(candles);
        const avgPrice = closes.reduce((a, b) => a + b, 0) / closes.length;
        
        // 1. Regime Detection
        let regime: MarketRegime = 'RANGE';
        
        const adx = MathEngine.calculateADX(candles);
        const isTrending = adx > 25;
        
        if (isTrending) {
            regime = 'TRENDING';
        } else if (rsi > 75 || rsi < 25) {
            regime = 'MEAN_REVERT';
        }
        
        // Risk-Off / Panic detection (Fast drop)
        const priceChange5 = (lastPrice - closes[closes.length - 5]) / closes[closes.length - 5];
        if (priceChange5 < -0.05) regime = 'PANIC';
        else if (priceChange5 < -0.02) regime = 'RISK_OFF';
        
        // 2. Volatility State
        let volatility: 'LOW' | 'NORMAL' | 'HIGH' = 'NORMAL';
        const atrPercent = (atr / lastPrice) * 100;
        if (atrPercent > 2) volatility = 'HIGH';
        else if (atrPercent < 0.5) volatility = 'LOW';
        
        // 3. Liquidity State (Simplified via volume)
        let liquidity: 'THIN' | 'NORMAL' | 'DEEP' = 'NORMAL';
        const avgVol = candles.reduce((a, b) => a + (b.volume || 0), 0) / candles.length;
        const lastVol = candles[candles.length - 1].volume || 0;
        if (lastVol < avgVol * 0.5) liquidity = 'THIN';
        else if (lastVol > avgVol * 2) liquidity = 'DEEP';
        
        return {
            regime,
            volatility,
            liquidity,
            timestamp: Date.now()
        };
    },

    // --- BLUEPRINT FINAL: QUANT-SCANNER (TECHNICAL) ---
    getQuantScannerOutput: (candles: CandleData[]): QuantScannerOutput => {
        const closes = candles.map(c => c.close);
        const adx = MathEngine.calculateADX(candles);
        const sma50 = MathEngine.calculateSMA(closes, 50);
        const sma200 = MathEngine.calculateSMA(closes, 200);
        
        const trendStrength = Math.min(adx / 50, 1.0);
        let structureState: 'BULL' | 'BEAR' | 'NEUTRAL' = 'NEUTRAL';
        
        if (closes[closes.length - 1] > sma50 && sma50 > sma200) structureState = 'BULL';
        else if (closes[closes.length - 1] < sma50 && sma50 < sma200) structureState = 'BEAR';
        
        const bb = MathEngine.calculateBollingerBands(closes);
        const volatilityExpansion = (bb.upper - bb.lower) > (MathEngine.calculateSMA(closes, 20) * 0.05);

        return {
            trendStrength,
            structureState,
            volatilityExpansion
        };
    },

    // --- BLUEPRINT FINAL: SMC / PRICE ACTION AGENT ---
    getSMCOutput: (candles: CandleData[]): SMCOutput => {
        if (candles.length < 20) return { liquiditySweep: false, displacementStrength: 0, poiValidity: 0 };
        
        const lastCandle = candles[candles.length - 1];
        const prevCandles = candles.slice(-20, -1);
        
        const highestHigh = Math.max(...prevCandles.map(c => c.high));
        const lowestLow = Math.min(...prevCandles.map(c => c.low));
        
        // Liquidity Sweep: Price breaks high/low then reverses
        const liquiditySweep = (lastCandle.high > highestHigh && lastCandle.close < highestHigh) || 
                               (lastCandle.low < lowestLow && lastCandle.close > lowestLow);
                               
        // Displacement: Strong candle
        const bodySize = Math.abs(lastCandle.close - lastCandle.open);
        const totalSize = lastCandle.high - lastCandle.low;
        const displacementStrength = totalSize === 0 ? 0 : bodySize / totalSize;
        
        // POI Validity: Simplified POI near extremes
        const poiValidity = (lastCandle.close > highestHigh * 0.98 || lastCandle.close < lowestLow * 1.02) ? 0.8 : 0.2;

        return {
            liquiditySweep,
            displacementStrength,
            poiValidity
        };
    },

    // --- BLUEPRINT FINAL: NEWS & MACRO SENTINEL ---
    getNewsSentinelOutput: async (news: NewsItem[]): Promise<NewsSentinelOutput> => {
        if (news.length === 0) return { eventType: 'NOISE', impactScore: 0.1, directionalUncertainty: 0.5, timeDecay: 0 };
        
        // Simplified sentiment analysis for impact/uncertainty
        const headlines = news.map(n => n.headline.toLowerCase());
        const macroKeywords = ['fed', 'cpi', 'fomc', 'gdp', 'inflation', 'rates', 'jobs', 'payrolls'];
        const shockKeywords = ['war', 'crash', 'collapse', 'halt', 'hack', 'crisis'];
        
        let impactScore = 0.2;
        let eventType: 'MACRO' | 'NOISE' | 'SHOCK' = 'NOISE';
        
        for (const h of headlines) {
            if (shockKeywords.some(k => h.includes(k))) {
                eventType = 'SHOCK';
                impactScore = 0.9;
                break;
            }
            if (macroKeywords.some(k => h.includes(k))) {
                eventType = 'MACRO';
                impactScore = Math.max(impactScore, 0.7);
            }
        }
        
        const directionalUncertainty = eventType === 'SHOCK' ? 0.8 : eventType === 'MACRO' ? 0.4 : 0.2;
        const timeDecay = Math.floor((Date.now() - news[0].timestamp) / 1000);

        return {
            eventType,
            impactScore,
            directionalUncertainty,
            timeDecay
        };
    },

    // --- BLUEPRINT FINAL: FLOW / COT / WHALE AGENT ---
    getFlowWhaleOutput: (): FlowWhaleOutput => {
        // Flow/whale data requires paid API integration (Coinglass, WhaleAlert, etc.)
        // Returns neutral state when not configured
        return {
            positioningBias: 'NEUTRAL',
            flowImbalance: 0
        };
    }
};
