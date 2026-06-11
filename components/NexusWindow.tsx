
import React, { useState, useEffect, useContext } from 'react';
import { ThemeContext } from '../App';
import WindowFrame from './WindowFrame';
import { quantumEngine } from '../services/quantum_engine';
import { ResearchAgent } from '../services/research_agent';

interface NexusWindowProps {
  isOpen: boolean;
  onClose: () => void;
  onMinimize: () => void;
  onFocus: () => void;
  isActive: boolean;
  zIndex: number;
}

const NexusWindow: React.FC<NexusWindowProps> = ({
  isOpen,
  onClose,
  onMinimize,
  onFocus,
  isActive,
  zIndex
}) => {
  const { theme } = useContext(ThemeContext);
  const [metrics, setMetrics] = useState(quantumEngine.getLiveMetrics());
  const [forecasts, setForecasts] = useState<string[]>([]);
  const [researchLogs, setResearchLogs] = useState<string[]>([]);

  useEffect(() => {
    const interval = setInterval(() => {
      setMetrics(quantumEngine.getLiveMetrics());
      const symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT'];
      const randomSymbol = symbols[Math.floor(Math.random() * symbols.length)];
      const forecast = quantumEngine.getQuantumForecast(randomSymbol);
      setForecasts(prev => [forecast, ...prev].slice(0, 10));
      
      // Sync with research agent logs if available
      const logs = ResearchAgent.getLogs().slice(-5).reverse();
      setResearchLogs(logs);
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  const glassStyle = theme === 'dark' 
    ? 'bg-white/5 border border-white/10' 
    : 'bg-black/5 border border-black/10';

  const accentColor = 'text-cyan-400';

    return (
      <WindowFrame
        title="COMMAND CENTER v11.5"
        isOpen={isOpen}
        onClose={onClose}
        onMinimize={onMinimize}
        onFocus={onFocus}
        isActive={isActive}
        zIndex={zIndex}
        icon={<svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" /></svg>}
        defaultSize={{ width: 900, height: 600 }}
      >
        <div className={`p-6 min-h-full ${theme === 'dark' ? 'text-white' : 'text-zinc-800'} font-sans text-[11px]`}>
          <div className="grid grid-cols-12 gap-4">
            
            {/* System Metrics */}
            <div className="col-span-4 space-y-4">
              <div className={`p-4 rounded-xl ${glassStyle} relative overflow-hidden group`}>
                <div className="absolute inset-0 bg-cyan-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-700" />
                <h3 className={`text-[10px] font-bold mb-3 opacity-50 uppercase tracking-widest ${accentColor}`}>Market Engine</h3>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="opacity-60">STABILITY</span>
                    <span className="font-bold text-cyan-400">{metrics.coherence}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="opacity-60">ACTIVE_NODES</span>
                    <span className="font-bold">{metrics.qubitsActive}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="opacity-60">PROCESSING_LOAD</span>
                    <span className="font-bold text-amber-400">{metrics.synapticLoad}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="opacity-60">ENGINE_STATUS</span>
                    <span className="font-bold text-emerald-400">{metrics.nexusStatus}</span>
                  </div>
                </div>
              </div>

              <div className={`p-4 rounded-xl ${glassStyle}`}>
                <h3 className="text-[10px] font-bold mb-3 opacity-50 uppercase tracking-widest">Intelligence Feed</h3>
                <div className="space-y-1 opacity-80 h-32 overflow-hidden">
                  {researchLogs.map((log, i) => (
                    <div key={i} className="truncate border-l border-white/10 pl-2 py-0.5">
                      {log}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Analysis Feed */}
            <div className="col-span-8 flex flex-col space-y-4">
              <div className={`flex-1 p-4 rounded-xl ${glassStyle} flex flex-col`}>
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-[10px] font-bold opacity-50 uppercase tracking-widest">Market Forecasts</h3>
                  <div className="flex gap-2">
                    <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                    <span className="text-[9px] opacity-40">REAL-TIME DATA</span>
                  </div>
                </div>
                <div className="flex-1 space-y-2 overflow-y-auto pr-2 custom-scrollbar">
                  {forecasts.map((f, i) => (
                    <div key={i} className={`p-2 rounded border border-white/5 transition-all hover:bg-white/5 ${i === 0 ? 'bg-cyan-500/10 border-cyan-500/20' : ''}`}>
                      {f}
                    </div>
                  ))}
                </div>
              </div>

            
            <div className="h-40 grid grid-cols-2 gap-4">
               <div className={`p-4 rounded-xl ${glassStyle} flex flex-col justify-center items-center text-center`}>
                  <div className="text-[20px] font-bold text-cyan-400">98.4%</div>
                  <div className="text-[9px] opacity-40 mt-1 uppercase">Model Synergy</div>
               </div>
               <div className={`p-4 rounded-xl ${glassStyle} flex flex-col justify-center items-center text-center`}>
                  <div className="text-[20px] font-bold text-amber-400">1.2ms</div>
                  <div className="text-[9px] opacity-40 mt-1 uppercase">Inference Latency</div>
               </div>
            </div>
          </div>
        </div>
      </div>
    </WindowFrame>
  );
};

export default NexusWindow;
