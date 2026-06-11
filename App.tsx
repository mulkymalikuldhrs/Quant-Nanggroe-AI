
import React, { useState, useEffect, useRef } from 'react';
import { AutonomousAgent } from './services/gemini'; 
import { ChatMessage, MessageRole, AgentState, SwarmAgent, ModelOption, Attachment, SystemConfiguration, SystemAction, SystemNotification } from './types';
import { BrowserFS } from './services/file_system';
import { MemoryManager } from './services/memory_manager';
import ChatMessageComponent from './components/ChatMessage';
import InputArea from './components/InputArea';
import AgentHud from './components/AgentHud';
import ArtifactWindow from './components/ArtifactWindow';
import PortfolioWindow from './components/PortfolioWindow';
import MarketWindow from './components/MarketWindow'; 
import BrowserWindow from './components/BrowserWindow';
import TradingTerminalWindow from './components/TradingTerminalWindow';
import SwarmConfigModal from './components/SwarmConfigModal';
import { SystemArchitecture } from './components/SystemArchitecture';
import Avatar from './components/Avatar';
import WindowFrame from './components/WindowFrame';
import Taskbar from './components/Taskbar';
import OmniBar from './components/OmniBar'; 
import Launchpad from './components/Launchpad';
import ControlCenter from './components/ControlCenter';
import SystemUpdater from './components/SystemUpdater';
import { ResearchAgentWindow } from './components/ResearchAgentWindow';
import { KnowledgeBaseWindow } from './components/KnowledgeBaseWindow';
import NexusWindow from './components/NexusWindow';
import { IconCode, IconBot, IconSettings, IconBrain, IconBook, IconMaximize, IconGlobe, IconLogo, IconChart, IconBrowser, IconTerminal, IconSearch, IconSun, IconMoon, IconDatabase, IconLayers } from './components/Icons';
import { useAdaptiveLayout } from './services/adaptive_layout';
import { ResearchAgent } from './services/research_agent';
import ErrorBoundary from './components/ErrorBoundary';

// --- THEME CONTEXT ---
export const ThemeContext = React.createContext<{ theme: 'light' | 'dark', toggleTheme: () => void }>({ theme: 'light', toggleTheme: () => {} });

const INSTITUTIONAL_LOGIC = `You are Nanggroe AI (v15.3.0).

CORE MISSION:
- SWARM INTELLIGENCE: Coordinate specialized agents for market analysis.
- DATA-DRIVEN ANALYSIS: Use advanced mathematical models for forecasting.
- AUTONOMOUS RESEARCH: Gather intelligence from multiple sources.
- UNIFIED INTERFACE: Access all intelligence via the Command Center.
`;

const DEFAULT_AGENTS: SwarmAgent[] = [
  { id: '0', name: 'Alpha Prime', capability: 'portfolio-manager', instructions: INSTITUTIONAL_LOGIC, tools: ['googleSearch', 'codeExecution', 'marketData', 'spawnAgent', 'browserNavigation', 'researchAutomation'] },
  { id: '1', name: 'Quant-Scanner', capability: 'quant', instructions: 'Technical & Algorithmic Specialist.', tools: ['googleSearch', 'codeExecution', 'marketData'] },
  { id: '2', name: 'News-Sentinel', capability: 'fundamental', instructions: 'Macro & Sentiment Specialist.', tools: ['googleSearch', 'browserNavigation'] },
  { id: '3', name: 'Risk-Guardian', capability: 'risk-manager', instructions: 'Risk & Capital Specialist.', tools: ['codeExecution', 'marketData'] },
  { id: '4', name: 'Strategy-Weaver', capability: 'algo-dev', instructions: 'Python & Strategy Specialist.', tools: ['codeExecution'] }
];

const AVAILABLE_MODELS: ModelOption[] = [
    { id: 'gemini-2.0-flash-exp', name: 'Nanggroe Flash 11.5', provider: 'google' },
    { id: 'gemini-1.5-pro', name: 'Nanggroe Pro 11.5', provider: 'google' },
];

const DEFAULT_CONFIG: SystemConfiguration = {
  enableSelfHealing: true, enableAutoScaling: true, enableDynamicTools: true, enableScheduling: true, enableAutoSwitch: true,
  enableVoiceResponse: true, enableAutoLearning: true, 
  apiKeys: { google: '', groq: '', openai: '', huggingface: '', llm7: '', alphaVantage: '', finnhub: '', fred: '', polygon: '' }
};

