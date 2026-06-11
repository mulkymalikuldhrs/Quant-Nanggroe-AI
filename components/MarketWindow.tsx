
import React, { useState, useEffect, useContext } from 'react';
import { MarketService } from '../services/market';
import { MarketTicker, NewsItem, ChartPoint, CandleData } from '../types';
import RealTimeChart from './RealTimeChart';
import { IconSearch, IconGlobe, IconLink, IconShield, IconChart } from './Icons';
import { ThemeContext } from '../App';

const ASSET_LISTS = {
    crypto: ['BTC', 'ETH', 'SOL', 'XRP', 'DOGE', 'PEPE', 'WIF'],
    stocks: ['AAPL', 'NVDA', 'TSLA', 'MSFT', 'COIN', 'MSTR'],
    forex: ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'XAGUSD', 'AUDUSD'], // Gold/Silver included here
    indices: ['SPX', 'NDX', 'IHSG']
};

const MarketWindow: React.FC = () => {
    const { theme } = useContext(ThemeContext);
    const [activeTab, setActiveTab] = useState<'crypto' | 'stocks' | 'forex' | 'news'>('crypto');
    const [tickers, setTickers] = useState<MarketTicker[]>([]);
    const [news, setNews] = useState<NewsItem[]>([]);
    const [selectedAsset, setSelectedAsset] = useState<string>('BTC');
    const [chartData, setChartData] = useState<(ChartPoint | CandleData)[]>([]);
    const [loadingChart, setLoadingChart] = useState(false);
    
    const fetchTickers = async () => {
        if (activeTab === 'news') {
            const newsItems = await MarketService.getNews();
            setNews(newsItems);
            return;
        }

        const assets = activeTab === 'forex' 
            ? ASSET_LISTS.forex 
            : activeTab === 'stocks' 
            ? [...ASSET_LISTS.stocks, ...ASSET_LISTS.indices] 
            : ASSET_LISTS.crypto;

        const results = [];
        for (const sym of assets) {
            const t = await MarketService.getPrice(sym);
            if (t) results.push(t);
        }
        setTickers(results);
    };

    const fetchChart = async (symbol: string) => {
        setLoadingChart(true);
        const history = await MarketService.getMarketChart(symbol, 30); 
        setChartData(history);
        setLoadingChart(false);
    };

    useEffect(() => {
        setTickers([]); // Clear old list
        fetchTickers();
        const interval = setInterval(fetchTickers, 60000);
        return () => clearInterval(interval);
    }, [activeTab]);

    useEffect(() => {
        if (activeTab !== 'news') fetchChart(selectedAsset);
    }, [selectedAsset, activeTab]);

    const activeTicker = tickers.find(t => t.symbol === selectedAsset);

    return (
        <div className={`flex h-full w-full flex-col transition-colors duration-500 ${theme === 'dark' ? 'bg-[#09090b]' : 'bg-[#f5f5f7]'}`}>
            
            {/* Top Tabs */}
            <div className={`flex-none px-4 pt-2 border-b flex gap-6 overflow-x-auto select-none transition-colors duration-500 ${theme === 'dark' ? 'bg-[#121214] border-white/5' : 'bg-white/60 border-black/5'}`}>
                {['crypto', 'stocks', 'forex', 'news'].map(tab => (
                    <button
                        key={tab}
                        onClick={() => { 
                            setActiveTab(tab as any); 
                            if(tab === 'stocks') setSelectedAsset('AAPL'); 
                            if(tab === 'crypto') setSelectedAsset('BTC');
                            if(tab === 'forex') setSelectedAsset('EURUSD');
                        }}
                        className={`text-[10px] font-black py-3 border-b-2 uppercase tracking-[0.2em] transition-all ${activeTab === tab ? 'border-emerald-500 text-emerald-500 shadow-[0_10px_10px_-10px_rgba(16,185,129,0.5)]' : 'border-transparent text-zinc-600 hover:text-zinc-400'}`}
                    >
                        {tab === 'forex' ? 'FX_COMM' : tab.toUpperCase()}
                    </button>
                ))}
            </div>

            <div className="flex-1 flex overflow-hidden">
                
                {/* NEWS VIEW */}
                {activeTab === 'news' ? (
                    <div className={`w-full h-full overflow-y-auto p-6 space-y-4 custom-scrollbar transition-colors duration-500 ${theme === 'dark' ? 'bg-[#09090b]' : 'bg-white/40'}`}>
                        {news.length === 0 && (
                            <div className="h-full flex flex-col items-center justify-center text-zinc-500 uppercase font-black text-[10px] tracking-widest gap-4 opacity-50">
                                <div className="w-12 h-12 border border-zinc-500 rounded-full flex items-center justify-center animate-pulse">
                                    <IconGlobe className="w-6 h-6" />
                                </div>
                                CHECK_FINNHUB_UPLINK
                            </div>
                        )}
                        {news.map(item => (
                            <div key={item.id} className={`p-5 rounded-2xl border transition-all group ${theme === 'dark' ? 'bg-[#121214] border-white/5 hover:border-zinc-700' : 'bg-white border-black/5 hover:border-zinc-300 shadow-sm'}`}>
                                <div className="flex justify-between items-start mb-3">
                                    <h4 className={`text-xs font-bold leading-relaxed group-hover:text-emerald-500 transition-colors ${theme === 'dark' ? 'text-zinc-100' : 'text-zinc-800'}`}>{item.headline}</h4>
                                    <span className={`text-[9px] font-mono px-2 py-0.5 rounded border ${theme === 'dark' ? 'text-zinc-600 bg-black border-white/5' : 'text-zinc-500 bg-zinc-100 border-black/5'}`}>{new Date(item.timestamp).toLocaleTimeString()}</span>
                                </div>
                                <p className={`text-[11px] leading-relaxed line-clamp-2 mb-4 ${theme === 'dark' ? 'text-zinc-500' : 'text-zinc-600'}`}>{item.summary}</p>
                                <div className={`flex justify-between items-center pt-4 border-t ${theme === 'dark' ? 'border-white/5' : 'border-black/5'}`}>
                                    <span className="text-[9px] font-black text-indigo-500 uppercase tracking-widest">{item.source}</span>
                                    <a href={item.url} target="_blank" className={`p-2 rounded-lg transition-all ${theme === 'dark' ? 'bg-white/5 hover:bg-white/10 text-zinc-400' : 'bg-black/5 hover:bg-black/10 text-zinc-600'}`}>
                                        <IconLink className="w-3 h-3" />
                                    </a>
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    /* MARKET VIEW (Sidebar + Chart) */
                    <>
                        <div className={`w-1/3 min-w-[220px] border-r flex flex-col transition-colors duration-500 ${theme === 'dark' ? 'bg-[#09090b] border-white/5' : 'bg-white border-black/5'}`}>
                            <div className="flex-1 overflow-y-auto custom-scrollbar">
                                {tickers.map(ticker => {
                                    const verdict = ticker.consensus?.verdict || 'NEUTRAL';
                                    const score = ticker.consensus?.score || 0;
                                    let verdictColor = theme === 'dark' ? 'text-zinc-500 bg-zinc-900 border-zinc-800' : 'text-zinc-500 bg-zinc-100 border-zinc-200';
                                    if (score > 50) verdictColor = 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20';
                                    else if (score > 20) verdictColor = 'text-emerald-500 bg-emerald-500/5 border-emerald-500/10';
                                    else if (score < -50) verdictColor = 'text-red-400 bg-red-500/10 border-red-500/20';
                                    else if (score < -20) verdictColor = 'text-red-500 bg-red-500/5 border-red-500/10';

                                    return (
                                        <div 
                                            key={ticker.id}
                                            onClick={() => setSelectedAsset(ticker.symbol)}
                                            className={`px-5 py-4 cursor-pointer border-b transition-all relative ${theme === 'dark' ? 'border-white/5' : 'border-black/5'} ${selectedAsset === ticker.symbol ? (theme === 'dark' ? 'bg-zinc-900/50 border-emerald-500/30' : 'bg-emerald-500/5 border-emerald-500/20') : (theme === 'dark' ? 'hover:bg-zinc-900/30' : 'hover:bg-zinc-50')}`}
                                        >
                                            {selectedAsset === ticker.symbol && <div className="absolute left-0 top-0 w-1 h-full bg-emerald-500 shadow-[0_0_10px_emerald]"></div>}
                                            <div className="flex justify-between items-center mb-2">
                                                <span className={`font-black text-[11px] tracking-widest ${theme === 'dark' ? 'text-zinc-100' : 'text-zinc-800'}`}>{ticker.symbol}</span>
                                                <span className={`font-mono text-xs font-bold ${theme === 'dark' ? 'text-zinc-100' : 'text-zinc-900'}`}>${ticker.currentPrice.toLocaleString(undefined, { maximumSignificantDigits: 6 })}</span>
                                            </div>
                                            <div className="flex justify-between items-center">
                                                <span className={`text-[10px] font-mono ${ticker.priceChange24h >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>
                                                    {ticker.priceChange24h >= 0 ? '+' : ''}{ticker.priceChange24h.toFixed(2)}%
                                                </span>
                                                <span className={`text-[8px] px-2 py-0.5 rounded-md font-black uppercase tracking-wider border ${verdictColor}`}>
                                                    {verdict}
                                                </span>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>

                        <div className={`flex-1 flex flex-col transition-colors duration-500 ${theme === 'dark' ? 'bg-[#09090b]' : 'bg-[#f5f5f7]'}`}>
                            <div className={`px-8 py-6 border-b backdrop-blur-xl transition-colors duration-500 ${theme === 'dark' ? 'border-white/5 bg-zinc-900/20' : 'border-black/5 bg-white/40'}`}>
                                <div className="flex justify-between items-start gap-8">
                                    <div className="flex-1">
                                        <div className="flex items-center gap-3 mb-2">
                                            <h2 className={`text-2xl font-black uppercase tracking-tighter ${theme === 'dark' ? 'text-zinc-100' : 'text-zinc-900'}`}>{activeTicker?.name || selectedAsset}</h2>
                                            <span className={`px-3 py-1 rounded-lg text-[9px] font-black uppercase tracking-[0.2em] border ${theme === 'dark' ? 'bg-white/5 text-zinc-500 border-white/5' : 'bg-black/5 text-zinc-500 border-black/5'}`}>{activeTicker?.source}</span>
                                        </div>
                                        <div className="flex items-baseline gap-4">
                                            <span className={`text-3xl font-mono font-black tracking-tighter ${theme === 'dark' ? 'text-zinc-100' : 'text-zinc-900'}`}>
                                                ${activeTicker?.currentPrice.toLocaleString() || '---'}
                                            </span>
                                            <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-black ${activeTicker && activeTicker.priceChange24h >= 0 ? 'bg-emerald-500/10 text-emerald-500' : 'bg-red-500/10 text-red-500'}`}>
                                                <div className={`w-1.5 h-1.5 rounded-full ${activeTicker && activeTicker.priceChange24h >= 0 ? 'bg-emerald-500' : 'bg-red-500'} animate-pulse`}></div>
                                                {activeTicker?.priceChange24h.toFixed(2)}%
                                            </div>
                                        </div>
                                    </div>
                                    
                                    {/* CONSENSUS CARD (Institutional) */}
                                    {activeTicker?.consensus && (
                                        <div className={`rounded-2xl p-5 border shadow-2xl min-w-[240px] transition-colors duration-500 ${theme === 'dark' ? 'bg-[#121214] border-white/5' : 'bg-white border-black/5 shadow-md'}`}>
                                            <div className="flex justify-between items-center mb-4">
                                                <span className="text-[9px] font-black text-zinc-500 uppercase tracking-widest">Neural_Consensus</span>
                                                <IconShield className={`w-4 h-4 ${activeTicker.consensus.score > 0 ? 'text-emerald-500' : 'text-red-500'}`} />
                                            </div>
                                            <div className={`text-xl font-black mb-3 ${activeTicker.consensus.score > 0 ? 'text-emerald-400' : activeTicker.consensus.score < 0 ? 'text-red-400' : 'text-zinc-400'}`}>
                                                {activeTicker.consensus.verdict}
                                            </div>
                                            <div className={`w-full h-2 rounded-full overflow-hidden mb-3 ${theme === 'dark' ? 'bg-zinc-800' : 'bg-zinc-200'}`}>
                                                <div 
                                                    className={`h-full transition-all duration-1000 ${activeTicker.consensus.score > 0 ? 'bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]' : 'bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.5)]'}`} 
                                                    style={{ width: `${Math.abs(activeTicker.consensus.score)}%` }}
                                                ></div>
                                            </div>
                                            <div className="flex justify-between text-[9px] font-black font-mono">
                                                <span className="text-emerald-500">{activeTicker.consensus.bullishCount} BULL_NODES</span>
                                                <span className="text-red-500">{activeTicker.consensus.bearishCount} BEAR_NODES</span>
                                            </div>
                                        </div>
                                    )}
                                </div>

                                {/* SIGNAL TAPE */}
                                {activeTicker?.activeSignals && activeTicker.activeSignals.length > 0 && (
                                    <div className="mt-8 flex gap-3 overflow-x-auto pb-2 custom-scrollbar">
                                        {activeTicker.activeSignals.map((s, i) => (
                                            <div key={i} className={`shrink-0 flex items-center gap-3 px-4 py-3 rounded-xl border transition-all hover:scale-105 ${s.type === 'BUY' ? 'bg-emerald-500/5 border-emerald-500/20 text-emerald-500' : 'bg-red-500/5 border-red-500/20 text-red-500'}`}>
                                                <div className="flex flex-col">
                                                    <span className="text-[10px] font-black uppercase tracking-widest">{s.name}</span>
                                                    <div className="flex items-center gap-2 mt-1">
                                                        <span className="text-[8px] opacity-60 font-bold">{s.category}</span>
                                                        <div className="w-1 h-1 rounded-full bg-current opacity-30"></div>
                                                        <span className="text-[8px] font-mono">STRENGTH: {s.strength}</span>
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>

                            <div className={`flex-1 p-8 relative transition-colors duration-500 ${theme === 'dark' ? 'bg-[#09090b]' : 'bg-[#f5f5f7]'}`}>
                                {loadingChart ? (
                                    <div className="absolute inset-0 flex items-center justify-center bg-black/20 backdrop-blur-sm z-10">
                                        <div className="w-10 h-10 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
                                    </div>
                                ) : null}
                                
                                <div className={`w-full h-full rounded-3xl border overflow-hidden p-1 shadow-2xl transition-colors duration-500 ${theme === 'dark' ? 'bg-black/40 border-white/5' : 'bg-white border-black/5'}`}>
                                    {chartData.length > 0 ? (
                                        <RealTimeChart data={chartData} />
                                    ) : (
                                        <div className="w-full h-full flex flex-col items-center justify-center text-center gap-4">
                                            <IconChart className="w-12 h-12 text-zinc-400 opacity-20" />
                                            <div className="text-[10px] text-zinc-400 font-black uppercase tracking-[0.3em] opacity-40">Neural_Data_Streaming_Required</div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
};

export default MarketWindow;
