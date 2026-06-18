import React from 'react';

export function StatusCard({ title, value, subtitle, icon, color = 'cyan' }: {
  title: string; value: string | number; subtitle?: string; icon?: string; color?: string;
}) {
  const colors: Record<string, string> = {
    cyan: 'from-cyan-500/10 to-cyan-500/5 border-cyan-500/20',
    purple: 'from-purple-500/10 to-purple-500/5 border-purple-500/20',
    emerald: 'from-emerald-500/10 to-emerald-500/5 border-emerald-500/20',
    amber: 'from-amber-500/10 to-amber-500/5 border-amber-500/20',
    red: 'from-red-500/10 to-red-500/5 border-red-500/20',
  };
  return (
    <div className={`rounded-xl bg-gradient-to-br ${colors[color] || colors.cyan} border backdrop-blur-sm p-4`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-white/50 text-xs uppercase tracking-wider">{title}</span>
        {icon && <span className="text-lg opacity-50">{icon}</span>}
      </div>
      <div className="text-2xl font-bold text-white">{value}</div>
      {subtitle && <div className="text-xs text-white/40 mt-1">{subtitle}</div>}
    </div>
  );
}

export function GlassCard({ title, children, className = '' }: { title?: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl bg-white/[0.03] border border-white/5 backdrop-blur-sm ${className}`}>
      {title && <div className="px-4 py-3 border-b border-white/5 text-white/70 text-sm font-medium">{title}</div>}
      <div className="p-4">{children}</div>
    </div>
  );
}
