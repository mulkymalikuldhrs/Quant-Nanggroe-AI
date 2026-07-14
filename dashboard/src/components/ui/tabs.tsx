"use client";

import { cn } from "@/lib/utils";
import React, { createContext, useContext, useState } from "react";

// ── Context ────────────────────────────────────────────────────────

interface TabsContextValue {
  value: string;
  onValueChange: (value: string) => void;
}

const TabsContext = createContext<TabsContextValue | null>(null);

function useTabsContext() {
  const ctx = useContext(TabsContext);
  if (!ctx) throw new Error("Tabs compound components must be used within <Tabs>");
  return ctx;
}

// ── Tabs Root ──────────────────────────────────────────────────────

interface TabsProps {
  children: React.ReactNode;
  defaultValue?: string;
  value?: string;
  onValueChange?: (value: string) => void;
  className?: string;
}

export function Tabs({ children, defaultValue, value: controlledValue, onValueChange, className }: TabsProps) {
  const [internalValue, setInternalValue] = useState(defaultValue || "");
  const isControlled = controlledValue !== undefined;
  const value = isControlled ? controlledValue : internalValue;

  const handleChange = (newValue: string) => {
    if (!isControlled) setInternalValue(newValue);
    onValueChange?.(newValue);
  };

  return (
    <TabsContext.Provider value={{ value, onValueChange: handleChange }}>
      <div className={cn("", className)}>
        {children}
      </div>
    </TabsContext.Provider>
  );
}

// ── TabsList ───────────────────────────────────────────────────────

interface TabsListProps {
  children: React.ReactNode;
  className?: string;
}

export function TabsList({ children, className }: TabsListProps) {
  return (
    <div className={cn(
      "flex items-center gap-1 p-1 rounded-xl bg-white/[0.03] border border-white/[0.06] w-fit",
      className,
    )}>
      {children}
    </div>
  );
}

// ── TabsTrigger ────────────────────────────────────────────────────

interface TabsTriggerProps {
  children: React.ReactNode;
  value: string;
  className?: string;
  disabled?: boolean;
}

export function TabsTrigger({ children, value, className, disabled }: TabsTriggerProps) {
  const { value: activeValue, onValueChange } = useTabsContext();
  const isActive = activeValue === value;

  return (
    <button
      role="tab"
      aria-selected={isActive}
      disabled={disabled}
      onClick={() => onValueChange(value)}
      className={cn(
        "relative px-3 py-1.5 text-xs font-medium rounded-lg transition-all duration-200 whitespace-nowrap",
        isActive
          ? "text-white bg-white/[0.08] shadow-sm"
          : "text-white/30 hover:text-white/60 hover:bg-white/[0.03]",
        disabled && "opacity-40 cursor-not-allowed",
        className,
      )}
    >
      {children}
    </button>
  );
}

// ── TabsContent ────────────────────────────────────────────────────

interface TabsContentProps {
  children: React.ReactNode;
  value: string;
  className?: string;
  forceMount?: boolean;
}

export function TabsContent({ children, value, className, forceMount }: TabsContentProps) {
  const { value: activeValue } = useTabsContext();
  const isActive = activeValue === value;

  if (!isActive && !forceMount) return null;

  return (
    <div
      role="tabpanel"
      className={cn(
        isActive ? "animate-fade-in" : "hidden",
        className,
      )}
    >
      {children}
    </div>
  );
}
