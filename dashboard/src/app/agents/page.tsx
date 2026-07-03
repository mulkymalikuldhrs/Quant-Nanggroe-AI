"use client";

import React, { useEffect, useState } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

export default function AgentsPage() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    fetch("/api/agents/status").then(r => r.json()).then(setData);
  }, []);

  const agents = data?.agents || [];

  return (
    <div className="space-y-4 animate-slide-up">
      <ChartCard title="Agent Status" subtitle="11-agent system">
        <ScrollArea className="max-h-96">
          <div className="space-y-2">
            {agents.map((a: any, i: number) => (
              <div key={i} className="flex justify-between p-2 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                <span className="text-xs text-white/80">{a.name}</span>
                <Badge variant={a.status === "active" ? "success" : "default"} className="text-[10px]">
                  {a.status}
                </Badge>
              </div>
            ))}
            {agents.length === 0 && (
              <div className="p-4 text-center text-white/40">Loading agents from /api/agents/status...</div>
            )}
          </div>
        </ScrollArea>
      </ChartCard>
    </div>
  );
}