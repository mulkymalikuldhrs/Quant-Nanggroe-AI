import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const statusIndicatorVariants = cva(
  "relative inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium uppercase tracking-wider",
  {
    variants: {
      status: {
        online: "bg-success/20 text-success border border-success/30",
        offline: "bg-muted text-muted-foreground border border-border",
        warning: "bg-warning/20 text-warning border border-warning/30",
        error: "bg-destructive/20 text-destructive border border-destructive/30",
        processing: "bg-primary/20 text-primary border border-primary/30",
        idle: "bg-secondary text-secondary-foreground border border-border",
      },
    },
    defaultVariants: {
      status: "offline",
    },
  }
);

export interface StatusIndicatorProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof statusIndicatorVariants> {
  pulse?: boolean;
}

const StatusIndicator = React.forwardRef<HTMLDivElement, StatusIndicatorProps>(
  ({ className, status, pulse = true, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(statusIndicatorVariants({ status }), className)}
        {...props}
      >
        <span className="relative flex h-2 w-2">
          {pulse && status === "online" && (
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75" />
          )}
          {pulse && status === "processing" && (
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />
          )}
          <span
            className={cn(
              "relative inline-flex rounded-full h-2 w-2",
              status === "online" && "bg-success",
              status === "offline" && "bg-muted-foreground",
              status === "warning" && "bg-warning",
              status === "error" && "bg-destructive",
              status === "processing" && "bg-primary",
              status === "idle" && "bg-secondary-foreground"
            )}
          />
        </span>
        {children}
      </div>
    );
  }
);
StatusIndicator.displayName = "StatusIndicator";

export { StatusIndicator, statusIndicatorVariants };
