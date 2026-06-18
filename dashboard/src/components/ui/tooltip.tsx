"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface TooltipProps {
  content: string;
  children: React.ReactNode;
  className?: string;
}

function Tooltip({ content, children, className }: TooltipProps) {
  const [show, setShow] = React.useState(false);

  return (
    <div className="relative inline-flex" onMouseEnter={() => setShow(true)} onMouseLeave={() => setShow(false)}>
      {children}
      {show && (
        <div
          className={cn(
            "absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 text-xs rounded-md bg-gray-900 text-white/90 border border-white/10 whitespace-nowrap z-50",
            className,
          )}
        >
          {content}
        </div>
      )}
    </div>
  );
}

export { Tooltip };
