
import React, { useState } from 'react';
import { SwarmAgent, SystemConfiguration, ApiKeys, DataSource } from '../types';
import { BrowserFS } from '../services/file_system';
import { IconTrash, IconPlus, IconGlobe, IconCheck } from './Icons';

interface Props {
  agents: SwarmAgent[];
  config: SystemConfiguration;
  onUpdateAgents: (agents: SwarmAgent[]) => void;
  onUpdateConfig: (config: SystemConfiguration) => void;
}

const SwarmConfigModal: React.FC<Props> = ({ agents, config, onUpdateAgents, onUpdateConfig }) => {
  const [editingConfig, setEditingConfig] = useState<SystemConfiguration>({ ...config });
  const [activeTab, setActiveTab] = useState<'keys' | 'system' | 'data'>('keys');
  
  const [dataSources, setDataSources] = useState<DataSource[]>(BrowserFS.getDataSources());
  const [newSource, setNewSource] = useState<Partial<DataSource>>({ category: 'market', type: 'api' });
  const [showAddSource, setShowAddSource] = useState(false);

  const handleApiKeyChange = (provider: keyof ApiKeys, value: string) => {
      setEditingConfig(prev => ({
          ...prev,
          apiKeys: { ...prev.apiKeys, [provider]: value }
      }));
  };

  const toggleConfig = (key: keyof SystemConfiguration) => {
      // @ts-ignore
      setEditingConfig(prev => ({ ...prev, [key]: !prev[key] }));
  }

  const handleSave = () => {
    onUpdateConfig(editingConfig);
  };

  const handleAddSource = () => {
      if (!newSource.name || !newSource.endpoint) return;
      const sourceToAdd: DataSource = {
          id: `src-${Date.now()}`,
          name: newSource.name,
          endpoint: newSource.endpoint,
          category: newSource.category as any || 'market',
          type: newSource.type as any || 'api',
          description: newSource.description || 'Custom User Source',
          status: 'active'
      };
      BrowserFS.addDataSource(sourceToAdd);
      setDataSources(BrowserFS.getDataSources());
      setShowAddSource(false);
      setNewSource({ category: 'market', type: 'api' });
  };

  const handleRemoveSource = (id: string) => {
      BrowserFS.removeDataSource(id);
      setDataSources(BrowserFS.getDataSources());
  };

  return (
    <div className="w-full h-full flex flex-col bg-gray-50/50">
        <div className="flex-none px-4 py-2 border-b border-gray-200 bg-white">
            <div className="flex gap-6">
                {['keys', 'data', 'system'].map(tab => (
                    <button 
                        key={tab}
                        onClick={() => setActiveTab(tab as any)} 
                        className={`text-xs font-semibold py-2 border-b-2 capitalize transition-colors ${activeTab === tab ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-400 hover:text-gray-600'}`}
                    >
                        {tab === 'data' ? 'Data Sources' : tab === 'keys' ? 'LLM Keys' : tab}
                    </button>
                ))}
            </div>
        </div>
        
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
            
            {/* LLM KEYS TAB */}
            {activeTab === 'keys' && (
                <div className="space-y-6">
                    <div className="bg-blue-50 border border-blue-100 p-3 rounded-xl">
                        <h3 className="text-blue-700 font-bold text-xs mb-1">🧠 Intelligence Core</h3>
                        <p className="text-[10px] text-blue-600/80">Configure your Reasoning Engines (LLMs). Keys are stored locally.</p>
                    </div>

                    <div className="space-y-1.5">
                         <label className="text-xs font-bold text-gray-700 flex justify-between items-center">
                             LLM7 Token
                             {editingConfig.apiKeys.llm7 ? (
                                <span className="text-[9px] bg-green-100 text-green-700 border border-green-200 px-2 py-0.5 rounded-full uppercase font-bold tracking-wide">Premium Active</span>
                             ) : (
                                <span className="text-[9px] bg-gray-100 text-gray-500 border border-gray-200 px-2 py-0.5 rounded-full uppercase font-bold tracking-wide">Free Tier</span>
                             )}
                         </label>
                         <input 
                             type="password" 
                             value={editingConfig.apiKeys.llm7 || ''}
                             onChange={(e) => handleApiKeyChange('llm7', e.target.value)}
                             className="w-full bg-white border border-gray-300 rounded-lg p-2 text-gray-800 font-mono text-[11px] focus:border-blue-500 focus:ring-2 focus:ring-blue-100 focus:outline-none transition-all"
                             placeholder="sk-..."
                         />
                    </div>

                    {[
                        { id: 'google', label: 'Google Gemini', desc: 'Required for Search Grounding.' },
                        { id: 'groq', label: 'Groq API', desc: 'Optional: High-speed Llama 3.' },
                        { id: 'openai', label: 'OpenAI API', desc: 'Optional: Legacy support.' },
                    ].map(provider => (
                        <div key={provider.id} className="space-y-1.5">
                            <label className="text-xs font-bold text-gray-700">{provider.label}</label>
                            <input 
                                type="password" 
                                value={editingConfig.apiKeys[provider.id as keyof ApiKeys] || ''}
                                onChange={(e) => handleApiKeyChange(provider.id as keyof ApiKeys, e.target.value)}
                                className="w-full bg-white border border-gray-300 rounded-lg p-2 text-gray-800 font-mono text-[11px] focus:border-blue-500 focus:ring-2 focus:ring-blue-100 focus:outline-none transition-all"
                                placeholder={`Enter ${provider.label} Key`}
                            />
                        </div>
                    ))}
                </div>
            )}

            {/* DATA SOURCES TAB */}
            {activeTab === 'data' && (
                <div className="space-y-6">
                    <div className="bg-orange-50 border border-orange-100 p-3 rounded-xl flex justify-between items-start">
                        <div>
                            <h3 className="text-orange-700 font-bold text-xs mb-1">📊 Market Data & Feeds</h3>
                            <p className="text-[10px] text-orange-600/80">Manage public APIs and data streams available to the Swarm.</p>
                        </div>
                        <button 
                            onClick={() => setShowAddSource(!showAddSource)}
                            className="bg-white border border-orange-200 text-orange-600 p-1.5 rounded-lg hover:bg-orange-100 transition-colors shadow-sm"
                        >
                            <IconPlus className="w-4 h-4" />
                        </button>
                    </div>

                    {showAddSource && (
                        <div className="bg-white border border-gray-200 p-3 rounded-xl shadow-sm space-y-2 animate-in fade-in slide-in-from-top-2">
                            <h4 className="text-xs font-bold text-gray-800 mb-2">Add Custom Source</h4>
                            <div className="grid grid-cols-2 gap-2">
                                <input 
                                    type="text" 
                                    placeholder="Source Name" 
                                    className="border border-gray-200 rounded p-1.5 text-[10px] w-full"
                                    value={newSource.name || ''}
                                    onChange={e => setNewSource({...newSource, name: e.target.value})}
                                />
                                <select 
                                    className="border border-gray-200 rounded p-1.5 text-[10px] w-full"
                                    value={newSource.category}
                                    onChange={e => setNewSource({...newSource, category: e.target.value as any})}
                                >
                                    <option value="market">Market</option>
                                    <option value="news">News</option>
                                    <option value="macro">Macro</option>
                                    <option value="onchain">On-Chain</option>
                                </select>
                            </div>
                            <input 
                                type="text" 
                                placeholder="Endpoint URL" 
                                className="border border-gray-200 rounded p-1.5 text-[10px] w-full"
                                value={newSource.endpoint || ''}
                                onChange={e => setNewSource({...newSource, endpoint: e.target.value})}
                            />
                            <div className="flex justify-end gap-2 mt-2">
                                <button onClick={() => setShowAddSource(false)} className="text-[10px] text-gray-500 hover:text-gray-700">Cancel</button>
                                <button onClick={handleAddSource} className="bg-orange-500 hover:bg-orange-600 text-white px-3 py-1 rounded text-[10px] font-bold">Add Source</button>
                            </div>
                        </div>
                    )}

                    <div className="space-y-3 pt-2">
                        <h4 className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Premium Providers</h4>
                        {[
                            { id: 'polygon', label: 'Polygon.io', desc: 'Stocks/Options/Crypto' },
                            { id: 'alphaVantage', label: 'Alpha Vantage', desc: 'Stocks/Forex' },
                            { id: 'finnhub', label: 'Finnhub.io', desc: 'News/Sentiment' },
                            { id: 'fred', label: 'FRED', desc: 'Macro Economics' },
                        ].map(provider => (
                            <div key={provider.id} className="flex items-center gap-2">
                                <div className="w-24 shrink-0">
                                    <label className="text-[10px] font-bold text-gray-700">{provider.label}</label>
                                    <p className="text-[8px] text-gray-400">{provider.desc}</p>
                                </div>
                                <input 
                                    type="password" 
                                    value={editingConfig.apiKeys[provider.id as keyof ApiKeys] || ''}
                                    onChange={(e) => handleApiKeyChange(provider.id as keyof ApiKeys, e.target.value)}
                                    className="flex-1 bg-white border border-gray-300 rounded-lg p-1.5 text-gray-800 font-mono text-[10px] focus:border-blue-500 focus:outline-none"
                                    placeholder="Enter Key..."
                                />
                            </div>
                        ))}
                    </div>

                    <div className="space-y-2 pt-2">
                        <h4 className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Active Registry ({dataSources.length})</h4>
                        <div className="space-y-2 max-h-[200px] overflow-y-auto custom-scrollbar p-1">
                            {dataSources.map(source => (
                                <div key={source.id} className="group bg-white border border-gray-200 p-2 rounded-lg flex items-center justify-between hover:shadow-sm transition-shadow">
                                    <div className="flex items-center gap-2 overflow-hidden">
                                        <div className={`p-1 rounded ${source.type === 'api' ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-600'}`}>
                                            <IconGlobe className="w-3 h-3" />
                                        </div>
                                        <div className="min-w-0">
                                            <div className="text-[10px] font-bold text-gray-800 truncate">{source.name}</div>
                                            <div className="text-[9px] text-gray-400 truncate max-w-[200px]">{source.endpoint}</div>
                                        </div>
                                    </div>
                                    <button 
                                        onClick={() => handleRemoveSource(source.id)}
                                        className="text-gray-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-all p-1"
                                    >
                                        <IconTrash className="w-3 h-3" />
                                    </button>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}

            {/* SYSTEM TAB */}
            {activeTab === 'system' && (
                 <div className="grid grid-cols-1 gap-3">
                    {[
                        { key: 'enableAutoLearning', label: 'Neural Evolution (ML)', desc: 'Automatically adjust strategy weights based on Profit/Loss history.' },
                        { key: 'enableSelfHealing', label: 'Self-Healing Protocol', desc: 'Automatically recover from API errors.' },
                        { key: 'enableAutoSwitch', label: 'Provider Auto-Switch', desc: 'Failover to backup LLMs if primary fails.' },
                        { key: 'enableDynamicTools', label: 'Dynamic Tooling', desc: 'Allow agents to request new capabilities.' },
                        { key: 'enableVoiceResponse', label: 'Vocal Interface (TTS)', desc: 'Alpha Prime will speak the final report.' },
                    ].map(item => (
                        <div key={item.key} className="bg-white border border-gray-200 rounded-xl p-4 flex items-center justify-between shadow-sm">
                             <div>
                                 <h3 className="font-bold text-gray-800 text-xs">{item.label}</h3>
                                 <p className="text-[10px] text-gray-500">{item.desc}</p>
                             </div>
                             <button 
                                onClick={() => toggleConfig(item.key as any)} 
                                className={`px-3 py-1 rounded-lg text-[10px] font-bold transition-all shadow-sm ${
                                    // @ts-ignore
                                    editingConfig[item.key] 
                                    ? 'bg-green-500 text-white shadow-green-200' 
                                    : 'bg-gray-100 text-gray-400'
                                }`}
                             >
                                 {/* @ts-ignore */}
                                 {editingConfig[item.key] ? 'ENABLED' : 'OFF'}
                             </button>
                        </div>
                    ))}
                 </div>
            )}
        </div>

        <div className="flex-none p-4 border-t border-gray-200 bg-white flex justify-end rounded-b-xl">
            <button onClick={handleSave} className="px-5 py-2 bg-[#007AFF] hover:bg-blue-600 text-white rounded-lg text-xs font-bold shadow-md shadow-blue-200 transition-all transform hover:scale-105 active:scale-95">
                Save System Config
            </button>
        </div>
    </div>
  );
};

export default SwarmConfigModal;
