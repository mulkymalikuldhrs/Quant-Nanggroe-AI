import { cn } from "@/lib/utils";
import { StatusIndicator } from "./ui/status-indicator";
import { Bot, Skull, Zap, Clock } from "lucide-react";

interface AgentCardProps {
  id: string;
  name: string;
  type: "research" | "builder" | "growth" | "support";
  status: "active" | "idle" | "terminated" | "spawning";
  tasksCompleted: number;
  uptime: string;
  efficiency: number;
  className?: string;
}

export function AgentCard({
  id,
  name,
  type,
  status,
  tasksCompleted,
  uptime,
  efficiency,
  className,
}: AgentCardProps) {
  const typeColors = {
    research: "border-intelligence/30 hover:border-intelligence",
    builder: "border-accent/30 hover:border-accent",
    growth: "border-success/30 hover:border-success",
    support: "border-primary/30 hover:border-primary",
  };

  const typeIcons = {
    research: "🔬",
    builder: "🏗️",
    growth: "📈",
    support: "🛠️",
  };

  const statusMap = {
    active: "online" as const,
    idle: "idle" as const,
    terminated: "error" as const,
    spawning: "processing" as const,
  };

  return (
    <div
      className={cn(
        "relative p-4 rounded-lg border bg-card/60 backdrop-blur-sm transition-all duration-300",
        typeColors[type],
        status === "terminated" && "opacity-50",
        className
      )}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-xl">{typeIcons[type]}</span>
          <div>
            <h4 className="font-medium text-sm">{name}</h4>
            <span className="text-xs text-muted-foreground font-mono">#{id}</span>
          </div>
        </div>
        <StatusIndicator status={statusMap[status]} pulse={status === "active"}>
          {status}
        </StatusIndicator>
      </div>

      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="p-2 rounded bg-muted/30">
          <Zap className="w-3 h-3 mx-auto mb-1 text-warning" />
          <span className="text-xs font-mono text-foreground">{tasksCompleted}</span>
          <span className="text-[10px] block text-muted-foreground">Tasks</span>
        </div>
        <div className="p-2 rounded bg-muted/30">
          <Clock className="w-3 h-3 mx-auto mb-1 text-primary" />
          <span className="text-xs font-mono text-foreground">{uptime}</span>
          <span className="text-[10px] block text-muted-foreground">Uptime</span>
        </div>
        <div className="p-2 rounded bg-muted/30">
          <Bot className="w-3 h-3 mx-auto mb-1 text-accent" />
          <span className="text-xs font-mono text-foreground">{efficiency}%</span>
          <span className="text-[10px] block text-muted-foreground">Eff.</span>
        </div>
      </div>

      {status === "terminated" && (
        <div className="absolute inset-0 flex items-center justify-center bg-background/50 rounded-lg">
          <Skull className="w-8 h-8 text-destructive" />
        </div>
      )}
    </div>
  );
}
