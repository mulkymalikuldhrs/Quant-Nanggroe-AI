"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn, getStatusColor } from "@/lib/utils";

interface AgentCardProps {
  id: string;
  name: string;
  icon: string;
  status: string;
  emotion: string;
  action: string;
  lastDecision?: string;
  className?: string;
  onClick?: () => void;
}

export function AgentCard({
  name,
  icon,
  status,
  emotion,
  action,
  lastDecision,
  className,
  onClick,
}: AgentCardProps) {
  const statusVariant =
    status === "active"
      ? "success"
      : status === "warning"
        ? "warning"
        : status === "error"
          ? "danger"
          : "default";

  return (
    <Card
      className={cn(
        "cursor-pointer transition-all duration-300 hover:scale-[1.02] hover:border-white/10 group",
        status === "active" && "border-emerald-500/10",
        status === "warning" && "border-amber-500/10",
        className,
      )}
      onClick={onClick}
    >
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <div className="text-2xl flex-shrink-0 w-10 h-10 flex items-center justify-center rounded-lg bg-white/5 group-hover:bg-white/10 transition-colors">
            {icon}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between gap-2 mb-1">
              <h3 className="text-sm font-semibold text-white truncate">{name}</h3>
              <Badge variant={statusVariant}>{status}</Badge>
            </div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs text-white/40">Emotion:</span>
              <span className={cn("text-xs font-medium", getStatusColor(emotion === "cautious" || emotion === "alert" ? "warning" : status))}>
                {emotion}
              </span>
            </div>
            <p className="text-xs text-white/50 mb-2 truncate">{action}</p>
            {lastDecision && (
              <div className="bg-white/[0.03] rounded-md px-2 py-1.5 border border-white/[0.04]">
                <p className="text-xs text-white/40 leading-relaxed">
                  <span className="text-white/50 font-medium">Last: </span>
                  {lastDecision}
                </p>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
