"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  options: { value: string; label: string }[];
}

const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, options, ...props }, ref) => (
    <select
      className={cn(
        "flex h-9 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-1 text-sm text-white shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-white/20 disabled:cursor-not-allowed disabled:opacity-50 appearance-none cursor-pointer",
        className,
      )}
      ref={ref}
      {...props}
    >
      {options.map((opt) => (
        <option key={opt.value} value={opt.value} className="bg-gray-900 text-white">
          {opt.label}
        </option>
      ))}
    </select>
  ),
);
Select.displayName = "Select";

export { Select };
