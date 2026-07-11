import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

interface OrganismCoreProps {
  status: "alive" | "dormant" | "spawning" | "dying";
  className?: string;
}

export function OrganismCore({ status, className }: OrganismCoreProps) {
  const [pulseIntensity, setPulseIntensity] = useState(1);

  useEffect(() => {
    const interval = setInterval(() => {
      setPulseIntensity((prev) => (prev === 1 ? 0.7 : 1));
    }, status === "alive" ? 1000 : 2000);
    return () => clearInterval(interval);
  }, [status]);

  const statusColors = {
    alive: "from-primary via-accent to-primary",
    dormant: "from-muted via-secondary to-muted",
    spawning: "from-intelligence via-primary to-intelligence",
    dying: "from-destructive via-warning to-destructive",
  };

  return (
    <div className={cn("relative flex items-center justify-center", className)}>
      {/* Outer rings */}
      {[...Array(3)].map((_, i) => (
        <div
          key={i}
          className={cn(
            "absolute rounded-full border opacity-20",
            status === "alive" && "border-primary animate-pulse-ring",
            status === "dormant" && "border-muted-foreground",
            status === "spawning" && "border-intelligence animate-pulse-ring",
            status === "dying" && "border-destructive animate-pulse-ring"
          )}
          style={{
            width: `${120 + i * 40}px`,
            height: `${120 + i * 40}px`,
            animationDelay: `${i * 0.5}s`,
          }}
        />
      ))}

      {/* Core glow */}
      <div
        className={cn(
          "absolute w-24 h-24 rounded-full blur-xl transition-opacity duration-1000",
          `bg-gradient-to-br ${statusColors[status]}`
        )}
        style={{ opacity: pulseIntensity * 0.6 }}
      />

      {/* Main core */}
      <div
        className={cn(
          "relative w-20 h-20 rounded-full transition-all duration-500",
          `bg-gradient-to-br ${statusColors[status]}`,
          status === "alive" && "glow-primary",
          status === "spawning" && "glow-intelligence",
          status === "dying" && "glow-destructive"
        )}
        style={{ opacity: pulseIntensity }}
      >
        {/* Inner pattern */}
        <div className="absolute inset-2 rounded-full bg-background/30 backdrop-blur-sm">
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-4 h-4 rounded-full bg-foreground/80 heartbeat" />
          </div>
        </div>
      </div>

      {/* Status label */}
      <div className="absolute -bottom-8 text-center">
        <span
          className={cn(
            "text-xs font-mono uppercase tracking-widest",
            status === "alive" && "text-primary text-glow-primary",
            status === "dormant" && "text-muted-foreground",
            status === "spawning" && "text-intelligence",
            status === "dying" && "text-destructive"
          )}
        >
          {status}
        </span>
      </div>
    </div>
  );
}
