
import React, { useState, useEffect, useRef } from 'react';
import { ThemeContext } from '../App';

interface WindowFrameProps {
  title: string;
  isOpen: boolean;
  isMinimized: boolean;
  isActive: boolean;
  zIndex: number;
  onClose: () => void;
  onMinimize: () => void;
  onFocus: () => void;
  defaultPosition?: { x: number; y: number };
  defaultSize?: { width: number; height: number };
  icon?: React.ReactNode;
  children: React.ReactNode;
}

const WindowFrame: React.FC<WindowFrameProps> = ({
  title,
  isOpen,
  isMinimized,
  isActive,
  zIndex,
  onClose,
  onMinimize,
  onFocus,
  defaultPosition = { x: 100, y: 100 },
  defaultSize = { width: 700, height: 500 },
  icon,
  children
}) => {
    const { theme } = React.useContext(ThemeContext);
    const [position, setPosition] = useState(defaultPosition);
    const [size, setSize] = useState(defaultSize);
    const [isMaximized, setIsMaximized] = useState(false);
    const [preMaxSize, setPreMaxSize] = useState(defaultSize);
    const [preMaxPos, setPreMaxPos] = useState(defaultPosition);
    
    const [isDragging, setIsDragging] = useState(false);
    const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
    const windowRef = useRef<HTMLDivElement>(null);

    // Position and size are initialized from defaultPosition/defaultSize on mount
    // We removed the useEffect that resets them on every prop change to allow user persistence

    const handleMouseDown = (e: React.MouseEvent) => {
        if (isMaximized) return;
        onFocus();
        if (windowRef.current) {
            setIsDragging(true);
            setDragOffset({
                x: e.clientX - position.x,
                y: e.clientY - position.y
            });
        }
    };

    useEffect(() => {
        const handleMouseMove = (e: MouseEvent) => {
            if (isDragging) {
                setPosition({
                    x: e.clientX - dragOffset.x,
                    y: e.clientY - dragOffset.y
                });
            }
        };
        const handleMouseUp = () => setIsDragging(false);

        if (isDragging) {
            document.addEventListener('mousemove', handleMouseMove);
            document.addEventListener('mouseup', handleMouseUp);
        }
        return () => {
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
        };
    }, [isDragging, dragOffset]);

    const toggleMaximize = () => {
        onFocus();
        if (isMaximized) {
            setSize(preMaxSize);
            setPosition(preMaxPos);
        } else {
            setPreMaxSize(size);
            setPreMaxPos(position);
            setPosition({ x: 0, y: 32 });
            setSize({ width: window.innerWidth, height: window.innerHeight - 32 });
        }
        setIsMaximized(!isMaximized);
    };

    if (!isOpen || isMinimized) return null;

    return (
        <div 
            ref={windowRef}
            className={`fixed flex flex-col rounded-[12px] overflow-hidden backdrop-blur-[50px] transition-all duration-500 shadow-2xl ${
                isActive ? 'z-[100] scale-100 ring-1 ring-white/20' : 'opacity-95 scale-[0.99] grayscale-[0.2]'
            } ${theme === 'dark' ? 'bg-[#1e1e1e]/80 border-white/10' : 'bg-white/80 border-black/10'}`}
            style={{
                left: position.x,
                top: position.y,
                width: size.width,
                height: size.height,
                zIndex: zIndex,
            }}
            onMouseDown={onFocus}
        >
            {/* macOS Title Bar */}
            <div 
                className={`h-10 flex items-center px-4 cursor-grab active:cursor-grabbing select-none relative transition-colors duration-500 ${
                    theme === 'dark' ? 'bg-white/5 border-b border-white/5' : 'bg-black/5 border-b border-black/5'
                }`}
                onMouseDown={handleMouseDown}
                onDoubleClick={toggleMaximize}
            >
                {/* Traffic Lights */}
                <div className="flex items-center gap-2 group/lights">
                    <button 
                        onClick={(e) => { e.stopPropagation(); onClose(); }} 
                        className="w-3 h-3 rounded-full bg-[#ff5f57] border border-black/10 flex items-center justify-center transition-all hover:brightness-90 active:brightness-75"
                    >
                        <span className="text-[10px] text-black/50 opacity-0 group-hover/lights:opacity-100 pointer-events-none mt-[-1px]">×</span>
                    </button>
                    <button 
                        onClick={(e) => { e.stopPropagation(); onMinimize(); }} 
                        className="w-3 h-3 rounded-full bg-[#febc2e] border border-black/10 flex items-center justify-center transition-all hover:brightness-90 active:brightness-75"
                    >
                        <span className="text-[10px] text-black/50 opacity-0 group-hover/lights:opacity-100 pointer-events-none mt-[-4px]">−</span>
                    </button>
                    <button 
                        onClick={(e) => { e.stopPropagation(); toggleMaximize(); }} 
                        className="w-3 h-3 rounded-full bg-[#28c840] border border-black/10 flex items-center justify-center transition-all hover:brightness-90 active:brightness-75"
                    >
                        <span className="text-[6px] text-black/50 opacity-0 group-hover/lights:opacity-100 pointer-events-none">+</span>
                    </button>
                </div>

                {/* Title */}
                <div className="flex-1 flex items-center justify-center gap-2 pr-12">
                    {icon && <div className="opacity-70">{icon}</div>}
                    <span className={`text-[12px] font-bold tracking-tight opacity-70 ${theme === 'dark' ? 'text-white' : 'text-zinc-800'}`}>
                        {title}
                    </span>
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-auto custom-scrollbar relative">
                {children}
            </div>

            {/* Resize handle */}
            {!isMaximized && (
                <div 
                    className="absolute bottom-0 right-0 w-4 h-4 cursor-se-resize z-[110]"
                    onMouseDown={(e) => {
                        e.stopPropagation();
                        e.preventDefault();
                        const startX = e.clientX;
                        const startY = e.clientY;
                        const startWidth = size.width;
                        const startHeight = size.height;
                        const handleMouseMove = (moveEvent: MouseEvent) => {
                            setSize({
                                width: Math.max(300, startWidth + moveEvent.clientX - startX),
                                height: Math.max(200, startHeight + moveEvent.clientY - startY)
                            });
                        };
                        const handleMouseUp = () => {
                            document.removeEventListener('mousemove', handleMouseMove);
                            document.removeEventListener('mouseup', handleMouseUp);
                        };
                        document.addEventListener('mousemove', handleMouseMove);
                        document.addEventListener('mouseup', handleMouseUp);
                    }}
                />
            )}
        </div>
    );
};

export default WindowFrame;
