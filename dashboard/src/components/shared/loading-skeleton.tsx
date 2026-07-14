"use client";

import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

// ── Main LoadingSkeleton (variant-based) ─────────────────────────

interface LoadingSkeletonProps {
  variant?: "page" | "card" | "chart" | "table" | "agent" | "dashboard";
  className?: string;
}

export function LoadingSkeleton({ variant = "card", className }: LoadingSkeletonProps) {
  switch (variant) {
    case "page":
      return <PageSkeleton />;
    case "dashboard":
      return <DashboardGridSkeleton />;
    case "chart":
      return <ChartCardSkeleton className={className} />;
    case "table":
      return <TableSkeleton />;
    case "agent":
      return <AgentCardSkeleton />;
    default:
      return <StatusCardSkeleton className={className} />;
  }
}

// ── Status Card Skeleton ─────────────────────────────────────────

export function StatusCardSkeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "rounded-xl border border-white/[0.06] bg-white/[0.02] p-4 space-y-3",
        className,
      )}
    >
      <Skeleton className="h-3 w-20" />
      <Skeleton className="h-7 w-28" />
      <Skeleton className="h-3 w-16" />
    </div>
  );
}

// ── Chart Card Skeleton ──────────────────────────────────────────

export function ChartCardSkeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "rounded-xl border border-white/[0.06] bg-white/[0.02] p-4 space-y-4",
        className,
      )}
    >
      <div className="flex items-center justify-between">
        <div className="space-y-1.5">
          <Skeleton className="h-4 w-28" />
          <Skeleton className="h-3 w-20" />
        </div>
        <Skeleton className="h-8 w-8 rounded-lg" />
      </div>
      <Skeleton className="h-[200px] w-full rounded-lg" />
    </div>
  );
}

// ── Table Row Skeleton ───────────────────────────────────────────

export function TableRowSkeleton({ columns = 4 }: { columns?: number }) {
  return (
    <div className="flex items-center gap-3 py-2.5">
      {Array.from({ length: columns }).map((_, i) => (
        <Skeleton
          key={i}
          className={cn("h-4", i === 0 ? "w-24" : "flex-1")}
        />
      ))}
    </div>
  );
}

// ── Table Skeleton (multiple rows) ───────────────────────────────

export function TableSkeleton({
  rows = 5,
  columns = 4,
}: {
  rows?: number;
  columns?: number;
}) {
  return (
    <div className="space-y-1">
      {Array.from({ length: rows }).map((_, i) => (
        <TableRowSkeleton key={i} columns={columns} />
      ))}
    </div>
  );
}

// ── Dashboard Grid Skeleton (4 metric cards) ─────────────────────

export function DashboardGridSkeleton() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      <StatusCardSkeleton />
      <StatusCardSkeleton />
      <StatusCardSkeleton />
      <StatusCardSkeleton />
    </div>
  );
}

// ── Full Page Skeleton ───────────────────────────────────────────

export function PageSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <Skeleton className="h-7 w-48" />
          <Skeleton className="h-4 w-32" />
        </div>
        <Skeleton className="h-7 w-20 rounded-full" />
      </div>

      {/* Metric Cards */}
      <DashboardGridSkeleton />

      {/* Charts */}
      <div className="grid md:grid-cols-2 gap-4">
        <ChartCardSkeleton />
        <ChartCardSkeleton />
      </div>
    </div>
  );
}

// ── Agent Card Skeleton ──────────────────────────────────────────

export function AgentCardSkeleton() {
  return (
    <div className="flex items-center gap-3 p-3 rounded-lg border border-white/[0.06] bg-white/[0.02]">
      <Skeleton className="w-8 h-8 rounded-full" />
      <div className="flex-1 space-y-1.5">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-3 w-32" />
      </div>
      <Skeleton className="h-5 w-14 rounded-full" />
    </div>
  );
}
