
import React, { useState, useEffect, useRef } from 'react';
import { BrowserCore, PageResult } from '../services/browser_core';
import { IconGlobe, IconLink, IconStar, IconRefresh, IconPlus, IconX, IconBook, IconSearch, IconShield } from './Icons';

interface Props {
    url?: string;
    onNavigate: (url: string) => void;
}

interface Tab extends PageResult {
    id: string;
}

const BOOKMARKS = [
    { name: "DuckDuckGo", url: "https://duckduckgo.com" },
    { name: "TradingView", url: "https://www.tradingview.com/chart/" },
    { name: "Quant Notebook", url: "https://notebooklm.google.com/notebook/743daa1f-6476-4390-914e-0044cdaf10a5" },
    { name: "MT5 Web", url: "https://trade.mql5.com/trade" },
    { name: "ForexFactory", url: "https://www.forexfactory.com/calendar" },
    { name: "CoinGecko", url: "https://www.coingecko.com" },
    { name: "TechCrunch", url: "https://techcrunch.com" },
    { name: "Bloomberg", url: "https://www.bloomberg.com" } 
];

const BrowserWindow: React.FC<Props> = ({ url, onNavigate }) => {
    const [tabs, setTabs] = useState<Tab[]>([
        { id: '1', url: 'https://duckduckgo.com', title: 'New Tab', content: '', html: '', markdown: '', mode: 'direct', loading: false }
    ]);
    const [activeTabId, setActiveTabId] = useState<string>('1');
    const [inputUrl, setInputUrl] = useState('');
    const [viewMode, setViewMode] = useState<'web' | 'reader'>('web');

    // Sync external navigation (Agent)
    useEffect(() => {
        if (url && url !== getActiveTab().url) {
            navigate(url, activeTabId);
        }
    }, [url]);

    // Update address bar
    useEffect(() => {
        const activeTab = getActiveTab();
        if (activeTab) {
            setInputUrl(activeTab.url);
            // Auto-switch based on content type
            if (activeTab.mode === 'reader') setViewMode('reader');
            if (activeTab.mode === 'direct') setViewMode('web');
        }
    }, [activeTabId, tabs]);

    const getActiveTab = () => tabs.find(t => t.id === activeTabId) || tabs[0];

    const updateTab = (id: string, updates: Partial<Tab>) => {
        setTabs(prev => prev.map(t => t.id === id ? { ...t, ...updates } : t));
    };

    const navigate = async (input: string, tabId: string) => {
        const finalUrl = BrowserCore.processInput(input);
        
        // Optimistic Update
        updateTab(tabId, { url: finalUrl, loading: true, title: 'Loading...', mode: 'direct' });
        if (tabId === activeTabId) setInputUrl(finalUrl);
        onNavigate(finalUrl); // Inform Parent/Agent

        // Determine Fetch Strategy
        // Known Embeddable Sites
        if (
            finalUrl.includes('duckduckgo') || 
            finalUrl.includes('google.com/search') || 
            finalUrl.includes('mql5.com') ||
            finalUrl.includes('tradingview.com') ||
            finalUrl.includes('dexscreener.com')
        ) {
            // Standard Iframe for Search Engines & Tools
            setTimeout(() => {
                updateTab(tabId, { loading: false, title: 'External App', mode: 'direct' });
            }, 1000);
        } else {
            // Use Neural Proxy / BrowserCore for Content Reading
            try {
                const result = await BrowserCore.fetchPage(finalUrl);
                updateTab(tabId, { 
                    ...result, 
                    id: tabId 
                });
            } catch (e) {
                updateTab(tabId, { loading: false, title: 'Error', mode: 'error' });
            }
        }
    };

    const createTab = () => {
        const newId = Date.now().toString();
        const newTab: Tab = { id: newId, url: 'https://duckduckgo.com', title: 'New Tab', content: '', html: '', markdown: '', mode: 'direct', loading: false };
        setTabs([...tabs, newTab]);
        setActiveTabId(newId);
    };

    const closeTab = (id: string, e: React.MouseEvent) => {
        e.stopPropagation();
        if (tabs.length === 1) return;
        const newTabs = tabs.filter(t => t.id !== id);
        setTabs(newTabs);
        if (activeTabId === id) setActiveTabId(newTabs[newTabs.length - 1].id);
    };

    const activeTab = getActiveTab();

    return (
        <div className="h-full w-full flex flex-col bg-[#e0e0e0]">
            
            {/* 1. TAB BAR */}
            <div className="flex-none h-9 bg-[#dcdcdc] border-b border-gray-300 flex items-end px-2 gap-1 overflow-x-auto custom-scrollbar select-none pt-1">
                {tabs.map(tab => (
                    <div 
                        key={tab.id}
                        onClick={() => setActiveTabId(tab.id)}
                        className={`group relative flex items-center gap-2 px-3 py-1.5 min-w-[120px] max-w-[200px] rounded-t-lg text-[11px] cursor-pointer transition-all border-t border-x ${
                            activeTabId === tab.id 
                            ? 'bg-white border-gray-300 text-gray-800 shadow-sm z-10' 
                            : 'bg-[#cfcfcf] border-transparent text-gray-600 hover:bg-[#d4d4d4]'
                        }`}
                    >
                        {tab.loading ? (
                            <div className="w-3 h-3 rounded-full border-2 border-blue-500 border-t-transparent animate-spin"></div>
                        ) : tab.mode === 'reader' ? (
                            <IconBook className="w-3 h-3 text-purple-500" />
                        ) : (
                            <IconGlobe className={`w-3 h-3 ${activeTabId === tab.id ? 'text-blue-500' : 'text-gray-500'}`} />
                        )}
                        <span className="truncate flex-1 font-medium">{tab.title}</span>
                        <button 
                            onClick={(e) => closeTab(tab.id, e)}
                            className="opacity-0 group-hover:opacity-100 hover:bg-red-100 hover:text-red-500 rounded p-0.5 transition-all"
                        >
                            <IconX className="w-3 h-3" />
                        </button>
                    </div>
                ))}
                <button onClick={createTab} className="p-1.5 hover:bg-gray-200 rounded text-gray-500 transition-colors mb-1">
                    <IconPlus className="w-4 h-4" />
                </button>
            </div>

            {/* 2. NAVIGATION & OMNIBOX */}
            <div className="flex-none h-12 bg-white border-b border-gray-200 flex items-center px-4 gap-3 shadow-sm z-20">
                <div className="flex gap-1">
                    <button onClick={() => navigate(activeTab.url, activeTab.id)} className="p-1.5 rounded-full hover:bg-gray-100 text-gray-600 transition-colors">
                        <IconRefresh className={`w-3.5 h-3.5 ${activeTab.loading ? 'animate-spin' : ''}`} />
                    </button>
                </div>

                <form 
                    onSubmit={(e) => { e.preventDefault(); navigate(inputUrl, activeTabId); }}
                    className="flex-1 flex items-center bg-gray-100 border border-transparent hover:border-gray-300 focus-within:bg-white focus-within:border-blue-400 focus-within:ring-4 focus-within:ring-blue-100 rounded-md px-3 py-1.5 transition-all"
                >
                    <div className="mr-2 flex items-center">
                        {activeTab.mode === 'reader' ? (
                            <div className="bg-purple-100 text-purple-600 px-1.5 py-0.5 rounded text-[9px] font-bold uppercase flex items-center gap-1">
                                <IconBook className="w-3 h-3" /> Reader
                            </div>
                        ) : (
                            <IconSearch className="w-3.5 h-3.5 text-gray-400" />
                        )}
                    </div>
                    <input 
                        type="text" 
                        value={inputUrl}
                        onChange={(e) => setInputUrl(e.target.value)}
                        className="flex-1 bg-transparent text-xs text-gray-800 focus:outline-none placeholder-gray-400 font-medium"
                        placeholder="Search web or enter URL..."
                    />
                </form>

                {/* View Toggles */}
                <div className="flex bg-gray-100 p-0.5 rounded-lg border border-gray-200">
                    <button 
                        onClick={() => setViewMode('web')}
                        className={`px-3 py-1 rounded-md text-[10px] font-bold transition-all ${viewMode === 'web' ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
                    >
                        Web
                    </button>
                    <button 
                        onClick={() => setViewMode('reader')}
                        className={`px-3 py-1 rounded-md text-[10px] font-bold transition-all flex items-center gap-1 ${viewMode === 'reader' ? 'bg-white text-purple-600 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
                    >
                        <IconBook className="w-3 h-3" /> Text
                    </button>
                </div>
            </div>

            {/* 3. BOOKMARKS */}
            <div className="flex-none h-7 bg-[#f8f8f8] border-b border-gray-200 flex items-center px-4 gap-4 overflow-x-auto">
                {BOOKMARKS.map(bm => (
                    <button 
                        key={bm.name} 
                        onClick={() => navigate(bm.url, activeTabId)}
                        className="flex items-center gap-1.5 text-[10px] font-medium text-gray-600 hover:text-blue-600 hover:bg-gray-200 px-2 py-0.5 rounded transition-colors whitespace-nowrap"
                    >
                        <IconStar className="w-3 h-3 text-yellow-500" />
                        {bm.name}
                    </button>
                ))}
            </div>

            {/* 4. CONTENT RENDERER */}
            <div className="flex-1 relative bg-white overflow-hidden">
                {activeTab.loading && (
                    <div className="absolute top-0 left-0 w-full h-0.5 bg-gray-100 overflow-hidden z-20">
                        <div className="h-full bg-blue-500 animate-progress origin-left"></div>
                    </div>
                )}

                {/* ERROR STATE */}
                {activeTab.mode === 'error' && (
                    <div className="w-full h-full flex flex-col items-center justify-center bg-gray-50 p-8 text-center">
                        <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mb-4">
                            <IconShield className="w-8 h-8 text-red-500" />
                        </div>
                        <h3 className="text-lg font-bold text-gray-800">Connection Terminated</h3>
                        <p className="text-xs text-gray-500 max-w-sm mt-2">
                            The Neural Proxy was unable to establish a secure link to <strong>{activeTab.url}</strong>.
                        </p>
                        <button onClick={() => navigate(activeTab.url, activeTabId)} className="mt-4 px-4 py-2 bg-white border border-gray-300 rounded-lg text-xs font-bold hover:bg-gray-50">Retry Connection</button>
                    </div>
                )}

                {/* READER MODE (Safe HTML) */}
                {(viewMode === 'reader' || activeTab.mode === 'reader') && activeTab.mode !== 'error' && (
                    <div className="w-full h-full overflow-y-auto bg-[#f9f9f9]">
                        <div className="max-w-3xl mx-auto bg-white min-h-full shadow-sm border-x border-gray-100 p-8 md:p-12">
                            <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2 font-serif">{activeTab.title}</h1>
                            <a href={activeTab.url} target="_blank" rel="noreferrer" className="text-xs text-blue-600 hover:underline mb-8 block">{activeTab.url}</a>
                            <div className="prose prose-sm md:prose-base max-w-none text-gray-800 font-serif leading-relaxed">
                                {activeTab.html ? (
                                    <iframe 
                                        srcDoc={activeTab.html} 
                                        className="w-full min-h-[80vh] border-none" 
                                        sandbox="allow-same-origin"
                                    />
                                ) : (
                                    <div className="whitespace-pre-wrap">{activeTab.content}</div>
                                )}
                            </div>
                        </div>
                    </div>
                )}

                {/* DIRECT/WEB VIEW */}
                {viewMode === 'web' && activeTab.mode === 'direct' && (
                    <iframe 
                        src={activeTab.url} 
                        className="w-full h-full border-none bg-white"
                        sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
                        title="Browser View"
                    />
                )}
            </div>
            
            {/* 5. FOOTER */}
            <div className="flex-none h-6 bg-[#f0f0f0] border-t border-gray-200 flex items-center px-4 justify-between text-[9px] text-gray-500">
                <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${activeTab.mode === 'reader' ? 'bg-purple-500' : 'bg-green-500'}`}></span>
                    <span>{activeTab.mode === 'reader' ? 'Neural Reader Active' : 'Direct Connection'}</span>
                </div>
                <div>{activeTab.content.length > 0 ? `${activeTab.content.length} chars parsed` : 'Waiting for content...'}</div>
            </div>
        </div>
    );
};

export default BrowserWindow;
