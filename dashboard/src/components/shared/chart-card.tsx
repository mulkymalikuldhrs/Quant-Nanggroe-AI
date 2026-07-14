"use client";

import { cn } from "@/lib/utils";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Maximize2, Minimize2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useState } from "react";

interface ChartCardProps {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  className?: string;
  action?: React.ReactNode;
  loading?: boolean;
  fullscreen?: boolean;
  glow?: "emerald" | "amber" | "purple" | "cyan";
}

export function ChartCard({
  title,
  subtitle,
  children,
  className,
  action,
  loading = false,
  fullscreen: allowFullscreen = false,
  glow,
}: ChartCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <Card
      className={cn(
        "relative",
        expanded && "fixed inset-4 z-50 overflow-auto",
        glow === "emerald" && "shadow-[0_0_30px_rgba(16,185,129,0.06)]",
        glow === "amber" && "shadow-[0_0_30px_rgba(245,158,11,0.06)]",
        glow === "purple" && "shadow-[0_0_30px_rgba(168,85,247,0.06)]",
        glow === "cyan" && "shadow-[0_0_30px_rgba(6,182,212,0.06)]",
        className,
      )}
    >
      <CardHeader>
        <div>
          <CardTitle>{title}</CardTitle>
          {subtitle && <CardDescription>{subtitle}</CardDescription>}
        </div>
        <div className="flex items-center gap-2">
          {action}
          {allowFullscreen && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7"
              onClick={() => setExpanded(!expanded)}
            >
              {expanded ? <Minimize2 className="w-3 h-3" /> : <Maximize2 className="w-3 h-3" />}
            </Button>
          )}
        </div>
      </CardHeader>

      {loading ? (
        <div className="space-y-3">
          <div className="h-4 w-3/4 animate-shimmer rounded" />
          <div className="h-[200px] animate-shimmer rounded-lg" />
        </div>
      ) : (
        <div>{children}</div>
      )}
    </Card>
  );
}
