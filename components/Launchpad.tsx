
import React, { useState, useEffect } from 'react';
import { ThemeContext } from '../App';
import { IconSearch } from './Icons';

interface LaunchpadProps {
    isOpen: boolean;
    onClose: () => void;
    apps: { id: string; title: string; icon: React.ReactNode; label: string }[];
    onLaunch: (id: string) => void;
}

const Launchpad: React.FC<LaunchpadProps> = ({ isOpen, onClose, apps, onLaunch }) => {
    const { theme } = React.useContext(ThemeContext);
    const [search, setSearch] = useState('');
    const [isVisible, setIsVisible] = useState(false);

    useEffect(() => {
        if (isOpen) {
            setIsVisible(true);
        } else {
            const timer = setTimeout(() => setIsVisible(false), 300);
            return () => clearTimeout(timer);
        }
    }, [isOpen]);

    if (!isVisible) return null;

    const filteredApps = apps.filter(app => 
        app.label.toLowerCase().includes(search.toLowerCase()) || 
        app.title.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <div 
            className={`fixed inset-0 z-[10000] backdrop-blur-[50px] transition-all duration-500 flex flex-col items-center pt-[10vh] px-10 ${
                isOpen ? 'opacity-100 scale-100' : 'opacity-0 scale-110 pointer-events-none'
            } ${theme === 'dark' ? 'bg-black/30' : 'bg-white/30'}`}
            onClick={onClose}
        >
            {/* Search Bar */}
            <div 
                className={`w-[300px] mb-16 flex items-center px-4 py-1.5 rounded-lg border transition-all ${
                    theme === 'dark' ? 'bg-white/10 border-white/10 focus-within:border-white/20' : 'bg-black/5 border-black/10 focus-within:border-black/20'
                }`}
                onClick={(e) => e.stopPropagation()}
            >
                <IconSearch className="w-4 h-4 opacity-50 mr-2" />
                <input 
                    autoFocus
                    type="text"
                    placeholder="Search"
                    className="bg-transparent border-none outline-none w-full text-sm font-medium"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                />
            </div>

            {/* Apps Grid */}
            <div 
                className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 gap-x-8 gap-y-12 max-w-6xl w-full"
                onClick={(e) => e.stopPropagation()}
            >
                {filteredApps.map((app) => (
                    <button
                        key={app.id}
                        className="flex flex-col items-center group transition-all active:scale-95"
                        onClick={() => {
                            onLaunch(app.id);
                            onClose();
                        }}
                    >
                        <div className={`w-16 h-16 md:w-20 md:h-20 rounded-[22px] flex items-center justify-center shadow-xl border transition-all duration-300 group-hover:brightness-110 group-hover:scale-105 ${
                            theme === 'dark' ? 'bg-zinc-800/80 border-white/10' : 'bg-white/80 border-black/5 shadow-md'
                        }`}>
                            {React.cloneElement(app.icon as React.ReactElement, { className: 'w-10 h-10 md:w-12 md:h-12' })}
                        </div>
                        <span className={`mt-3 text-[13px] font-medium tracking-tight opacity-90 transition-opacity group-hover:opacity-100 ${
                            theme === 'dark' ? 'text-white' : 'text-zinc-900'
                        }`}>
                            {app.label}
                        </span>
                    </button>
                ))}
            </div>
        </div>
    );
};

export default Launchpad;
