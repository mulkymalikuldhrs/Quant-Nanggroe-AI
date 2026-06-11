import React from 'react';
import { IconBrain, IconBot, IconGlobe, IconTerminal, IconChart } from './Icons';

export const SystemArchitecture: React.FC = () => {
    return (
        <div className="h-full w-full bg-[#09090b] p-6 overflow-y-auto custom-scrollbar">
            <div className="max-w-4xl mx-auto space-y-12 pb-20">
                
                {/* HEADER */}
                <div className="text-center space-y-2">
                    <h1 className="text-4xl font-black uppercase tracking-tighter text-white">Neural Swarm Architecture</h1>
                    <p className="text-emerald-500 font-mono text-sm tracking-widest">QUANT NANGGROE AI v10.0</p>
                </div>

                {/* FLOW DIAGRAM */}
                <div className="relative">
                    <div className="grid grid-cols-1 md:grid-cols-5 gap-4 relative z-10">
                        <Node icon={<IconTerminal />} title="Input" desc="Neural Terminal / OmniBar" color="blue" />
                        <div className="hidden md:flex items-center justify-center text-zinc-700">→</div>
                        <Node icon={<IconBrain />} title="Alpha Prime" desc="Coordinator & Decision Maker" color="emerald" highlight />
                        <div className="hidden md:flex items-center justify-center text-zinc-700">→</div>
                        <Node icon={<IconBot />} title="Swarm" desc="Parallel Agent Spawning" color="purple" />
                    </div>
                    
                    {/* CONNECTIONS (Visual only) */}
                    <div className="absolute inset-0 flex items-center justify-center opacity-20 pointer-events-none">
                        <div className="w-full h-[1px] bg-gradient-to-r from-transparent via-emerald-500 to-transparent"></div>
                    </div>
                </div>

                {/* AGENT SPECIALIZATION */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    <AgentCard name="Quant-Scanner" role="Technical Analysis" details="RSI, MACD, Volume Profile, Order Flow" color="emerald" />
                    <AgentCard name="News-Sentinel" role="Macro & Sentiment" details="Global News, Social Media, Fed Data" color="blue" />
                    <AgentCard name="Risk-Guardian" role="Safety & Risk" details="Stop Loss, Position Sizing, Hedging" color="red" />
                    <AgentCard name="Strategy-Weaver" role="Algo Development" details="Backtesting, Optimization, Python" color="amber" />
                </div>

                {/* THE CORE LOGIC */}
                <div className="glass-panel p-6 rounded-2xl border border-white/5 space-y-4">
                    <h3 className="text-lg font-bold flex items-center gap-2">
                        <IconChart className="text-emerald-500" />
                        Operational Flow (A-Z)
                    </h3>
                    <div className="space-y-3 text-sm text-zinc-400">
                        <div className="flex gap-4">
                            <span className="text-emerald-500 font-mono">01</span>
                            <p><span className="text-white font-bold">Parallel Spawning:</span> When a complex task arrives, Alpha Prime "splits" the workload across the swarm.</p>
                        </div>
                        <div className="flex gap-4">
                            <span className="text-emerald-500 font-mono">02</span>
                            <p><span className="text-white font-bold">Independent Research:</span> Each agent uses its own tools (Market API, Browser, Code Exec) to gather intelligence.</p>
                        </div>
                        <div className="flex gap-4">
                            <span className="text-emerald-500 font-mono">03</span>
                            <p><span className="text-white font-bold">Neural Synthesis:</span> Results are fed back to Alpha Prime for a final multi-perspective conclusion.</p>
                        </div>
                        <div className="flex gap-4">
                            <span className="text-emerald-500 font-mono">04</span>
                            <p><span className="text-white font-bold">Autonomous Execution:</span> The system opens required windows (Trading Terminal, Browser) and executes the plan.</p>
                        </div>
                    </div>
                </div>

            </div>
        </div>
    );
};

interface NodeProps {
    icon: React.ReactNode;
    title: string;
    desc: string;
    color: string;
    highlight?: boolean;
}

const Node = ({ icon, title, desc, color, highlight }: NodeProps) => (
    <div className={`p-4 rounded-xl border border-white/5 bg-white/5 text-center space-y-2 ${highlight ? 'ring-2 ring-emerald-500/50 scale-105 shadow-[0_0_30px_rgba(16,185,129,0.2)]' : ''}`}>
        <div className={`mx-auto w-10 h-10 rounded-full flex items-center justify-center bg-${color}-500/20 text-${color}-500`}>
            {icon}
        </div>
        <h4 className="font-bold text-white text-sm">{title}</h4>
        <p className="text-[10px] text-zinc-500">{desc}</p>
    </div>
);

interface AgentCardProps {
    name: string;
    role: string;
    details: string;
    color: string;
}

const AgentCard = ({ name, role, details, color }: AgentCardProps) => (
    <div className="glass-panel p-4 rounded-xl border border-white/5 hover:bg-white/[0.08] transition-all group">
        <div className={`text-[10px] font-mono text-${color}-500 mb-1 uppercase tracking-widest`}>{role}</div>
        <h4 className="font-bold text-white mb-2">{name}</h4>
        <p className="text-[10px] text-zinc-500 leading-relaxed">{details}</p>
    </div>
);
