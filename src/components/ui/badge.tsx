import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary/20 text-primary shadow-[inset_0_0_8px_rgba(6,182,212,0.1)]",
        secondary: "border-transparent bg-secondary text-secondary-foreground",
        destructive: "border-transparent bg-destructive/20 text-destructive shadow-[inset_0_0_8px_rgba(239,68,68,0.1)]",
        outline: "text-foreground backdrop-blur-sm bg-background/30",
        cyan: "border-transparent bg-cyan/15 text-cyan border border-cyan/20 shadow-[0_0_10px_rgba(6,182,212,0.1)]",
        purple: "border-transparent bg-purple/15 text-purple border border-purple/20 shadow-[0_0_10px_rgba(139,92,246,0.1)]",
        emerald: "border-transparent bg-emerald/15 text-emerald border border-emerald/20 shadow-[0_0_10px_rgba(16,185,129,0.1)]",
        amber: "border-transparent bg-amber/15 text-amber border border-amber/20 shadow-[0_0_10px_rgba(245,158,11,0.1)]",
        rose: "border-transparent bg-rose/15 text-rose border border-rose/20 shadow-[0_0_10px_rgba(244,63,94,0.1)]",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
