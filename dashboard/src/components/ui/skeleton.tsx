import { cn } from "@/lib/utils";

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        "animate-shimmer rounded-md bg-gradient-to-r from-white/5 via-white/10 to-white/5 bg-[length:200%_100%]",
        className,
      )}
    />
  );
}
