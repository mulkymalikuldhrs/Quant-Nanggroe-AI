
import React, { useState, useEffect, useRef } from 'react';
import { IconSearch, IconTerminal, IconChart, IconBook, IconGlobe } from './Icons';
import { ThemeContext } from '../App';

interface Props {
    isOpen: boolean;
    onClose: () => void;
    onCommand: (cmd: string) => void;
}

const OmniBar: React.FC<Props> = ({ isOpen, onClose, onCommand }) => {
    const { theme } = React.useContext(ThemeContext);
    const [input, setInput] = useState('');
    const inputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        if (isOpen && inputRef.current) {
            inputRef.current.focus();
        }
    }, [isOpen]);

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter') {
            onCommand(input);
            setInput('');
            onClose();
        }
        if (e.key === 'Escape') onClose();
    };

    if (!isOpen) return null;

    return (
        <div className={`fixed inset-0 backdrop-blur-2xl z-[99999] flex items-start justify-center pt-[15vh] animate-in fade-in zoom-in-95 duration-200 p-4 ${theme === 'dark' ? 'bg-[#020205]/60' : 'bg-white/40'}`}>
            <div className={`w-[700px] max-w-full rounded-[32px] overflow-hidden flex flex-col scale-100 shadow-[0_32px_64px_-12px_rgba(0,0,0,0.4)] border transition-all duration-500 ${theme === 'dark' ? 'bg-[#121214]/80 border-white/10 shadow-black' : 'bg-white/90 border-black/5 shadow-zinc-400'}`}>
                <div className={`flex items-center px-8 py-6 border-b transition-colors duration-500 ${theme === 'dark' ? 'bg-white/5 border-white/5' : 'bg-black/5 border-black/5'}`}>
                    <IconSearch className={`w-6 h-6 mr-4 ${theme === 'dark' ? 'text-zinc-400' : 'text-zinc-500'}`} />
                    <input 
                        ref={inputRef}
                        type="text" 
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Search or enter command..."
                        className={`flex-1 text-2xl font-bold focus:outline-none tracking-tight bg-transparent ${theme === 'dark' ? 'text-zinc-100 placeholder-zinc-800' : 'text-zinc-800 placeholder-zinc-300'}`}
                    />
                    <div className="flex items-center gap-2">
                        <span className={`text-[9px] px-2 py-1 rounded font-bold tracking-widest border ${theme === 'dark' ? 'bg-white/10 text-zinc-400 border-white/5' : 'bg-black/5 text-zinc-500 border-black/5'}`}>CTRL+K</span>
                        <span className={`text-[9px] px-2 py-1 rounded font-bold tracking-widest border ${theme === 'dark' ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20' : 'bg-emerald-500 text-white border-emerald-600'}`}>READY</span>
                    </div>
                </div>
                
                <div className="p-6 bg-transparent">
                    <div className={`text-[9px] font-bold uppercase tracking-[0.2em] px-4 mb-4 opacity-50 ${theme === 'dark' ? 'text-zinc-500' : 'text-zinc-400'}`}>Intelligence Suggestions</div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {[
                            { cmd: "/scan BTCUSD", label: "Market Structure Pulse", icon: <IconChart className="text-emerald-500" /> },
                            { cmd: "Check global news impact", label: "Sentiment Analysis", icon: <IconGlobe className="text-blue-500" /> },
                            { cmd: "/exec long XAUUSD", label: "Execution Engine", icon: <IconTerminal className="text-amber-500" /> },
                            { cmd: "Optimize system performance", label: "System Core", icon: <IconBook className="text-purple-500" /> }
                        ].map((item, i) => (
                            <button 
                                key={i}
                                onClick={() => { onCommand(item.cmd); onClose(); }} 
                                className={`group flex items-center gap-4 px-5 py-4 rounded-2xl transition-all text-left border ${theme === 'dark' ? 'hover:bg-white/5 border-transparent hover:border-white/10' : 'hover:bg-black/5 border-transparent hover:border-black/10'}`}
                            >
                                <div className={`p-3 rounded-xl group-hover:scale-110 transition-transform border ${theme === 'dark' ? 'bg-white/5 border-white/5' : 'bg-black/5 border-black/5'}`}>
                                    {React.cloneElement(item.icon as React.ReactElement, { className: 'w-4 h-4 ' + (item.icon as any).props.className })}
                                </div>
                                <div className="flex flex-col">
                                    <span className={`text-[11px] font-bold tracking-tight ${theme === 'dark' ? 'text-zinc-100' : 'text-zinc-800'}`}>{item.label}</span>
                                    <span className={`text-[9px] font-mono opacity-50 ${theme === 'dark' ? 'text-zinc-500' : 'text-zinc-400'}`}>{item.cmd}</span>
                                </div>
                            </button>
                        ))}
                    </div>
                </div>

                <div className={`px-8 py-4 border-t flex justify-between items-center text-[9px] font-bold tracking-widest uppercase transition-colors duration-500 ${theme === 'dark' ? 'bg-white/5 border-white/5 text-zinc-600' : 'bg-black/5 border-black/5 text-zinc-400'}`}>
                    <span>NANGGROE AI v11.5</span>
                    <span className="text-emerald-500/50">SECURE CHANNEL ACTIVE</span>
                </div>
            </div>
        </div>
    );
};

export default OmniBar;
