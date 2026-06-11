
import React, { useEffect, useRef } from 'react';
import { SwarmAgent, AgentState } from '../types';

interface Props {
  agents: SwarmAgent[];
  state: AgentState;
}

const SwarmGraph: React.FC<Props> = ({ agents, state }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const getAgentStatus = (agentId: string) => {
    const task = state.tasks.find(t => t.agentId === agentId);
    if (!task) return 'idle';
    return task.status;
  };

  useEffect(() => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      const centerX = canvas.width / 2;
      const centerY = canvas.height / 2;
      const radius = 80;
      let animationFrameId: number;
      let tick = 0;

        const render = () => {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            tick++;

            // Background Grid (Conceptual)
            ctx.strokeStyle = 'rgba(16, 185, 129, 0.05)';
            ctx.lineWidth = 0.5;
            for(let i=0; i<canvas.width; i+=20) {
                ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, canvas.height); ctx.stroke();
            }
            for(let i=0; i<canvas.height; i+=20) {
                ctx.beginPath(); ctx.moveTo(0, i); ctx.lineTo(canvas.width, i); ctx.stroke();
            }

            // Draw Core (Alpha Prime) - The Matrix Core
            ctx.beginPath();
            const corePulse = 22 + Math.sin(tick * 0.08) * 4;
            const gradient = ctx.createRadialGradient(centerX, centerY, 5, centerX, centerY, corePulse);
            gradient.addColorStop(0, 'rgba(16, 185, 129, 0.8)');
            gradient.addColorStop(1, 'rgba(16, 185, 129, 0)');
            ctx.arc(centerX, centerY, corePulse, 0, Math.PI * 2);
            ctx.fillStyle = gradient;
            ctx.fill();
            
            ctx.beginPath();
            ctx.arc(centerX, centerY, 10, 0, Math.PI * 2);
            ctx.fillStyle = '#10b981';
            ctx.shadowBlur = 15;
            ctx.shadowColor = '#10b981';
            ctx.fill();
            ctx.shadowBlur = 0;

            // Draw Agents
            agents.forEach((agent, index) => {
                const total = agents.length;
                const angle = (index * (360 / total)) * (Math.PI / 180) - (Math.PI / 2) + (tick * 0.005);
                const x = centerX + radius * Math.cos(angle);
                const y = centerY + radius * Math.sin(angle);
                
                const status = getAgentStatus(agent.id);
                const isActive = status === 'active';
                const isDone = status === 'completed';
                
                let color = '#3f3f46'; // zinc-600
                if (isActive) color = '#10b981'; // green
                if (isDone) color = '#3b82f6'; // blue
                
                // Connection Line (Laser Style)
                ctx.beginPath();
                ctx.moveTo(centerX, centerY);
                ctx.lineTo(x, y);
                ctx.strokeStyle = isActive ? 'rgba(16, 185, 129, 0.4)' : 'rgba(63, 63, 70, 0.2)';
                ctx.lineWidth = isActive ? 1.5 : 0.5;
                ctx.stroke();

                // Data flow effect
                if (isActive) {
                    const t = (tick % 40) / 40;
                    const packX = centerX + (x - centerX) * t;
                    const packY = centerY + (y - centerY) * t;
                    ctx.beginPath();
                    ctx.arc(packX, packY, 2, 0, Math.PI * 2);
                    ctx.fillStyle = '#10b981';
                    ctx.fill();
                }

                // Agent Node
                ctx.beginPath();
                ctx.arc(x, y, isActive ? 10 : 7, 0, Math.PI * 2);
                ctx.fillStyle = '#09090b';
                ctx.strokeStyle = color;
                ctx.lineWidth = 2;
                ctx.fill();
                ctx.stroke();

                // Agent Label
                ctx.font = 'bold 8px monospace';
                ctx.fillStyle = isActive ? '#10b981' : '#71717a';
                ctx.textAlign = 'center';
                ctx.fillText(agent.name.toUpperCase(), x, y + 20);
            });

            animationFrameId = requestAnimationFrame(render);
        };

        render();

        return () => cancelAnimationFrame(animationFrameId);
    }, [agents, state]);

    return (
      <div className="relative w-full h-[200px] flex items-center justify-center bg-[#09090b] overflow-hidden border-b border-white/5">
        <canvas ref={canvasRef} width={400} height={200} className="relative z-10" />
      </div>
    );

};

export default SwarmGraph;
