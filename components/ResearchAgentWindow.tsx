
import React, { useState, useEffect } from 'react';
import { ResearchAgent } from '../services/research_agent';
import { IconSearch, IconBot, IconZap, IconActivity, IconGlobe, IconDatabase } from './Icons';

export const ResearchAgentWindow: React.FC = () => {
    const [isRunning, setIsRunning] = useState(ResearchAgent.isAutonomouslyRunning);
    const [logs, setLogs] = useState<string[]>([]);

    useEffect(() => {
        const interval = setInterval(() => {
            setLogs([...ResearchAgent.logs]);
            setIsRunning(ResearchAgent.isAutonomouslyRunning);
        }, 1000);
        return () => clearInterval(interval);
    }, []);

    const toggleAgent = () => {
        if (isRunning) {
            ResearchAgent.stopAutonomousResearch();
        } else {
            ResearchAgent.startAutonomousResearch(60000); // 1 min for demo
        }
        setIsRunning(!isRunning);
    };

    return (
        <div className="flex flex-col h-full bg-[#05050a]/80 backdrop-blur-xl text-white font-mono p-4">
            <div className="flex items-center justify-between mb-6 bg-white/5 p-4 rounded-xl border border-white/10">
                <div className="flex items-center gap-4">
                    <div className={`w-3 h-3 rounded-full ${isRunning ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`} />
                    <div>
                          <h2 className="text-xl font-bold flex items-center gap-2">
                              <IconBot className="w-5 h-5 text-blue-400" />
                              Intelligence Agent
                          </h2>
                          <p className="text-[10px] opacity-50 uppercase tracking-widest">Autonomous Data Collection & Analysis</p>

                    </div>
                </div>
                <button 
                    onClick={toggleAgent}
                    className={`px-6 py-2 rounded-lg font-bold transition-all ${isRunning ? 'bg-red-500/20 text-red-400 border border-red-500/40 hover:bg-red-500/30' : 'bg-blue-600 text-white hover:bg-blue-500 shadow-lg shadow-blue-600/20'}`}
                >
                    {isRunning ? 'SHUTDOWN' : 'INITIALIZE'}
                </button>
            </div>

            <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="bg-white/5 p-3 rounded-lg border border-white/5">
                    <div className="flex items-center gap-2 text-blue-400 mb-1">
                        <IconGlobe className="w-4 h-4" />
                        <span className="text-xs font-bold">SOURCES</span>
                    </div>
                    <div className="text-2xl font-black">6</div>
                </div>
                <div className="bg-white/5 p-3 rounded-lg border border-white/5">
                    <div className="flex items-center gap-2 text-emerald-400 mb-1">
                        <IconDatabase className="w-4 h-4" />
                        <span className="text-xs font-bold">C:/ DATA</span>
                    </div>
                    <div className="text-2xl font-black">{Math.floor(Math.random() * 100) + 240} MB</div>
                </div>
                <div className="bg-white/5 p-3 rounded-lg border border-white/5">
                    <div className="flex items-center gap-2 text-purple-400 mb-1">
                        <IconActivity className="w-4 h-4" />
                        <span className="text-xs font-bold">LATENCY</span>
                    </div>
                    <div className="text-2xl font-black">12ms</div>
                </div>
            </div>

            <div className="flex-1 overflow-hidden flex flex-col bg-black/40 rounded-xl border border-white/10">
                <div className="px-4 py-2 bg-white/5 border-b border-white/10 flex items-center justify-between">
                    <span className="text-[10px] font-bold text-white/40">NEURAL_LOG_STREAM</span>
                    <IconZap className="w-3 h-3 text-yellow-500 animate-pulse" />
                </div>
                <div className="flex-1 overflow-y-auto p-4 space-y-1 font-mono text-[11px]">
                    {logs.length === 0 ? (
                        <div className="text-white/20 italic">Waiting for agent initialization...</div>
                    ) : (
                        logs.map((log, i) => (
                            <div key={i} className="flex gap-2">
                                <span className="text-blue-500 shrink-0">{">"}</span>
                                <span className={log.includes('Error') ? 'text-red-400' : log.includes('Saved') ? 'text-emerald-400' : 'text-white/80'}>
                                    {log}
                                </span>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
};
