"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

const Progress = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement> & {
  value?: number;
  indicatorClassName?: string;
}>(({ className, value = 0, indicatorClassName, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("relative h-2 w-full overflow-hidden rounded-full bg-white/10", className)}
    {...props}
  >
    <div
      className={cn(
        "h-full rounded-full bg-emerald-500 transition-all duration-500",
        indicatorClassName,
      )}
      style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
    />
  </div>
));
Progress.displayName = "Progress";

export { Progress };
