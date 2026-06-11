
import React, { useContext, useEffect, useRef, useState } from 'react';
import { AgentState, SwarmAgent, SystemPatch } from '../types';
import SwarmGraph from './SwarmGraph';
import { BrowserFS } from '../services/file_system';
import { MLEngine } from '../services/ml_engine';
import { IconSearch, IconDownload, IconCheck, IconShield, IconCode, IconGlobe, IconLink, IconBrain } from './Icons';
import { ThemeContext } from '../App';

interface Props {
  state: AgentState;
  agents: SwarmAgent[];
}

const AgentHud: React.FC<Props> = ({ state, agents }) => {
  const { theme } = useContext(ThemeContext);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [activeTab, setActiveTab] = useState<'live' | 'audit' | 'sources' | 'brain'>('live');
  const [evState, setEvState] = useState(MLEngine.getEvolutionState());
  
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [state.logs, state.currentAction]);

  useEffect(() => {
      // Poll for evolution updates
      const interval = setInterval(() => {
          setEvState(MLEngine.getEvolutionState());
      }, 5000);
      return () => clearInterval(interval);
  }, []);

  const auditLogs = state.knowledgeBase.filter(k => k.category === 'event').reverse();
  const dataSources = BrowserFS.getDataSources();
  const activeTaskCount = state.tasks.filter(t => t.status === 'active').length;

  return (
    <div className={`w-full h-full flex flex-col ${theme === 'dark' ? 'bg-[#09090b]' : 'bg-white'}`}>
      {/* Tabs */}
      <div className={`flex-none flex items-center justify-between px-3 pt-2 border-b backdrop-blur-xl ${theme === 'dark' ? 'border-white/5 bg-[#121214]/50' : 'border-black/5 bg-white/50'}`}>
        <div className="flex items-center gap-1 overflow-x-auto">
          {['live', 'audit', 'sources', 'brain'].map((tab) => (
             <button
                key={tab}
                onClick={() => setActiveTab(tab as any)}
                className={`px-4 py-2 text-[10px] font-black uppercase tracking-[0.2em] transition-all relative ${
                    activeTab === tab 
                    ? 'text-[#10b981]' 
                    : theme === 'dark' ? 'text-zinc-600 hover:text-zinc-400' : 'text-zinc-400 hover:text-zinc-600'
                }`}
             >
                 {tab === 'brain' ? 'Neural_Net' : tab.toUpperCase()}
                 {activeTab === tab && <div className="absolute bottom-0 left-0 w-full h-0.5 bg-[#10b981] shadow-[0_0_8px_#10b981]"></div>}
             </button>
          ))}
        </div>
        <div className="flex items-center gap-4 pr-3 pb-1">
            <span className={`text-[9px] font-black uppercase bg-zinc-900 px-2 py-0.5 rounded border ${theme === 'dark' ? 'text-zinc-500 border-white/5 bg-zinc-900' : 'text-zinc-400 border-black/5 bg-zinc-100'}`}>
                GEN_{evState.generation}
            </span>
            <div className={`w-2 h-2 rounded-full ${state.isActive ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)] animate-pulse' : 'bg-zinc-800'}`}></div>
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-hidden relative">
        
        {/* LIVE VIEW */}
        {activeTab === 'live' && (
            <div className="h-full flex flex-col">
                <div className={`h-[180px] md:h-[200px] flex-none border-b flex items-center justify-center relative ${theme === 'dark' ? 'border-white/5 bg-[#09090b]' : 'border-black/5 bg-zinc-50'}`}>
                    <SwarmGraph agents={agents} state={state} />
                    
                    {/* Active Task Overlay */}
                    {activeTaskCount > 0 && (
                        <div className="absolute top-3 right-3 flex flex-col gap-2 items-end">
                            {state.tasks.filter(t => t.status === 'active').map(t => (
                                <div key={t.id} className="bg-emerald-500/10 backdrop-blur border border-emerald-500/20 px-3 py-1 rounded-lg text-[9px] text-emerald-500 font-black flex items-center gap-2 shadow-2xl">
                                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                                    {agents.find(a => a.id === t.agentId)?.name.toUpperCase() || 'AGENT'} WORKING
                                </div>
                            ))}
                        </div>
                    )}
                </div>
                
                {/* Active Thought Process Terminal */}
                <div className={`flex-1 flex flex-col font-mono text-[10px] ${theme === 'dark' ? 'bg-[#09090b] text-zinc-400' : 'bg-white text-zinc-600'}`}>
                    <div className={`px-4 py-2 border-b flex items-center justify-between ${theme === 'dark' ? 'border-white/5 bg-[#121214]' : 'border-black/5 bg-zinc-50'}`}>
                        <span className={`font-black uppercase tracking-widest flex items-center gap-2 text-[9px] ${theme === 'dark' ? 'text-zinc-500' : 'text-zinc-400'}`}>
                            <IconCode className="w-3 h-3" />
                            NEURAL_LOG_UPLINK
                        </span>
                        <span className="text-[9px] font-mono opacity-50">STREAMS_ENCRYPTED</span>
                    </div>
                    <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-2 custom-scrollbar">
                        {state.logs.length === 0 && <div className="text-zinc-800 italic uppercase font-black text-[9px]">Initiating neural handshake...</div>}
                        {state.logs.map((log, i) => {
                            const isApi = log.includes('[API]') || log.includes('[MARKET]');
                            const isDeploy = log.includes('[DEPLOY]');
                            const isFail = log.includes('[FAIL]') || log.includes('CRITICAL');
                            const isML = log.includes('[ML ENGINE]');
                            
                            return (
                                <div key={i} className={`break-all border-l-2 pl-3 py-0.5 ${isFail ? 'border-red-500 bg-red-500/5' : isML ? 'border-purple-500 bg-purple-500/5' : isApi ? 'border-blue-500 bg-blue-500/5' : isDeploy ? 'border-emerald-500 bg-emerald-500/5' : theme === 'dark' ? 'border-zinc-800' : 'border-zinc-200'}`}>
                                    <span className="text-zinc-500 mr-2">[{new Date().toLocaleTimeString().split(' ')[0]}]</span>
                                    <span className={isFail ? 'text-red-400 font-bold' : isML ? 'text-purple-400' : isApi ? 'text-blue-400' : isDeploy ? 'text-emerald-500' : theme === 'dark' ? 'text-zinc-300' : 'text-zinc-700'}>
                                        {log.toUpperCase()}
                                    </span>
                                </div>
                            );
                        })}
                        {state.isActive && (
                            <div className="animate-pulse text-emerald-500 font-black">█</div>
                        )}
                    </div>
                </div>
            </div>
        )}


        {/* BRAIN (NEURAL NET) VIEW */}
        {activeTab === 'brain' && (
            <div className="h-full flex flex-col bg-gray-50 p-4 overflow-y-auto custom-scrollbar">
                <div className="flex items-center gap-3 mb-4">
                    <div className="bg-purple-100 p-2 rounded-lg">
                        <IconBrain className="w-6 h-6 text-purple-600" />
                    </div>
                    <div>
                        <h3 className="text-sm font-bold text-gray-900">Evolution Engine (Gen {evState.generation})</h3>
                        <p className="text-[10px] text-gray-500">Last Optimization: {new Date(evState.lastOptimization).toLocaleString()}</p>
                    </div>
                </div>

                <div className="grid grid-cols-1 gap-4">
                    <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
                        <h4 className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-3">Top Optimized Strategies</h4>
                        <div className="space-y-3">
                            {Object.entries(evState.weights).sort(([,a], [,b]) => (b as number) - (a as number)).map(([name, weight]) => (
                                <div key={name} className="flex flex-col gap-1">
                                    <div className="flex justify-between text-[10px] font-medium text-gray-700">
                                        <span>{name}</span>
                                        <span>Weight: {(weight as number).toFixed(2)}</span>
                                    </div>
                                    <div className="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden">
                                        <div 
                                            className="h-full bg-purple-500 transition-all duration-500" 
                                            style={{ width: `${((weight as number) / 10) * 100}%` }}
                                        ></div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        )}

        {/* AUDIT VIEW */}
        {activeTab === 'audit' && (
            <div className="h-full flex flex-col bg-gray-50">
                <div className="flex-1 overflow-y-auto p-2 space-y-2 custom-scrollbar">
                    {auditLogs.map((log) => (
                        <div key={log.id} className="bg-white p-2.5 rounded-lg border border-gray-200 shadow-sm flex flex-col gap-1">
                            <div className="flex justify-between items-center">
                                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded border border-gray-200 bg-gray-50 uppercase tracking-wider text-gray-600">
                                    {log.category}
                                </span>
                                <span className="text-[9px] text-gray-400 font-mono">{new Date(log.timestamp).toLocaleTimeString()}</span>
                            </div>
                            <div className="flex items-center gap-1.5 mt-1">
                                <span className="text-[10px] font-bold text-gray-700 bg-gray-100 px-1 rounded">{log.sourceAgentId}</span>
                                <span className="text-[11px] text-gray-600 leading-tight">{log.content}</span>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        )}

        {/* SOURCES VIEW */}
        {activeTab === 'sources' && (
            <div className="h-full flex flex-col bg-gray-50">
                 <div className="flex-1 overflow-y-auto p-3 space-y-2 custom-scrollbar">
                    {dataSources.map(source => (
                        <div key={source.id} className="bg-white p-3 rounded-xl border border-gray-200 shadow-sm flex flex-col gap-2">
                             <div className="flex justify-between items-start">
                                <div className="flex items-center gap-2">
                                    <div className={`p-1.5 rounded-lg ${source.type === 'api' ? 'bg-blue-100 text-blue-600' : 'bg-orange-100 text-orange-600'}`}>
                                        <IconGlobe className="w-3.5 h-3.5" />
                                    </div>
                                    <div>
                                        <div className="text-xs font-bold text-gray-900">{source.name}</div>
                                        <div className="text-[9px] text-gray-400 uppercase">{source.category}</div>
                                    </div>
                                </div>
                             </div>
                             <code className="text-[9px] bg-gray-50 p-1 rounded text-gray-500 truncate">{source.endpoint}</code>
                        </div>
                    ))}
                 </div>
            </div>
        )}
      </div>
    </div>
  );
};

export default AgentHud;
