import * as React from "react";
import { cn } from "@/lib/utils";
import { cva, type VariantProps } from "class-variance-authority";

const metricVariants = cva("", {
  variants: {
    variant: {
      default: "text-foreground",
      primary: "text-primary text-glow-primary",
      accent: "text-accent text-glow-accent",
      success: "text-success",
      warning: "text-warning",
      destructive: "text-destructive",
    },
    size: {
      sm: "text-xl font-semibold",
      default: "text-3xl font-bold",
      lg: "text-5xl font-bold",
    },
  },
  defaultVariants: {
    variant: "default",
    size: "default",
  },
});

export interface MetricDisplayProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof metricVariants> {
  value: string | number;
  label: string;
  trend?: "up" | "down" | "neutral";
  trendValue?: string;
}

const MetricDisplay = React.forwardRef<HTMLDivElement, MetricDisplayProps>(
  ({ className, variant, size, value, label, trend, trendValue, ...props }, ref) => {
    return (
      <div ref={ref} className={cn("flex flex-col gap-1", className)} {...props}>
        <span className="text-xs uppercase tracking-wider text-muted-foreground">
          {label}
        </span>
        <div className="flex items-end gap-2">
          <span className={cn(metricVariants({ variant, size }), "font-mono")}>
            {value}
          </span>
          {trend && trendValue && (
            <span
              className={cn(
                "text-xs font-medium mb-1",
                trend === "up" && "text-success",
                trend === "down" && "text-destructive",
                trend === "neutral" && "text-muted-foreground"
              )}
            >
              {trend === "up" && "↑"}
              {trend === "down" && "↓"}
              {trend === "neutral" && "→"}
              {trendValue}
            </span>
          )}
        </div>
      </div>
    );
  }
);
MetricDisplay.displayName = "MetricDisplay";

export { MetricDisplay, metricVariants };