type WindowId = 'terminal' | 'monitor' | 'settings' | 'about' | 'docs' | 'artifact' | 'portfolio' | 'market' | 'browser' | 'trading_terminal' | 'architecture' | 'research' | 'knowledge_base' | 'nexus';

interface WindowState {
    id: WindowId;
    isOpen: boolean;
    isMinimized: boolean;
    zIndex: number;
    title: string;
    icon: React.ReactNode;
    defaultPos: { x: number, y: number };
    defaultSize: { width: number, height: number };
}

const App: React.FC = () => {
    const { screenSize, getLayout } = useAdaptiveLayout();
    
    // --- THEME STATE ---
    const [theme, setTheme] = useState<'light' | 'dark'>('light');

    const toggleTheme = async () => {
        const next = theme === 'dark' ? 'light' : 'dark';
        setTheme(next);
        await storageManager.setItem('system-theme', next);
    };

    // ...

    // Clock & Init
    useEffect(() => {
        const interval = setInterval(() => setCurrentTime(new Date()), 1000);
        
        // Initialize Storage Services
        const initStorage = async () => {
            await storageManager.getItem('system-theme').then(saved => {
                if (saved) setTheme(saved as 'light' | 'dark');
            });
            await BrowserFS.init();
            await KnowledgeBase.initDisk();
            await MemoryManager.init();
            console.log("[System] Storage Services Initialized.");
        };
        initStorage();

        // Start Autonomous Research Agent v15.3
        ResearchAgent.startAutonomousResearch(60000); // 1 minute interval

        return () => {
            clearInterval(interval);
            ResearchAgent.stopAutonomousResearch();
        };
    }, []);

    const focusWindow = (id: WindowId) => {
        const newZ = highestZ + 1;
        setHighestZ(newZ);
        setActiveWindow(id);
        setWindows(prev => ({ ...prev, [id]: { ...prev[id], zIndex: newZ, isMinimized: false, isOpen: true } }));
    };

    const toggleWindow = (id: WindowId) => {
        const w = windows[id];
        if (!w.isOpen || w.isMinimized) focusWindow(id);
        else setWindows(prev => ({ ...prev, [id]: { ...prev[id], isMinimized: true } }));
    };

    const closeWindow = (id: WindowId) => setWindows(prev => ({ ...prev, [id]: { ...prev[id], isOpen: false } }));
    const minimizeWindow = (id: WindowId) => setWindows(prev => ({ ...prev, [id]: { ...prev[id], isMinimized: true } }));

    const handleSendMessage = async (text: string, attachments: Attachment[] = []) => {
      const userMsg: ChatMessage = { id: Date.now().toString(), role: MessageRole.USER, text, timestamp: Date.now(), attachments };
      setMessages(prev => [...prev, userMsg]);
      setIsLoading(true);
      
      // Handle Local Commands
      if (text.startsWith('/scan ')) {
          const symbol = text.replace('/scan ', '').toUpperCase();
          try {
              setAgentState(prev => ({ ...prev, isActive: true, currentAction: `Scanning ${symbol}...`, emotion: 'focused' }));
              const data = await MarketService.getPrice(symbol);
              if (data) {
                  let output = `### Market Analysis: ${symbol}\n\n`;
                  output += `**Price:** $${data.currentPrice.toLocaleString()} (${data.priceChange24h.toFixed(2)}%)\n`;
                  output += `**Source:** ${data.source}\n\n`;
                  
                  if (data.consensus) {
                      output += `**VERDICT: ${data.consensus.verdict}** (Score: ${data.consensus.score})\n\n`;
                      output += `**Top Factors:**\n${data.consensus.topFactors.map(f => `- ${f}`).join('\n')}\n\n`;
                  }
                  
                  if (data.activeSignals) {
                      output += `**Technical Signals:**\n`;
                      data.activeSignals.forEach(s => {
                          output += `- [${s.type}] **${s.name}**: ${s.description} (Strength: ${s.strength}%)\n`;
                      });
                  }
                  
                  setMessages(prev => [...prev, { id: Date.now().toString(), role: MessageRole.MODEL, text: output, timestamp: Date.now() }]);
                  setIsLoading(false);
                  setAgentState(prev => ({ ...prev, isActive: false, emotion: 'idle' }));
                  return;
              } else {
                  throw new Error(`Could not fetch data for ${symbol}`);
              }
          } catch (e: unknown) {
              const message = e instanceof Error ? e.message : String(e);
              setMessages(prev => [...prev, { id: Date.now().toString(), role: MessageRole.MODEL, text: `Scan failed: ${message}`, error: true, timestamp: Date.now() }]);
              setIsLoading(false);
              setAgentState(prev => ({ ...prev, isActive: false, emotion: 'focused' }));
              return;
          }
      }

      try {
        const history = messages.map(msg => ({ role: msg.role === MessageRole.MODEL ? 'model' : 'user', parts: [{ text: msg.text }] }));
        const agent = new AutonomousAgent(history, swarmAgents, (partial) => {
            setAgentState(prev => ({ ...prev, ...partial }));
        }, selectedModel, systemConfig, Object.keys(windows).filter(id => windows[id as WindowId].isOpen && !windows[id as WindowId].isMinimized));

        const response = await agent.run(text, attachments);
        setMessages(prev => [...prev, { id: Date.now().toString(), role: MessageRole.MODEL, text: response.text, timestamp: Date.now() }]);
      } catch (error: unknown) {
        const message = error instanceof Error ? error.message : String(error);
        setMessages(prev => [...prev, { id: Date.now().toString(), role: MessageRole.MODEL, text: `Error: ${message}`, error: true, timestamp: Date.now() }]);
      } finally { setIsLoading(false); }
    };

    const launchpadApps = Object.values(windows).map(win => ({
        id: win.id,
        title: win.title,
        icon: win.icon,
        label: win.title
    }));

    return (
        <ErrorBoundary>
        <ThemeContext.Provider value={{ theme, toggleTheme }}>
            <div className={`h-screen w-screen relative overflow-hidden transition-all duration-700 font-sans ${theme === 'dark' ? 'bg-[#020205] text-white' : 'bg-[#f5f5f7] text-zinc-900'}`} role="main" aria-label="Quant Nanggroe AI Dashboard">
            
            {/* WALLPAPER */}
            <div className="absolute inset-0 z-0 overflow-hidden">
                {theme === 'dark' ? (
                    <div className="absolute inset-0 bg-gradient-to-br from-[#020205] via-[#0a0a1a] to-[#020205]">
                        <div className="absolute top-[-10%] left-[-10%] w-[60%] h-[60%] rounded-full bg-blue-600/10 blur-[120px]"></div>
                        <div className="absolute bottom-[-10%] right-[-10%] w-[60%] h-[60%] rounded-full bg-emerald-600/10 blur-[120px]"></div>
                    </div>
                ) : (
                    <div className="absolute inset-0 bg-[#f5f5f7]">
                        <div className="absolute top-[-15%] left-[-15%] w-[70%] h-[70%] rounded-full bg-blue-400/20 blur-[150px]"></div>
                        <div className="absolute bottom-[-15%] right-[-15%] w-[70%] h-[70%] rounded-full bg-rose-300/10 blur-[150px]"></div>
                    </div>
                )}
                <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-[0.05] pointer-events-none"></div>
            </div>
            
            {/* TOP BAR */}
            <div className={`fixed top-0 left-0 w-full h-8 backdrop-blur-[40px] border-b flex items-center justify-between px-4 z-[9999] select-none text-[12px] font-medium transition-all duration-500 ${theme === 'dark' ? 'bg-black/30 border-white/5 text-white/90' : 'bg-white/60 border-black/5 text-zinc-800'}`} role="banner" aria-label="System top bar">
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-1.5 cursor-pointer hover:opacity-70 transition-opacity" onClick={() => setIsLaunchpadOpen(true)}>
                        <IconLogo className="w-4 h-4" />
                        <span className="font-bold">Nanggroe</span>
                    </div>
                    <div className="hidden md:flex items-center gap-4 opacity-70">
                        <span>Market</span>
                        <span>Swarm</span>
                        <span>Intelligence</span>
                    </div>
                </div>
                
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20">
                        <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                        <span className="text-[10px] text-emerald-500 font-bold uppercase tracking-wider">Swarm Active</span>
                    </div>
                    
                    <div className="flex items-center gap-3">
                        <button onClick={() => setIsOmniBarOpen(true)} className="hover:opacity-60 transition-opacity" aria-label="Open search command bar">
                            <IconSearch className="w-4 h-4" />
                        </button>
                        <button onClick={() => setIsControlCenterOpen(!isControlCenterOpen)} className="hover:opacity-60 transition-opacity" aria-label="Toggle control center">
                            <div className="flex flex-col gap-0.5 w-4">
                                <div className="h-[1.5px] w-full bg-current rounded-full" />
                                <div className="h-[1.5px] w-[70%] bg-current rounded-full self-center" />
                                <div className="h-[1.5px] w-full bg-current rounded-full" />
                            </div>
                        </button>
                        <div className="flex items-center gap-2 font-semibold">
                            <span>{currentTime.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* OVERLAYS */}
            <Launchpad isOpen={isLaunchpadOpen} onClose={() => setIsLaunchpadOpen(false)} apps={launchpadApps} onLaunch={(id) => focusWindow(id as WindowId)} />
            <ControlCenter isOpen={isControlCenterOpen} onClose={() => setIsControlCenterOpen(false)} />
            <OmniBar isOpen={isOmniBarOpen} onClose={() => setIsOmniBarOpen(false)} onCommand={(cmd) => handleSendMessage(cmd)} />
            <SystemUpdater currentVersion="15.3.0" />

            {/* WINDOWS */}
            <div className="relative w-full h-full pt-8 pb-20">
                {Object.values(windows).map(win => (
                <WindowFrame
                    key={win.id}
                    title={win.title}
                    icon={win.icon}
                    isOpen={win.isOpen}
                    isMinimized={win.isMinimized}
                    isActive={activeWindow === win.id}
                    zIndex={win.zIndex}
                    onClose={() => closeWindow(win.id)}
                    onMinimize={() => minimizeWindow(win.id)}
                    onFocus={() => focusWindow(win.id)}
                    defaultPosition={win.defaultPos}
                    defaultSize={win.defaultSize}
                >
                    {win.id === 'terminal' && (
                        <div className="flex flex-col h-full overflow-hidden">
                             <div className="flex-1 overflow-y-auto p-6 custom-scrollbar">
                                {messages.length === 0 ? (
                                    <div className="h-full flex flex-col items-center justify-center text-center opacity-20">
                                        <IconLogo className="w-24 h-24 mb-4" />
                                        <h2 className="text-2xl font-black uppercase tracking-tighter">Quant Nanggroe v15.3</h2>
                                    </div>
                                ) : (
                                    <div className="space-y-6 max-w-3xl mx-auto">
                                        {messages.map(msg => <ChatMessageComponent key={msg.id} message={msg} />)}
                                    </div>
                                )}
                             </div>
                             <InputArea onSendMessage={handleSendMessage} isLoading={isLoading} />
                        </div>
                    )}
                    {win.id === 'browser' && <BrowserWindow url={agentState.activeBrowserUrl} onNavigate={(url) => setAgentState(prev => ({ ...prev, activeBrowserUrl: url }))} />}
                    {win.id === 'trading_terminal' && <TradingTerminalWindow />}
                    {win.id === 'market' && <MarketWindow />}
                    {win.id === 'portfolio' && <PortfolioWindow />}
                    {win.id === 'monitor' && <AgentHud state={agentState} agents={swarmAgents} />}
                    {win.id === 'architecture' && <SystemArchitecture />}
                    {win.id === 'research' && <ResearchAgentWindow />}
                    {win.id === 'knowledge_base' && <KnowledgeBaseWindow />}
                    {win.id === 'nexus' && <NexusWindow isOpen={win.isOpen} onClose={() => closeWindow(win.id)} onMinimize={() => minimizeWindow(win.id)} onFocus={() => focusWindow(win.id)} isActive={activeWindow === win.id} zIndex={win.zIndex} />}
                    {win.id === 'settings' && <SwarmConfigModal agents={swarmAgents} config={systemConfig} onUpdateAgents={setSwarmAgents} onUpdateConfig={setSystemConfig} />}
                </WindowFrame>
                ))}
            </div>

            {/* DOCK */}
            <Taskbar windows={windows} onToggleWindow={toggleWindow} onStartClick={() => setIsLaunchpadOpen(true)} />
            </div>
        </ThemeContext.Provider>
        </ErrorBoundary>
    );
};


export default App;
