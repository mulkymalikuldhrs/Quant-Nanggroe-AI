
import React, { useEffect, useState, useContext } from 'react';
import { BrowserFS } from '../services/file_system';
import { MarketService } from '../services/market';
import { PortfolioPosition, TradeHistoryItem } from '../types';
import { IconBook, IconActivity, IconTerminal } from './Icons';
import { ThemeContext } from '../App';

const PortfolioWindow: React.FC = () => {
  const { theme } = useContext(ThemeContext);
  const [activeTab, setActiveTab] = useState<'positions' | 'history' | 'exposure'>('positions');
  const [portfolio, setPortfolio] = useState<PortfolioPosition[]>([]);
  const [history, setHistory] = useState<TradeHistoryItem[]>([]);
  const [lastSync, setLastSync] = useState<number>(Date.now());
  const [isSyncing, setIsSyncing] = useState(false);

  const loadData = () => {
      setPortfolio(BrowserFS.getPortfolio());
      setHistory(BrowserFS.getTradeHistory());
  };

  const syncPrices = async () => {
      setIsSyncing(true);
      const current = BrowserFS.getPortfolio();
      const updates: Record<string, number> = {};
      const assets = current.filter(p => p.ticker !== 'USD' && p.amount > 0);
      
        for (const asset of assets) {
            const marketData = await MarketService.getPrice(asset.ticker);
            if (marketData) {
                updates[asset.ticker] = marketData.currentPrice;
            }
        }

      if (Object.keys(updates).length > 0) {
          BrowserFS.updatePortfolioPrices(updates);
          loadData();
          setLastSync(Date.now());
      }
      setIsSyncing(false);
  };

  useEffect(() => {
    loadData();
    syncPrices();
    const interval = setInterval(loadData, 1000);
    const priceInterval = setInterval(syncPrices, 30000);
    return () => { clearInterval(interval); clearInterval(priceInterval); };
  }, []);

  const totalValue = portfolio.reduce((acc, p) => {
      if (p.ticker === 'USD') return acc + p.amount;
      return acc + (p.amount * p.currentPrice);
  }, 0);

  const cash = portfolio.find(p => p.ticker === 'USD')?.amount || 0;
  const margin = totalValue - cash;

  return (
    <div className={`h-full w-full flex flex-col font-mono text-[11px] ${theme === 'dark' ? 'bg-[#0f0f12] text-zinc-300' : 'bg-zinc-50 text-zinc-800'}`}>
        
        {/* Account Summary Bar (MT4 Style) */}
        <div className={`flex-none px-4 py-2 border-b flex items-center gap-6 ${theme === 'dark' ? 'bg-[#1a1a1e] border-white/5' : 'bg-white border-zinc-200 shadow-sm'}`}>
            <div className="flex flex-col">
                <span className="text-[9px] opacity-50 uppercase font-bold">Balance</span>
                <span className="text-sm font-bold tracking-tight">${cash.toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
            </div>
            <div className="flex flex-col">
                <span className="text-[9px] opacity-50 uppercase font-bold">Equity</span>
                <span className="text-sm font-bold tracking-tight text-blue-500">${totalValue.toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
            </div>
            <div className="flex flex-col">
                <span className="text-[9px] opacity-50 uppercase font-bold">Margin</span>
                <span className="text-sm font-bold tracking-tight">${margin.toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
            </div>
            <div className="ml-auto flex items-center gap-4">
                <div className="text-right">
                    <div className="text-[9px] opacity-50 uppercase font-bold">Total PnL</div>
                    <div className={`text-sm font-bold ${(totalValue - 100000) >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>
                        {(totalValue - 100000) >= 0 ? '+' : ''}${(totalValue - 100000).toLocaleString(undefined, {minimumFractionDigits: 2})}
                    </div>
                </div>
                <button onClick={syncPrices} className={`p-2 rounded hover:bg-white/5 transition-colors ${isSyncing ? 'animate-spin' : ''}`}>
                    <IconActivity className="w-4 h-4 opacity-50" />
                </button>
            </div>
        </div>

        {/* Navigation Tabs */}
        <div className={`flex border-b ${theme === 'dark' ? 'bg-[#121216] border-white/5' : 'bg-zinc-100 border-zinc-200'}`}>
            {['positions', 'history', 'exposure'].map((tab) => (
                <button 
                    key={tab}
                    onClick={() => setActiveTab(tab as any)}
                    className={`px-6 py-2 uppercase tracking-tighter font-bold border-r ${theme === 'dark' ? 'border-white/5' : 'border-zinc-200'} ${activeTab === tab ? (theme === 'dark' ? 'bg-[#1a1a1e] text-blue-400' : 'bg-white text-blue-600') : 'opacity-40 hover:opacity-100'}`}
                >
                    {tab}
                </button>
            ))}
        </div>
        
        <div className="flex-1 overflow-auto custom-scrollbar">
            {activeTab === 'positions' ? (
                <table className="w-full text-left border-collapse">
                    <thead className={`sticky top-0 z-10 ${theme === 'dark' ? 'bg-[#1a1a1e]' : 'bg-zinc-100'}`}>
                        <tr className="border-b border-white/5 text-[9px] opacity-50 uppercase font-bold">
                            <th className="py-2 px-4">Symbol</th>
                            <th className="py-2 px-4 text-right">Volume</th>
                            <th className="py-2 px-4 text-right">Price</th>
                            <th className="py-2 px-4 text-right">S/L</th>
                            <th className="py-2 px-4 text-right">T/P</th>
                            <th className="py-2 px-4 text-right">Market</th>
                            <th className="py-2 px-4 text-right font-bold">Profit</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                        {portfolio.filter(p => p.ticker !== 'USD' && p.amount > 0).map((pos) => {
                            const pnl = (pos.currentPrice - pos.avgPrice) * pos.amount;
                            const pnlColor = pnl >= 0 ? 'text-emerald-500' : 'text-red-500';

                            return (
                                <tr key={pos.ticker} className={`hover:bg-white/5 transition-colors ${theme === 'dark' ? 'text-zinc-400' : 'text-zinc-700'}`}>
                                    <td className="py-2 px-4 font-bold text-blue-400">{pos.ticker}</td>
                                    <td className="py-2 px-4 text-right">{pos.amount.toFixed(2)}</td>
                                    <td className="py-2 px-4 text-right">{pos.avgPrice.toLocaleString()}</td>
                                    <td className="py-2 px-4 text-right opacity-30">0.00</td>
                                    <td className="py-2 px-4 text-right opacity-30">0.00</td>
                                    <td className="py-2 px-4 text-right">{pos.currentPrice.toLocaleString()}</td>
                                    <td className={`py-2 px-4 text-right font-bold ${pnlColor}`}>{pnl >= 0 ? '+' : ''}{pnl.toFixed(2)}</td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            ) : activeTab === 'history' ? (
                <table className="w-full text-left border-collapse">
                    <thead className={`sticky top-0 z-10 ${theme === 'dark' ? 'bg-[#1a1a1e]' : 'bg-zinc-100'}`}>
                        <tr className="border-b border-white/5 text-[9px] opacity-50 uppercase font-bold">
                            <th className="py-2 px-4">Time</th>
                            <th className="py-2 px-4">Order</th>
                            <th className="py-2 px-4 text-right">Size</th>
                            <th className="py-2 px-4 text-right">Entry</th>
                            <th className="py-2 px-4 text-right">Exit</th>
                            <th className="py-2 px-4 text-right font-bold">PnL</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                         {history.map(tx => (
                             <tr key={tx.id} className="hover:bg-white/5 transition-colors opacity-80">
                                 <td className="py-2 px-4 text-[10px]">
                                     {new Date(tx.timestamp).toLocaleString([], {month:'short', day:'numeric', hour:'2-digit', minute:'2-digit'})}
                                 </td>
                                 <td className="py-2 px-4 font-bold">
                                     <span className={tx.action === 'BUY' ? 'text-blue-500' : 'text-orange-500'}>
                                         {tx.action} {tx.ticker}
                                     </span>
                                 </td>
                                 <td className="py-2 px-4 text-right">{tx.amount.toFixed(2)}</td>
                                 <td className="py-2 px-4 text-right">{tx.price.toLocaleString()}</td>
                                 <td className="py-2 px-4 text-right">{(tx.price * 1.001).toLocaleString()}</td>
                                 <td className={`py-2 px-4 text-right font-bold ${tx.realizedPnL && tx.realizedPnL >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>
                                     {tx.realizedPnL ? (tx.realizedPnL >= 0 ? '+' : '') + tx.realizedPnL.toFixed(2) : '0.00'}
                                 </td>
                             </tr>
                         ))}
                    </tbody>
                </table>
            ) : (
                <div className="p-8 flex flex-col items-center justify-center opacity-20 text-center">
                    <IconTerminal className="w-12 h-12 mb-4" />
                    <p className="text-sm font-bold uppercase tracking-widest">Exposure Analysis</p>
                    <p className="mt-2 text-[10px] max-w-xs">Dynamic exposure calculation and risk weighting module active.</p>
                </div>
            )}

            {portfolio.length <= 1 && history.length === 0 && (
                <div className="flex flex-col items-center justify-center mt-20 opacity-20 gap-2">
                    <IconBook className="w-12 h-12" />
                    <p className="text-xs font-bold uppercase tracking-widest">Terminal Empty</p>
                    <p className="text-[10px]">No active positions found in current session.</p>
                </div>
            )}
        </div>

        {/* Footer info bar */}
        <div className={`flex-none h-6 px-4 flex items-center justify-between text-[9px] font-bold uppercase tracking-widest ${theme === 'dark' ? 'bg-[#1a1a1e] border-t border-white/5 text-zinc-500' : 'bg-zinc-100 border-t border-zinc-200 text-zinc-400'}`}>
            <div className="flex items-center gap-4">
                <span>Server: NANGGROE-LIVE-01</span>
                <span className="text-emerald-500/50">Ping: 12ms</span>
            </div>
            <div>
                MT4 BRIDGE v11.5 | ASYNC-LINK READY
            </div>
        </div>
    </div>
  );
};

export default PortfolioWindow;
