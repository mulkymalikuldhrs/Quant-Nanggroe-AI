"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link" | "glow";
  size?: "default" | "sm" | "lg" | "icon";
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", ...props }, ref) => {
    const variants: Record<string, string> = {
      default: "bg-white/10 text-white hover:bg-white/20 border border-white/10",
      destructive: "bg-red-500/20 text-red-400 hover:bg-red-500/30 border border-red-500/20",
      outline: "border border-white/10 bg-transparent hover:bg-white/5 text-white/70",
      secondary: "bg-white/5 text-white/70 hover:bg-white/10 border border-white/5",
      ghost: "hover:bg-white/5 text-white/70",
      link: "text-blue-400 underline-offset-4 hover:underline",
      glow: "bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 border border-emerald-500/30 shadow-[0_0_15px_rgba(16,185,129,0.15)]",
    };

    const sizes: Record<string, string> = {
      default: "h-9 px-4 py-2",
      sm: "h-7 rounded-md px-3 text-xs",
      lg: "h-10 rounded-md px-8",
      icon: "h-9 w-9",
    };

    return (
      <button
        className={cn(
          "inline-flex items-center justify-center whitespace-nowrap rounded-lg text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-white/20 disabled:pointer-events-none disabled:opacity-50",
          variants[variant],
          sizes[size],
          className,
        )}
        ref={ref}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";

export { Button };
