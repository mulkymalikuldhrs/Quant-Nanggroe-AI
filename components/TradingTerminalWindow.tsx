
import React, { useEffect, useRef, useState } from 'react';
import { IconChart, IconTerminal, IconGlobe } from './Icons';

interface TradingViewWidget {
    widget: new (config: Record<string, unknown>) => unknown;
}

declare global {
    interface Window {
        TradingView: TradingViewWidget;
    }
}

const TradingTerminalWindow: React.FC = () => {
    const [mode, setMode] = useState<'analysis' | 'execution' | 'risk'>('analysis');
    const containerRef = useRef<HTMLDivElement>(null);

    // TradingView Loader
    useEffect(() => {
        if (mode === 'analysis') {
            const script = document.createElement('script');
            script.src = "https://s3.tradingview.com/tv.js";
            script.async = true;
            script.onload = () => {
                if (window.TradingView && containerRef.current) {
                    containerRef.current.innerHTML = ''; // Clear prev
                    new window.TradingView.widget({
                        "width": "100%",
                        "height": "100%",
                        "symbol": "BINANCE:BTCUSDT",
                        "interval": "15",
                        "timezone": "Etc/UTC",
                        "theme": "dark",
                        "style": "1",
                        "locale": "en",
                        "toolbar_bg": "#131722",
                        "enable_publishing": false,
                        "withdateranges": true,
                        "hide_side_toolbar": false,
                        "allow_symbol_change": true,
                        "details": true,
                        "container_id": "tv_chart_container"
                    });
                }
            };
            document.head.appendChild(script);
        }
    }, [mode]);

    return (
        <div className="h-full w-full flex flex-col bg-[#09090b]">
            {/* Terminal Header / Switcher */}
            <div className="flex-none h-12 bg-[#121214] border-b border-white/5 flex items-center justify-between px-4">
                <div className="flex bg-black p-1 rounded-xl border border-white/5">
                    {[
                        { id: 'analysis', label: 'NEURAL_CHART', icon: <IconChart className="w-3.5 h-3.5" /> },
                        { id: 'execution', label: 'MT5_DIRECT', icon: <IconTerminal className="w-3.5 h-3.5" /> },
                        { id: 'risk', label: 'RISK_CENTER', icon: <IconGlobe className="w-3.5 h-3.5" /> }
                    ].map(item => (
                        <button 
                            key={item.id}
                        onClick={() => setMode(item.id as 'analysis' | 'execution' | 'risk')}
                            className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all ${mode === item.id ? 'bg-[var(--accent-primary)] text-black shadow-[0_0_10px_rgba(16,185,129,0.3)]' : 'text-zinc-500 hover:text-zinc-300'}`}
                        >
                            {item.icon} {item.label}
                        </button>
                    ))}
                </div>

                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2 bg-zinc-900 px-3 py-1 rounded-lg border border-white/5">
                        <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></div>
                        <span className="text-[9px] font-black text-zinc-400 uppercase tracking-[0.2em]">
                            STREAMS_ACTIVE
                        </span>
                    </div>
                </div>
            </div>

            {/* Content Area */}
            <div className="flex-1 relative overflow-hidden">
                {mode === 'analysis' && (
                    <div id="tv_chart_container" ref={containerRef} className="h-full w-full bg-[#131722]" />
                )}
                
                {mode === 'execution' && (
                    <div className="h-full w-full flex flex-col">
                        <div className="flex-none bg-[#121214] border-b border-white/5 px-4 py-2 text-[9px] text-zinc-500 flex justify-between font-bold uppercase tracking-widest">
                            <span>Institutional Provider: <strong className="text-zinc-300">MetaQuotes_v5</strong></span>
                            <span className="text-emerald-500">Secure_SSL_Handshake</span>
                        </div>
                        <iframe 
                            src="https://trade.mql5.com/trade?servers=MetaQuotes-Demo&trade_server=MetaQuotes-Demo&demo_all_servers=1&startup_mode=open_demo&lang=en" 
                            className="w-full h-full border-none invert hue-rotate-180 brightness-90 grayscale-[0.2]"
                            allowFullScreen={true}
                            title="MetaTrader 5 Web Terminal"
                        />
                    </div>
                )}

                {mode === 'risk' && (
                    <div className="h-full w-full bg-[#09090b] p-8 overflow-y-auto custom-scrollbar">
                        <div className="max-w-4xl mx-auto space-y-8">
                            <div className="flex items-center gap-4 mb-8">
                                <div className="w-12 h-12 bg-emerald-500/10 rounded-2xl flex items-center justify-center border border-emerald-500/20">
                                    <IconGlobe className="w-6 h-6 text-emerald-500" />
                                </div>
                                <div>
                                    <h2 className="text-xl font-black text-zinc-100 uppercase tracking-tighter">Quant Risk Control</h2>
                                    <p className="text-[10px] text-zinc-500 uppercase tracking-widest font-bold">Capital Preservation & Position Sizing Engine</p>
                                </div>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                {/* Risk Calculator Card */}
                                <div className="bg-[#121214] p-6 rounded-2xl border border-white/5 shadow-2xl space-y-6">
                                    <h3 className="text-[11px] font-black text-[var(--accent-primary)] uppercase tracking-[0.2em]">Position_Size_Calculator</h3>
                                    <div className="space-y-4">
                                        <div className="space-y-1">
                                            <label className="text-[9px] font-black text-zinc-500 uppercase tracking-widest">Account Equity ($)</label>
                                            <input type="number" defaultValue="100000" className="w-full bg-black border border-white/10 rounded-xl px-4 py-3 text-sm font-mono text-zinc-100 focus:outline-none focus:border-emerald-500/50" />
                                        </div>
                                        <div className="grid grid-cols-2 gap-4">
                                            <div className="space-y-1">
                                                <label className="text-[9px] font-black text-zinc-500 uppercase tracking-widest">Risk %</label>
                                                <input type="number" defaultValue="1" className="w-full bg-black border border-white/10 rounded-xl px-4 py-3 text-sm font-mono text-zinc-100 focus:outline-none" />
                                            </div>
                                            <div className="space-y-1">
                                                <label className="text-[9px] font-black text-zinc-500 uppercase tracking-widest">Stop Loss (%)</label>
                                                <input type="number" defaultValue="2" className="w-full bg-black border border-white/10 rounded-xl px-4 py-3 text-sm font-mono text-zinc-100 focus:outline-none" />
                                            </div>
                                        </div>
                                        <div className="pt-4">
                                            <div className="bg-emerald-500/10 border border-emerald-500/20 p-4 rounded-xl flex justify-between items-center">
                                                <span className="text-[10px] font-black text-emerald-500 uppercase">CALCULATED_SIZE</span>
                                                <span className="text-xl font-mono font-bold text-zinc-100">$50,000.00</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                {/* Kelly Criterion Card */}
                                <div className="bg-[#121214] p-6 rounded-2xl border border-white/5 shadow-2xl space-y-6">
                                    <h3 className="text-[11px] font-black text-blue-500 uppercase tracking-[0.2em]">Kelly_Optimization</h3>
                                    <div className="space-y-4">
                                        <div className="flex justify-between items-center text-[10px] font-bold text-zinc-400">
                                            <span>Win Rate</span>
                                            <span className="text-zinc-100">58%</span>
                                        </div>
                                        <div className="w-full h-1 bg-zinc-800 rounded-full">
                                            <div className="w-[58%] h-full bg-blue-500 rounded-full shadow-[0_0_8px_rgba(59,130,246,0.5)]"></div>
                                        </div>
                                        <div className="flex justify-between items-center text-[10px] font-bold text-zinc-400">
                                            <span>Profit Factor</span>
                                            <span className="text-zinc-100">2.1</span>
                                        </div>
                                        <div className="w-full h-1 bg-zinc-800 rounded-full">
                                            <div className="w-[70%] h-full bg-blue-500 rounded-full shadow-[0_0_8px_rgba(59,130,246,0.5)]"></div>
                                        </div>
                                        
                                        <div className="pt-4 border-t border-white/5">
                                            <div className="text-[9px] font-black text-zinc-500 uppercase mb-2">Recommendation</div>
                                            <p className="text-[11px] text-zinc-400 italic">Apply fractional Kelly (0.25x) for maximum terminal growth while minimizing ruin risk. Recommended allocation: <strong>4.2%</strong> per setup.</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default TradingTerminalWindow;
