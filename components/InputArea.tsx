
import React, { useState, useRef, useEffect, useContext } from 'react';
import { IconSend, IconPaperclip, IconX } from './Icons';
import { Attachment } from '../types';
import { ThemeContext } from '../App';

interface Props {
  onSendMessage: (text: string, attachments: Attachment[]) => void;
  isLoading: boolean;
}

const InputArea: React.FC<Props> = ({ onSendMessage, isLoading }) => {
    const { theme } = useContext(ThemeContext);
    const [input, setInput] = useState('');
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    if ((input.trim() || attachments.length > 0) && !isLoading) {
      onSendMessage(input.trim(), attachments);
      setInput('');
      setAttachments([]);
      if (textareaRef.current) textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      const reader = new FileReader();
      
      reader.onload = (event) => {
        if (event.target?.result) {
          const base64String = (event.target.result as string).split(',')[1];
          const newAttachment: Attachment = {
            mimeType: file.type,
            data: base64String,
            name: file.name
          };
          setAttachments(prev => [...prev, newAttachment]);
        }
      };
      
      reader.readAsDataURL(file);
    }
  };

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [input]);

    return (
      <div className={`w-full px-4 pb-4 pt-2 transition-colors duration-500 border-t ${theme === 'dark' ? 'bg-[#09090b]/40 backdrop-blur-md border-white/5' : 'bg-white/40 backdrop-blur-md border-black/5'}`}>
        
        {/* Attachment Previews */}
        {attachments.length > 0 && (
            <div className="flex gap-2 mb-2 overflow-x-auto">
                {attachments.map((att, idx) => (
                    <div key={idx} className={`relative group border rounded-lg p-1.5 shadow-sm flex items-center gap-2 ${theme === 'dark' ? 'bg-[#121214] border-white/10' : 'bg-white border-black/5'}`}>
                        <div className={`w-8 h-8 rounded flex items-center justify-center text-[8px] font-bold ${theme === 'dark' ? 'bg-black/20 text-zinc-500' : 'bg-zinc-100 text-zinc-500'}`}>
                             FILE
                        </div>
                        <span className={`text-[10px] truncate max-w-[80px] ${theme === 'dark' ? 'text-zinc-300' : 'text-zinc-700'}`}>{att.name}</span>
                        <button 
                          onClick={() => setAttachments(prev => prev.filter((_, i) => i !== idx))}
                          className="absolute -top-1 -right-1 bg-red-500 rounded-full p-0.5 text-white shadow-md opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                            <IconX className="w-2 h-2" />
                        </button>
                    </div>
                ))}
            </div>
        )}

        <div className="relative group">
          <form 
            onSubmit={handleSubmit}
            className={`relative flex items-end gap-2 border rounded-2xl p-1.5 transition-all shadow-sm ${theme === 'dark' ? 'bg-black/40 border-white/10 focus-within:ring-2 focus-within:ring-indigo-500/20 focus-within:border-indigo-500/50' : 'bg-white/80 border-black/5 shadow-md focus-within:ring-2 focus-within:ring-indigo-500/20 focus-within:border-indigo-400'}`}
          >
            {/* File Button */}
            <div className="pb-1 pl-1">
                <input 
                   type="file" 
                   ref={fileInputRef} 
                   onChange={handleFileSelect} 
                   className="hidden" 
                   accept="image/*,text/*,application/json,application/pdf"
                />
                <button 
                  type="button" 
                  onClick={() => fileInputRef.current?.click()}
                  className={`w-8 h-8 rounded-full flex items-center justify-center transition-colors ${theme === 'dark' ? 'hover:bg-white/5 text-zinc-500 hover:text-zinc-300' : 'hover:bg-black/5 text-zinc-400 hover:text-zinc-600'}`}
                  title="Attach File"
                  aria-label="Attach a file"
                >
                    <IconPaperclip className="w-4 h-4" />
                </button>
            </div>
            
            <div className="flex-1 min-w-0">
               <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask Quant Nanggroe..."
                disabled={isLoading}
                rows={1}
                aria-label="Chat message input"
                className={`w-full bg-transparent text-sm py-2 px-1 resize-none focus:outline-none transition-colors ${theme === 'dark' ? 'text-zinc-100 placeholder-zinc-600' : 'text-zinc-800 placeholder-zinc-400'}`}
              />
            </div>

            <button
              type="submit"
              disabled={(!input.trim() && attachments.length === 0) || isLoading}
              aria-label="Send message"
              className={`w-8 h-8 rounded-full flex items-center justify-center mb-0.5 transition-all duration-300 ${
                (input.trim() || attachments.length > 0) && !isLoading
                  ? (theme === 'dark' ? 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/20 scale-105' : 'bg-indigo-500 hover:bg-indigo-600 text-white shadow-lg shadow-indigo-500/20 scale-105')
                  : (theme === 'dark' ? 'bg-zinc-800/50 text-zinc-600 cursor-not-allowed' : 'bg-zinc-100 text-zinc-300 cursor-not-allowed')
              }`}
            >
               <IconSend className="w-3.5 h-3.5 ml-0.5" />
            </button>
          </form>
        </div>
      </div>

  );
};

export default InputArea;
