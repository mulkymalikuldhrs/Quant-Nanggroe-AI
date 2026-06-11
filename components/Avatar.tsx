
import React from 'react';

interface Props {
  state: 'idle' | 'thinking' | 'speaking' | 'happy' | 'error' | 'curious' | 'frustrated' | 'confident';
  size?: number;
}

const Avatar: React.FC<Props> = ({ state, size = 64 }) => {
  // Simple Pixel Art generated via SVG rectangles
  
  const getColor = () => {
    switch(state) {
        case 'error': return '#ef4444'; // Red
        case 'frustrated': return '#f97316'; // Orange
        case 'thinking': return '#f59e0b'; // Amber
        case 'curious': return '#d946ef'; // Magenta
        case 'speaking': return '#3b82f6'; // Blue
        case 'happy': return '#10b981'; // Green
        case 'confident': return '#06b6d4'; // Cyan
        default: return '#64748b'; // Slate
    }
  };

  const primary = getColor();

  return (
    <div className="relative inline-block transition-colors duration-500" style={{ width: size, height: size }}>
      <svg viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg" className="w-full h-full drop-shadow-[0_0_10px_rgba(0,0,0,0.5)]">
        {/* Head Shape */}
        <path d="M4 2h8v2h2v8h-2v2H4v-2H2V4h2V2z" fill="#0f172a" />
        <path d="M4 3h8v1h2v8h-2v1H4v-1H2V4h2V3z" fill="#334155" opacity="0.6" />
        
        {/* Eyes */}
        {state === 'thinking' ? (
             // Thinking (One eye up, one down)
             <>
               <rect x="4" y="6" width="2" height="1" fill={primary} />
               <rect x="10" y="5" width="2" height="2" fill={primary} />
             </>
        ) : state === 'curious' ? (
             // Curious (One eye big, one small)
             <>
               <rect x="4" y="5" width="2" height="3" fill={primary} />
               <rect x="10" y="6" width="2" height="1" fill={primary} />
             </>
        ) : state === 'frustrated' ? (
             // Frustrated (Slanted angry eyes)
             <>
               <path d="M4 5h2v1H5v1H4V5z" fill={primary} />
               <path d="M10 5h2v1h-1v1h-1V5z" fill={primary} />
             </>
        ) : state === 'confident' ? (
            // Confident (Sunglasses / Solid bar)
            <>
               <rect x="4" y="6" width="3" height="2" fill={primary} />
               <rect x="9" y="6" width="3" height="2" fill={primary} />
               <rect x="7" y="7" width="2" height="1" fill={primary} opacity="0.5"/>
            </>
        ) : state === 'error' ? (
             // X Eyes
             <>
               <path d="M4 5h1v1h-1v-1zm1 1h-1v1h1v-1z M10 5h1v1h-1v-1zm1 1h-1v1h1v-1z" fill={primary} />
             </>
        ) : (
            // Normal Eyes (Blinking animation)
             <>
               <rect x="4" y="6" width="2" height="2" fill={primary} className="animate-pulse" />
               <rect x="10" y="6" width="2" height="2" fill={primary} className="animate-pulse" />
             </>
        )}

        {/* Mouth */}
        {state === 'speaking' ? (
             <rect x="6" y="11" width="4" height="2" fill="#fff">
                 <animate attributeName="height" values="1;3;1" dur="0.2s" repeatCount="indefinite" />
                 <animate attributeName="y" values="11;10;11" dur="0.2s" repeatCount="indefinite" />
             </rect>
        ) : state === 'happy' || state === 'confident' ? (
             <path d="M4 10h1v1h6v-1h1v2H4v-2z" fill="#fff" />
        ) : state === 'frustrated' ? (
             <rect x="6" y="11" width="4" height="1" fill="#fff" />
        ) : (
             <rect x="6" y="11" width="4" height="1" fill="#fff" />
        )}
      </svg>
      
      {/* Status Badge */}
      <div className={`absolute -bottom-1 -right-1 w-3 h-3 rounded-full border-2 border-black transition-colors duration-300 ${state === 'idle' ? 'bg-gray-500' : 'bg-' + primary}`} style={{backgroundColor: primary}}></div>
    </div>
  );
};

export default Avatar;
