import React from 'react';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  text?: string;
}

const sizeMap = {
  sm: 'w-4 h-4',
  md: 'w-8 h-8',
  lg: 'w-12 h-12',
};

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ size = 'md', text }) => {
  return (
    <div role="status" aria-label={text || 'Loading'} className="flex flex-col items-center justify-center gap-3">
      <div
        className={`${sizeMap[size]} border-2 border-zinc-700 border-t-emerald-500 rounded-full animate-spin`}
        aria-hidden="true"
      />
      {text && (
        <>
          <span className="text-xs text-zinc-500 font-mono uppercase tracking-widest">{text}</span>
          <span className="sr-only">{text}</span>
        </>
      )}
    </div>
  );
};

export default LoadingSpinner;
