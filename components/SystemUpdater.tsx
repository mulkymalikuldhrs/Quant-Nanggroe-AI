
import React, { useEffect, useState } from 'react';
import { IconDownload, IconCheck, IconShield, IconRefresh } from './Icons';

interface Props {
    currentVersion: string;
}

const SystemUpdater: React.FC<Props> = ({ currentVersion }) => {
    const [status, setStatus] = useState<'idle' | 'checking' | 'updating' | 'complete'>('idle');
    const [log, setLog] = useState('');

    useEffect(() => {
        // Auto-check on mount (Simulated "Always Update")
        const check = async () => {
            setStatus('checking');
            await new Promise(r => setTimeout(r, 2000));
            
            // Random chance to find an "update" to simulate living ecosystem
            if (Math.random() > 0.5) {
                setStatus('updating');
                setLog('New strategy algorithms detected from Dhaher Core...');
                await new Promise(r => setTimeout(r, 1500));
                setLog('Patching Quant OS logic...');
                await new Promise(r => setTimeout(r, 1500));
                setLog('Optimizing Neural Weights...');
                await new Promise(r => setTimeout(r, 1000));
                setStatus('complete');
            } else {
                setStatus('idle');
            }
        };
        const timer = setTimeout(check, 5000); // Check 5s after load
        return () => clearTimeout(timer);
    }, []);

    if (status === 'idle') return null;

    return (
        <div className="fixed top-12 right-4 z-[90] pointer-events-none">
            <div className="bg-white/90 backdrop-blur-md border border-gray-200 shadow-xl rounded-xl p-3 flex items-center gap-3 max-w-xs animate-in slide-in-from-right-10 fade-in duration-500">
                <div className="relative">
                    {status === 'complete' ? (
                        <div className="bg-green-100 p-2 rounded-full text-green-600"><IconCheck className="w-4 h-4" /></div>
                    ) : (
                        <div className="bg-blue-100 p-2 rounded-full text-blue-600 animate-spin"><IconRefresh className="w-4 h-4" /></div>
                    )}
                </div>
                <div>
                    <div className="text-xs font-bold text-gray-800">
                        {status === 'checking' && "Checking Registry..."}
                        {status === 'updating' && "System Auto-Update"}
                        {status === 'complete' && "System Up To Date"}
                    </div>
                    {(status === 'updating' || status === 'complete') && (
                        <div className="text-[10px] text-gray-500">{log || `Version ${currentVersion}`}</div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default SystemUpdater;
