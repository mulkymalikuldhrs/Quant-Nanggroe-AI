import { cn } from "@/lib/utils";
import { OrganismCard, OrganismCardHeader, OrganismCardTitle, OrganismCardContent } from "./ui/organism-card";
import { StatusIndicator } from "./ui/status-indicator";
import { MetricDisplay } from "./ui/metric-display";
import { LucideIcon } from "lucide-react";

interface OrganEngineProps {
  name: string;
  icon: LucideIcon;
  variant: "sense" | "decision" | "factory" | "growth" | "memory" | "danger" | "default";
  status: "online" | "offline" | "warning" | "error" | "processing" | "idle";
  metrics: Array<{
    label: string;
    value: string | number;
    trend?: "up" | "down" | "neutral";
    trendValue?: string;
  }>;
  description: string;
  className?: string;
}

export function OrganEngine({
  name,
  icon: Icon,
  variant,
  status,
  metrics,
  description,
  className,
}: OrganEngineProps) {
  const variantColors = {
    sense: "text-primary",
    decision: "text-intelligence",
    factory: "text-accent",
    growth: "text-success",
    memory: "text-warning",
    danger: "text-destructive",
    default: "text-foreground",
  };

  return (
    <OrganismCard variant={variant} className={cn("group", className)} pulse={status === "processing"}>
      <OrganismCardHeader>
        <div className={cn("p-2 rounded-lg bg-muted/50", variantColors[variant])}>
          <Icon className="w-4 h-4" />
        </div>
        <OrganismCardTitle className={variantColors[variant]}>
          {name}
        </OrganismCardTitle>
        <div className="ml-auto">
          <StatusIndicator status={status}>
            {status}
          </StatusIndicator>
        </div>
      </OrganismCardHeader>

      <OrganismCardContent>
        <p className="text-xs text-muted-foreground mb-4">
          {description}
        </p>

        <div className="grid grid-cols-2 gap-4">
          {metrics.map((metric, index) => (
            <MetricDisplay
              key={index}
              label={metric.label}
              value={metric.value}
              variant={index === 0 ? (variant === "default" ? "primary" : variant === "sense" ? "primary" : variant === "decision" ? "primary" : variant === "factory" ? "accent" : variant === "growth" ? "success" : variant === "memory" ? "warning" : "destructive") : "default"}
              size="sm"
              trend={metric.trend}
              trendValue={metric.trendValue}
            />
          ))}
        </div>
      </OrganismCardContent>
    </OrganismCard>
  );
}
