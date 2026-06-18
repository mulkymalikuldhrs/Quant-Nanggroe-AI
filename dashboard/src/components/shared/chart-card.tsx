"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface ChartCardProps {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  className?: string;
  action?: React.ReactNode;
  glow?: "emerald" | "red" | "blue" | "amber" | "purple" | "none";
}

export function ChartCard({ title, subtitle, children, className, action, glow = "none" }: ChartCardProps) {
  const glowStyles = {
    emerald: "shadow-[0_0_30px_rgba(16,185,129,0.08)] border-emerald-500/10",
    red: "shadow-[0_0_30px_rgba(239,68,68,0.08)] border-red-500/10",
    blue: "shadow-[0_0_30px_rgba(59,130,246,0.08)] border-blue-500/10",
    amber: "shadow-[0_0_30px_rgba(245,158,11,0.08)] border-amber-500/10",
    purple: "shadow-[0_0_30px_rgba(168,85,247,0.08)] border-purple-500/10",
    none: "",
  };

  return (
    <Card className={cn(glowStyles[glow], className)}>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <div>
          <CardTitle>{title}</CardTitle>
          {subtitle && (
            <p className="text-xs text-white/40 mt-0.5">{subtitle}</p>
          )}
        </div>
        {action}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}
