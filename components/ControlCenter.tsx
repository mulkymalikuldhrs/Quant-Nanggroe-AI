
import React, { useRef } from 'react';
import { ThemeContext } from '../App';
import { IconSun, IconMoon, IconLogo, IconDatabase, IconActivity } from './Icons';
import { BackupService } from '../services/backup_service';

interface ControlCenterProps {
    isOpen: boolean;
    onClose: () => void;
}

const ControlCenter: React.FC<ControlCenterProps> = ({ isOpen, onClose }) => {
    const { theme, toggleTheme } = React.useContext(ThemeContext);
    const fileInputRef = useRef<HTMLInputElement>(null);

    if (!isOpen) return null;

    const handleBackup = async () => {
        await BackupService.exportToFile();
    };

    const handleRestore = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            const success = await BackupService.importFromFile(file);
            if (success) onClose();
        }
    };

    return (
        <>
            <div className="fixed inset-0 z-[9998]" onClick={onClose}></div>
            <div className={`fixed top-10 right-4 w-80 backdrop-blur-[40px] rounded-[24px] shadow-2xl border p-5 z-[9999] animate-in slide-in-from-top-4 duration-300 ${
                theme === 'dark' ? 'bg-zinc-900/70 border-white/10' : 'bg-white/70 border-black/5 shadow-zinc-300'
            }`}>
                <div className="grid grid-cols-2 gap-3 mb-4">
                    {/* Theme Toggle Button */}
                    <button 
                        onClick={toggleTheme}
                        className={`flex flex-col items-start p-3 rounded-2xl transition-all ${
                            theme === 'dark' ? 'bg-blue-600 text-white' : 'bg-zinc-200/50 text-zinc-800'
                        }`}
                    >
                        <div className={`w-7 h-7 rounded-full flex items-center justify-center mb-2 ${
                            theme === 'dark' ? 'bg-white/20' : 'bg-white shadow-sm'
                        }`}>
                            {theme === 'dark' ? <IconMoon className="w-4 h-4" /> : <IconSun className="w-4 h-4 text-amber-500" />}
                        </div>
                        <span className="text-[11px] font-bold">Theme</span>
                        <span className="text-[9px] opacity-70">{theme === 'dark' ? 'Dark Mode' : 'Light Mode'}</span>
                    </button>

                    {/* System Status Button */}
                    <div className={`flex flex-col items-start p-3 rounded-2xl ${
                        theme === 'dark' ? 'bg-zinc-800/50 text-white' : 'bg-zinc-200/50 text-zinc-800'
                    }`}>
                        <div className={`w-7 h-7 rounded-full flex items-center justify-center mb-2 bg-emerald-500 text-white`}>
                            <div className="w-2 h-2 rounded-full bg-white animate-pulse" />
                        </div>
                        <span className="text-[11px] font-bold">Network</span>
                        <span className="text-[9px] opacity-70">Connected</span>
                    </div>
                </div>

                {/* Storage Management (New in Hybrid Storage Update) */}
                <div className={`p-4 rounded-2xl mb-4 ${theme === 'dark' ? 'bg-zinc-800/50' : 'bg-zinc-100/50'}`}>
                    <div className="flex items-center justify-between mb-3">
                        <span className="text-[10px] font-black uppercase tracking-widest opacity-40">Storage Management</span>
                        <IconDatabase className="w-3 h-3 opacity-30" />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                        <button 
                            onClick={handleBackup}
                            className={`py-2 px-3 rounded-xl text-[10px] font-bold transition-all ${
                                theme === 'dark' ? 'bg-zinc-700 hover:bg-zinc-600 text-white' : 'bg-white hover:bg-zinc-50 text-zinc-800 border border-black/5'
                            }`}
                        >
                            Backup to File
                        </button>
                        <button 
                            onClick={() => fileInputRef.current?.click()}
                            className={`py-2 px-3 rounded-xl text-[10px] font-bold transition-all ${
                                theme === 'dark' ? 'bg-zinc-700 hover:bg-zinc-600 text-white' : 'bg-white hover:bg-zinc-50 text-zinc-800 border border-black/5'
                            }`}
                        >
                            Restore File
                        </button>
                        <input 
                            type="file" 
                            ref={fileInputRef} 
                            onChange={handleRestore} 
                            accept=".json" 
                            className="hidden" 
                        />
                    </div>
                    <p className="text-[8px] opacity-50 mt-2 text-center italic">Hybrid-Ready Storage Engine v1.0</p>
                </div>

                {/* Quick Actions */}
                <div className={`p-4 rounded-2xl flex items-center gap-4 ${theme === 'dark' ? 'bg-zinc-800/50' : 'bg-white shadow-sm'}`}>
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white shadow-lg">
                        <IconLogo className="w-6 h-6" />
                    </div>
                    <div className="flex flex-col">
                        <span className="text-[11px] font-bold">Quant Nanggroe AI</span>
                        <span className="text-[9px] opacity-60">v15.3.0 Advanced Intelligence</span>
                    </div>
                </div>

                {/* Institutional Metrics */}
                <div className={`mt-4 p-4 rounded-2xl ${theme === 'dark' ? 'bg-zinc-800/30' : 'bg-zinc-100/50'} border ${theme === 'dark' ? 'border-white/5' : 'border-black/5'}`}>
                    <div className="flex items-center justify-between mb-3">
                        <span className="text-[10px] font-black uppercase tracking-widest opacity-40">Security Matrix</span>
                        <div className="flex gap-1">
                            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div>
                            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500/30"></div>
                        </div>
                    </div>
                    <div className="space-y-2">
                        <div className="flex justify-between items-center text-[10px]">
                            <span className="opacity-60 italic">Risk Guardian</span>
                            <span className="font-mono text-emerald-500 font-bold">NOMINAL</span>
                        </div>
                        <div className="flex justify-between items-center text-[10px]">
                            <span className="opacity-60 italic">Data Integrity</span>
                            <span className="font-mono text-blue-500 font-bold">100%</span>
                        </div>
                        <div className="flex justify-between items-center text-[10px]">
                            <span className="opacity-60 italic">Neural Sync</span>
                            <span className="font-mono text-amber-500 font-bold">STABLE</span>
                        </div>
                    </div>
                </div>
            </div>
        </>
    );
};

export default ControlCenter;

