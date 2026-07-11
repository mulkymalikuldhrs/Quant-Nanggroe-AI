import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const organismCardVariants = cva(
  "relative rounded-lg border backdrop-blur-sm transition-all duration-300",
  {
    variants: {
      variant: {
        default: "bg-card/80 border-border hover:border-primary/50 hover:glow-primary",
        sense: "bg-card/80 border-primary/30 hover:border-primary hover:glow-primary",
        decision: "bg-card/80 border-intelligence/30 hover:border-intelligence hover:glow-intelligence",
        factory: "bg-card/80 border-accent/30 hover:border-accent hover:glow-accent",
        growth: "bg-card/80 border-success/30 hover:border-success",
        memory: "bg-card/80 border-warning/30 hover:border-warning",
        danger: "bg-card/80 border-destructive/30 hover:border-destructive hover:glow-destructive",
      },
      size: {
        sm: "p-3",
        default: "p-4",
        lg: "p-6",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface OrganismCardProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof organismCardVariants> {
  pulse?: boolean;
}

const OrganismCard = React.forwardRef<HTMLDivElement, OrganismCardProps>(
  ({ className, variant, size, pulse, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          organismCardVariants({ variant, size }),
          pulse && "pulse-glow",
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);
OrganismCard.displayName = "OrganismCard";

const OrganismCardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex items-center gap-3 mb-3", className)}
    {...props}
  />
));
OrganismCardHeader.displayName = "OrganismCardHeader";

const OrganismCardTitle = React.forwardRef<
  HTMLHeadingElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn("text-sm font-semibold uppercase tracking-wider", className)}
    {...props}
  />
));
OrganismCardTitle.displayName = "OrganismCardTitle";

const OrganismCardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("", className)} {...props} />
));
OrganismCardContent.displayName = "OrganismCardContent";

export {
  OrganismCard,
  OrganismCardHeader,
  OrganismCardTitle,
  OrganismCardContent,
  organismCardVariants,
};
