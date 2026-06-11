
import React, { useEffect, useState } from 'react';
import { Artifact } from '../types';

interface Props {
  artifact?: Artifact;
}

const ArtifactWindow: React.FC<Props> = ({ artifact }) => {
  const [key, setKey] = useState(0);

  useEffect(() => {
    // Force re-render iframe on artifact change
    if (artifact) setKey(prev => prev + 1);
  }, [artifact]);

  if (!artifact) {
      return (
          <div className="h-full w-full flex flex-col items-center justify-center text-gray-500 bg-[#050505]">
              <div className="w-12 h-12 rounded-full border border-white/10 flex items-center justify-center mb-2 animate-pulse">
                  <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
              </div>
              <p className="text-xs">Waiting for Neural Artifact...</p>
              <p className="text-[9px] opacity-50 mt-1">Ask the Swarm to "Write a game" or "Create an app"</p>
          </div>
      );
  }

  return (
    <div className="h-full w-full flex flex-col bg-white">
        <div className="flex-none bg-gray-100 border-b border-gray-200 px-4 py-2 flex items-center justify-between">
            <div className="flex items-center gap-2">
                <div className="flex gap-1.5">
                    <div className="w-2.5 h-2.5 rounded-full bg-red-400"></div>
                    <div className="w-2.5 h-2.5 rounded-full bg-amber-400"></div>
                    <div className="w-2.5 h-2.5 rounded-full bg-green-400"></div>
                </div>
                <div className="ml-3 bg-white px-3 py-1 rounded-md text-[10px] text-gray-500 border border-gray-200 shadow-sm w-64 truncate">
                    preview://{artifact.id}.html
                </div>
            </div>
            <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Live Preview</span>
        </div>
        <div className="flex-1 relative">
            <iframe
                key={key}
                srcDoc={artifact.content}
                title="Artifact Preview"
                className="w-full h-full border-none"
                sandbox="allow-scripts allow-same-origin allow-forms"
            />
        </div>
    </div>
  );
};

export default ArtifactWindow;
