
import React, { useState, useRef, useEffect } from 'react';
import { IconSettings, IconBot, IconCode, IconBook, IconSearch, IconLogo, IconChart, IconBrowser, IconTerminal, IconBrain } from './Icons';
import { ThemeContext } from '../App';

interface Props {
  windows: Record<string, { isOpen: boolean; isMinimized: boolean; isActive: boolean }>;
  onToggleWindow: (id: string) => void;
  onStartClick: () => void;
}

const Taskbar: React.FC<Props> = ({ windows, onToggleWindow, onStartClick }) => {
    const { theme } = React.useContext(ThemeContext);
    const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
    const [mousePos, setMousePos] = useState<number | null>(null);
    const dockRef = useRef<HTMLDivElement>(null);

    const dockItems = [
        { id: 'terminal', icon: <IconCode className="w-4 h-4 text-[#00D1FF]" />, label: 'Neural Terminal' },
        { id: 'browser', icon: <IconBrowser className="w-4 h-4 text-[#FF3B30]" />, label: 'Explorer' },
        { id: 'trading_terminal', icon: <IconTerminal className="w-4 h-4 text-[#FFCC00]" />, label: 'Trading' },
        { id: 'market', icon: <IconChart className="w-4 h-4 text-[#34C759]" />, label: 'Market' },
        { id: 'portfolio', icon: <IconBook className="w-4 h-4 text-[#5856D6]" />, label: 'Portfolio' },
        { id: 'monitor', icon: <IconBot className="w-4 h-4 text-[#FF2D55]" />, label: 'Monitor' },
        { id: 'architecture', icon: <IconBrain className="w-4 h-4 text-[#10b981]" />, label: 'System' },
        { id: 'artifact', icon: <IconSearch className="w-4 h-4 text-[#AF52DE]" />, label: 'Research' },
        { id: 'settings', icon: <IconSettings className="w-4 h-4 text-[#8E8E93]" />, label: 'Settings' },
    ];

    const handleMouseMove = (e: React.MouseEvent) => {
        if (dockRef.current) {
            const rect = dockRef.current.getBoundingClientRect();
            setMousePos(e.clientX - rect.left);
        }
    };

    const getScale = (index: number) => {
        if (mousePos === null) return 1;
        const itemWidth = 52; 
        const itemCenter = index * itemWidth + itemWidth / 2 + 50; 
        const distance = Math.abs(mousePos - itemCenter);
        const maxDistance = 120;
        if (distance > maxDistance) return 1;
        return 1 + (0.4 * (1 - distance / maxDistance));
    };

    return (
      <div className="fixed bottom-4 w-full flex justify-center z-[10000] pointer-events-none">
          <div 
            className="pointer-events-auto"
            onMouseMove={handleMouseMove}
            onMouseLeave={() => { setMousePos(null); setHoveredIndex(null); }}
            ref={dockRef}
          >
              <div className={`px-3 py-1.5 rounded-[22px] flex items-end gap-1.5 transition-all duration-500 shadow-2xl border backdrop-blur-[50px] ${
                  theme === 'dark' ? 'bg-black/20 border-white/10' : 'bg-white/40 border-black/10'
              }`}>
                  
                  {/* Launchpad Icon */}
                  <div 
                    className="group relative flex flex-col items-center gap-1 shrink-0 transition-transform duration-200"
                    style={{ transform: `scale(${getScale(-1)})` }}
                  >
                        <button 
                            onClick={onStartClick}
                            className={`w-9 h-9 rounded-xl flex items-center justify-center transition-all border active:scale-90 ${
                                theme === 'dark' ? 'bg-gradient-to-br from-zinc-800 to-black border-white/10' : 'bg-gradient-to-br from-white to-zinc-100 border-black/5 shadow-sm'
                            }`}
                        >
                            <div className="grid grid-cols-3 gap-0.5">
                                {[...Array(9)].map((_, i) => <div key={i} className={`w-1 h-1 rounded-full ${theme === 'dark' ? 'bg-white/50' : 'bg-zinc-800/50'}`} />)}
                            </div>
                        </button>
                        <div className="h-1" />
                  </div>
    
                  <div className={`w-[1px] h-8 mx-1 mb-2 shrink-0 ${theme === 'dark' ? 'bg-white/10' : 'bg-black/10'}`}></div>
    
                  {/* App Icons */}
                  {dockItems.map((app, index) => {
                      const state = windows[app.id];
                      const isOpen = state?.isOpen;
                      const isActive = state?.isActive;
                      const scale = getScale(index);
                      
                      return (
                          <div 
                            key={app.id} 
                            className="group relative flex flex-col items-center gap-1 shrink-0"
                            style={{ 
                                transform: `scale(${scale}) translateY(${isActive ? '-4px' : '0'})`, 
                                transition: 'transform 0.2s cubic-bezier(0.23, 1, 0.32, 1)' 
                            }}
                          >
                                <button 
                                    onClick={() => onToggleWindow(app.id)}
                                    className={`w-9 h-9 rounded-xl flex items-center justify-center transition-all border active:scale-95 ${
                                        theme === 'dark' ? 'bg-black/40 border-white/5 hover:border-white/20' : 'bg-white/80 border-black/5 shadow-sm hover:bg-white'
                                    }`}
                                >
                                    {app.icon}
                                </button>
                                
                                {/* Indicator Dot */}
                                <div className="h-1 flex items-center justify-center">
                                  <div className={`w-1 h-1 rounded-full transition-all duration-500 ${
                                      isOpen ? (theme === 'dark' ? 'bg-white shadow-[0_0_8px_white]' : 'bg-zinc-800 shadow-[0_0_8px_rgba(0,0,0,0.3)]') : 'bg-transparent'
                                  }`}></div>
                                </div>
                                
                                {/* Tooltip */}
                                <div className={`absolute -top-10 left-1/2 -translate-x-1/2 px-2 py-1 backdrop-blur-xl border rounded-md text-[9px] font-bold opacity-0 group-hover:opacity-100 transition-all scale-90 group-hover:scale-100 whitespace-nowrap pointer-events-none ${
                                    theme === 'dark' ? 'bg-zinc-900/90 border-white/10 text-white' : 'bg-white/90 border-black/10 text-zinc-800'
                                }`}>
                                    {app.label}
                                </div>
                          </div>
                      );
                  })}
              </div>
          </div>
      </div>
    );
};

export default Taskbar;
