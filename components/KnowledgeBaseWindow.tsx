
import React, { useState, useEffect } from 'react';
import { KnowledgeBase } from '../services/knowledge_base';
import { VirtualDiskNode, KnowledgeItem } from '../types';
import { IconDatabase, IconBook, IconSearch, IconActivity } from './Icons';

export const KnowledgeBaseWindow: React.FC = () => {
    const [root, setRoot] = useState<VirtualDiskNode | null>(null);
    const [currentPath, setCurrentPath] = useState<string>('C:');
    const [selectedFile, setSelectedFile] = useState<KnowledgeItem | null>(null);

    useEffect(() => {
        const interval = setInterval(() => {
            const data = KnowledgeBase.getRoot();
            setRoot(data);
        }, 2000);
        return () => clearInterval(interval);
    }, []);

    const getCurrentNodes = () => {
        if (!root) return [];
        if (currentPath === 'C:') return root.children || [];
        
        const parts = currentPath.split('/').slice(1);
        let current = root;
        for (const part of parts) {
            const next = current.children?.find(c => c.name === part && c.type === 'folder');
            if (next) current = next;
            else break;
        }
        return current.children || [];
    };

    const navigate = (node: VirtualDiskNode) => {
        if (node.type === 'folder') {
            setCurrentPath(node.path);
        } else {
            const content = KnowledgeBase.readFile(node.path);
            setSelectedFile(content);
        }
    };

    const goBack = () => {
        if (currentPath === 'C:') return;
        const parts = currentPath.split('/');
        setCurrentPath(parts.slice(0, -1).join('/'));
    };

    return (
        <div className="flex h-full bg-[#05050a]/90 backdrop-blur-3xl text-white font-mono">
            {/* Sidebar */}
            <div className="w-64 border-r border-white/10 bg-black/40 p-4 flex flex-col gap-6">
                <div>
                    <h3 className="text-[10px] font-bold text-white/30 uppercase tracking-widest mb-4">Storage Devices</h3>
                    <div className="space-y-2">
                        <div className={`flex items-center gap-3 p-2 rounded-lg cursor-pointer transition-all ${currentPath.startsWith('C:') ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30' : 'hover:bg-white/5 opacity-50'}`} onClick={() => setCurrentPath('C:')}>
                            <IconDatabase className="w-4 h-4" />
                            <span className="text-xs font-bold">Local Disk (C:)</span>
                        </div>
                        <div className="flex items-center gap-3 p-2 rounded-lg opacity-20 cursor-not-allowed">
                            <IconDatabase className="w-4 h-4" />
                            <span className="text-xs font-bold">Network Drive (Z:)</span>
                        </div>
                    </div>
                </div>

                <div className="flex-1">
                    <h3 className="text-[10px] font-bold text-white/30 uppercase tracking-widest mb-4">Quick Access</h3>
                    <div className="space-y-1 text-[11px] opacity-60">
                        <div className="hover:text-blue-400 cursor-pointer py-1" onClick={() => setCurrentPath('C:/MARKET')}>/MARKET</div>
                        <div className="hover:text-blue-400 cursor-pointer py-1" onClick={() => setCurrentPath('C:/NEWS')}>/NEWS</div>
                        <div className="hover:text-blue-400 cursor-pointer py-1" onClick={() => setCurrentPath('C:/SENTIMENT')}>/SENTIMENT</div>
                        <div className="hover:text-blue-400 cursor-pointer py-1" onClick={() => setCurrentPath('C:/GEO')}>/GEO</div>
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <div className="flex-1 flex flex-col min-w-0">
                {/* Header */}
                <div className="h-14 border-b border-white/10 flex items-center px-6 justify-between bg-white/5">
                    <div className="flex items-center gap-4 text-xs">
                        <button onClick={goBack} className="opacity-50 hover:opacity-100 disabled:opacity-10" disabled={currentPath === 'C:'}>{"<"}</button>
                        <span className="text-white/40">{currentPath}</span>
                    </div>
                    <div className="flex items-center gap-2 bg-black/40 px-3 py-1.5 rounded-full border border-white/5 text-[10px]">
                        <IconSearch className="w-3 h-3 text-white/40" />
                        <input type="text" placeholder="Search Knowledge Base..." className="bg-transparent border-none outline-none w-40" />
                    </div>
                </div>

                {/* Explorer / Content */}
                <div className="flex-1 overflow-auto p-6">
                    {selectedFile ? (
                        <div className="max-w-4xl mx-auto space-y-6 animate-in fade-in slide-in-from-bottom-4">
                            <div className="flex items-center justify-between border-b border-white/10 pb-4">
                                <div className="flex items-center gap-3">
                                    <IconBook className="w-6 h-6 text-blue-400" />
                                    <div>
                                        <h2 className="text-xl font-bold">{selectedFile.path?.split('/').pop()}</h2>
                                        <p className="text-[10px] opacity-40 uppercase tracking-widest">{new Date(selectedFile.timestamp).toLocaleString()}</p>
                                    </div>
                                </div>
                                <button onClick={() => setSelectedFile(null)} className="text-xs text-blue-400 hover:underline">Back to Explorer</button>
                            </div>
                            <div className="bg-white/5 p-6 rounded-2xl border border-white/10 font-mono text-sm leading-relaxed whitespace-pre-wrap overflow-x-auto">
                                {selectedFile.content}
                            </div>
                            <div className="flex flex-wrap gap-2">
                                {selectedFile.tags.map(tag => (
                                    <span key={tag} className="px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-[10px] text-blue-400">#{tag}</span>
                                ))}
                            </div>
                        </div>
                    ) : (
                        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                            {getCurrentNodes().map(node => (
                                <div 
                                    key={node.id} 
                                    onClick={() => navigate(node)}
                                    className="group flex flex-col items-center gap-2 p-4 rounded-xl hover:bg-white/5 border border-transparent hover:border-white/10 transition-all cursor-pointer"
                                >
                                    <div className={`w-12 h-12 flex items-center justify-center rounded-lg shadow-lg ${node.type === 'folder' ? 'bg-blue-600/20 text-blue-400' : 'bg-emerald-600/20 text-emerald-400'}`}>
                                        {node.type === 'folder' ? (
                                            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" /></svg>
                                        ) : (
                                            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                                        )}
                                    </div>
                                    <span className="text-[11px] font-medium text-center truncate w-full opacity-80 group-hover:opacity-100">{node.name}</span>
                                </div>
                            ))}
                            {getCurrentNodes().length === 0 && (
                                <div className="col-span-full h-64 flex flex-col items-center justify-center opacity-20 border-2 border-dashed border-white/10 rounded-2xl">
                                    <IconActivity className="w-12 h-12 mb-4" />
                                    <span className="text-xs uppercase tracking-widest font-bold">Empty Directory</span>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
