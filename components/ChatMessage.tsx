
import React, { useContext } from 'react';
import { MessageRole, ChatMessage as ChatMessageType } from '../types';
import { IconBot, IconUser, IconLink, IconSearch, IconCode } from './Icons';
import { ThemeContext } from '../App';

interface Props {
  message: ChatMessageType;
}

const ChatMessage: React.FC<Props> = ({ message }) => {
    const { theme } = useContext(ThemeContext);
    const isModel = message.role === MessageRole.MODEL;

    const handleRunCode = (code: string) => {
        // SECURITY: Log code for review instead of executing arbitrary code
        console.warn("[SECURITY] Code execution blocked. Review the following code manually:", code);
    }

    const renderChart = (jsonString: string) => {
        try {
            const chartData = JSON.parse(jsonString);
            if (chartData.type !== 'chart') return null;
            
            const data = chartData.data as {label: string, value: number}[];
            const maxValue = Math.max(...data.map(d => d.value));
            
            return (
                <div className={`my-4 p-4 rounded-xl border shadow-sm transition-colors duration-500 ${theme === 'dark' ? 'bg-[#121214] border-white/5' : 'bg-white border-black/5 shadow-md'}`}>
                    <h4 className={`text-[9px] font-black uppercase mb-4 tracking-[0.2em] ${theme === 'dark' ? 'text-zinc-500' : 'text-zinc-400'}`}>{chartData.title || "Data Analysis"}</h4>
                    <div className={`flex items-end gap-2 h-40 pb-6 border-b ${theme === 'dark' ? 'border-white/5' : 'border-black/5'}`}>
                        {data.map((d, i) => {
                            const height = (d.value / maxValue) * 100;
                            return (
                                <div key={i} className="flex-1 flex flex-col items-center gap-2 group relative">
                                    <div 
                                      className="w-full bg-emerald-500/80 hover:bg-emerald-600 transition-all rounded-sm relative shadow-[0_0_15px_rgba(16,185,129,0.2)]" 
                                      style={{ height: `${height}%` }}
                                    >
                                        <span className={`absolute -top-6 left-1/2 -translate-x-1/2 text-[9px] font-mono font-bold opacity-0 group-hover:opacity-100 transition-opacity ${theme === 'dark' ? 'text-zinc-300' : 'text-zinc-600'}`}>
                                            {d.value}
                                        </span>
                                    </div>
                                    <span className={`absolute -bottom-6 text-[8px] font-black uppercase tracking-tighter truncate w-full text-center ${theme === 'dark' ? 'text-zinc-600' : 'text-zinc-400'}`}>{d.label}</span>
                                </div>
                            )
                        })}
                    </div>
                </div>
            );
        } catch (e) {
            return null;
        }
    }

    const renderContent = (text: string) => {
      const parts = text.split(/(```[\s\S]*?```)/g);
      
      return parts.map((part, index) => {
        if (part.startsWith('```') && part.endsWith('```')) {
          const content = part.slice(3, -3).replace(/^[a-z]+\n/, '');
          
          if (content.trim().startsWith('{') && content.includes('"type": "chart"')) {
              const chart = renderChart(content);
              if (chart) return <div key={index}>{chart}</div>;
          }

          return (
            <div key={index} className={`my-4 rounded-xl overflow-hidden border shadow-inner group transition-colors duration-500 ${theme === 'dark' ? 'bg-[#000]/40 border-white/5' : 'bg-zinc-100/50 border-black/5'}`}>
              <div className={`flex items-center justify-between px-4 py-1.5 border-b transition-colors duration-500 ${theme === 'dark' ? 'bg-white/5 border-white/5' : 'bg-black/5 border-black/5'}`}>
                 <span className={`text-[9px] font-black tracking-widest ${theme === 'dark' ? 'text-zinc-500' : 'text-zinc-400'}`}>NEURAL_KERNEL_LOG</span>
                        <button 
                    onClick={() => handleRunCode(content)}
                    aria-label="Copy code to clipboard"
                    className={`opacity-0 group-hover:opacity-100 flex items-center gap-1 text-[9px] font-black tracking-widest transition-all px-2 py-0.5 rounded shadow-sm border ${theme === 'dark' ? 'text-emerald-400 border-emerald-500/20 bg-emerald-500/5 hover:bg-emerald-500/10' : 'text-emerald-600 border-emerald-500/30 bg-white hover:bg-emerald-50'}`}
                 >
                     <IconCode className="w-3 h-3" /> REVIEW
                 </button>
              </div>
              <pre className={`p-4 overflow-x-auto text-[11px] font-mono custom-scrollbar ${theme === 'dark' ? 'text-zinc-300' : 'text-zinc-700'}`}>
                <code>{content}</code>
              </pre>
            </div>
          );
        }
        
        const boldParts = part.split(/(\*\*.*?\*\*)/g);
        return (
          <span key={index}>
            {boldParts.map((subPart, subIndex) => {
              if (subPart.startsWith('**') && subPart.endsWith('**')) {
                return <strong key={subIndex} className={`font-black uppercase tracking-tight ${theme === 'dark' ? 'text-zinc-100' : 'text-zinc-900'}`}>{subPart.slice(2, -2)}</strong>;
              }
              return subPart;
            })}
          </span>
        );
      });
    };

    return (
      <div className={`flex w-full mb-6 ${isModel ? 'justify-start' : 'justify-end'}`}>
        <div 
          className={`relative max-w-[90%] rounded-2xl p-5 transition-all duration-500 border ${
            isModel 
              ? (theme === 'dark' ? 'bg-[#121214] text-zinc-300 rounded-tl-none border-white/5' : 'bg-white text-zinc-700 rounded-tl-none border-black/5 shadow-md shadow-black/5') 
              : (theme === 'dark' ? 'bg-indigo-600 text-white rounded-tr-none border-indigo-500/50 shadow-lg shadow-indigo-600/20' : 'bg-indigo-500 text-white rounded-tr-none border-indigo-400 shadow-lg shadow-indigo-500/20')
          }`}
        >
          {/* Header */}
          <div className="flex items-center gap-2 mb-3">
             {isModel && (
                 <span className={`text-[9px] font-black uppercase tracking-[0.2em] ${theme === 'dark' ? 'text-zinc-500' : 'text-zinc-400'}`}>Neural_Synthetic_Response</span>
             )}
             {!isModel && (
                 <span className="text-[9px] font-black uppercase tracking-[0.2em] text-indigo-100 w-full text-right">User_Command</span>
             )}
          </div>
  
          {/* Attachments */}
          {message.attachments && message.attachments.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-4">
              {message.attachments.map((att, idx) => (
                 att.mimeType.startsWith('image') && (
                   <div key={idx} className="rounded-xl overflow-hidden border border-white/10 max-w-[240px] shadow-2xl">
                     <img src={`data:${att.mimeType};base64,${att.data}`} alt="attachment" className="w-full h-auto" />
                   </div>
                 )
              ))}
            </div>
          )}
  
          {/* Content */}
          <div className={`leading-relaxed text-[13px] font-medium ${isModel ? (theme === 'dark' ? 'text-zinc-300' : 'text-zinc-700') : 'text-white'}`}>
            {message.error ? (
              <div className="text-red-500 bg-red-500/5 border border-red-500/20 p-3 rounded-xl font-mono text-[11px]">
                KERNEL_PANIC: {message.text}
              </div>
            ) : (
              renderContent(message.text)
            )}
          </div>
  
          {/* Sources */}
          {message.groundingSources && message.groundingSources.length > 0 && (
            <div className={`mt-5 pt-4 border-t ${theme === 'dark' ? 'border-white/5' : 'border-black/5'}`}>
              <div className={`flex items-center gap-2 mb-3 text-[9px] font-black uppercase tracking-widest ${theme === 'dark' ? 'text-emerald-400' : 'text-emerald-600'}`}>
                <IconSearch className="w-3 h-3" />
                <span>Verified_Neural_Source</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {message.groundingSources.map((source, idx) => (
                  <a
                    key={idx}
                    href={source.uri}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-xl border transition-all text-[10px] font-black uppercase tracking-tighter ${theme === 'dark' ? 'bg-white/5 border-white/5 hover:bg-white/10 text-zinc-400 hover:text-white' : 'bg-black/5 border-black/5 hover:bg-black/10 text-zinc-600 hover:text-zinc-900 shadow-sm'}`}
                  >
                    <IconLink className="w-3 h-3 opacity-60" />
                    <span className="truncate max-w-[140px]">{source.title}</span>
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

  );
};

export default ChatMessage;
