import * as React from "react";
import { cn } from "@/lib/utils";
import { ScrollArea } from "./scroll-area";

export interface LogEntry {
  id: string;
  timestamp: Date;
  type: "info" | "success" | "warning" | "error" | "system";
  source: string;
  message: string;
}

interface ActivityLogProps {
  entries: LogEntry[];
  maxHeight?: string;
  className?: string;
}

const typeStyles = {
  info: "text-primary",
  success: "text-success",
  warning: "text-warning",
  error: "text-destructive",
  system: "text-intelligence",
};

const typeLabels = {
  info: "INFO",
  success: "DONE",
  warning: "WARN",
  error: "FAIL",
  system: "SYS",
};

export function ActivityLog({ entries, maxHeight = "300px", className }: ActivityLogProps) {
  return (
    <ScrollArea className={cn("font-mono text-xs", className)} style={{ maxHeight }}>
      <div className="space-y-1 p-2">
        {entries.map((entry) => (
          <div
            key={entry.id}
            className="flex gap-2 py-1 px-2 rounded hover:bg-muted/50 transition-colors"
          >
            <span className="text-muted-foreground shrink-0">
              {entry.timestamp.toLocaleTimeString("en-US", { hour12: false })}
            </span>
            <span className={cn("shrink-0 font-semibold w-12", typeStyles[entry.type])}>
              [{typeLabels[entry.type]}]
            </span>
            <span className="text-secondary-foreground shrink-0">
              {entry.source}:
            </span>
            <span className="text-foreground/90 break-all">
              {entry.message}
            </span>
          </div>
        ))}
        {entries.length === 0 && (
          <div className="text-muted-foreground text-center py-4">
            No activity recorded
          </div>
        )}
      </div>
    </ScrollArea>
  );
}
