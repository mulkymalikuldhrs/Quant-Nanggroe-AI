/**
 * @deprecated Use useOrganismReal.ts instead for Supabase-connected real data.
 * This hook is kept as a fallback for demo/preview mode without Supabase auth.
 */

import { useState, useEffect, useCallback } from "react";
import type { LogEntry } from "@/components/ui/activity-log";

interface OrganismState {
  status: "alive" | "dormant" | "spawning" | "dying";
  generation: number;
  uptime: number;
  problemsScanned: number;
  ideasGenerated: number;
  productsBuilt: number;
  revenue: number;
  agentsActive: number;
  agentsTerminated: number;
}

const logMessages = {
  sense: [
    "Scanning Reddit for pain points...",
    "Analyzing YouTube comments...",
    "Processing Quora questions...",
    "Found potential problems in tech space",
    "Detected trending issue: API rate limiting",
  ],
  decision: [
    "Clustering problems by category...",
    "Running sentiment analysis...",
    "Calculating automation potential...",
    "Top candidate: developer tools (score: 87)",
    "Selected MVP: API monitoring dashboard",
  ],
  factory: [
    "Generating project structure...",
    "Creating database schema...",
    "Building API endpoints...",
    "Deploying to Vercel...",
    "Product live: monitor.saas.ai",
  ],
  growth: [
    "Generating blog content...",
    "Posting to Medium...",
    "A/B testing CTAs...",
    "New signup from organic search",
    "Revenue +$12.99 from subscription",
  ],
  system: [
    "Immune system check: OK",
    "Memory optimization complete",
    "Spawning new research agent...",
    "Agent efficiency monitoring active",
  ],
};

export function useOrganismSimulation() {
  const [state, setState] = useState<OrganismState>({
    status: "alive",
    generation: 1,
    uptime: 0,
    problemsScanned: 0,
    ideasGenerated: 0,
    productsBuilt: 0,
    revenue: 0,
    agentsActive: 0,
    agentsTerminated: 0,
  });

  const [logs, setLogs] = useState<LogEntry[]>([]);

  const addLog = useCallback((type: LogEntry["type"], source: string, message: string) => {
    const newLog: LogEntry = {
      id: Date.now().toString(),
      timestamp: new Date(),
      type,
      source,
      message,
    };
    setLogs((prev) => [newLog, ...prev].slice(0, 100));
  }, []);

  // Simulate organism activity
  useEffect(() => {
    const interval = setInterval(() => {
      const sources = ["SENSE", "DECISION", "FACTORY", "GROWTH", "SYSTEM"];
      const sourceKey = sources[Math.floor(Math.random() * sources.length)].toLowerCase() as keyof typeof logMessages;
      const messages = logMessages[sourceKey] || logMessages.system;
      const message = messages[Math.floor(Math.random() * messages.length)];
      
      const types: LogEntry["type"][] = ["info", "success", "warning", "system"];
      const type = types[Math.floor(Math.random() * types.length)];

      addLog(type, sourceKey.toUpperCase(), message);

      // Update metrics occasionally
      if (Math.random() > 0.7) {
        setState((prev) => ({
          ...prev,
          uptime: prev.uptime + 1,
          problemsScanned: prev.problemsScanned + Math.floor(Math.random() * 10),
          ideasGenerated: Math.random() > 0.9 ? prev.ideasGenerated + 1 : prev.ideasGenerated,
        }));
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [addLog]);

  // Initial logs
  useEffect(() => {
    addLog("system", "CORE", "Simulation mode — no Supabase connection");
    addLog("info", "SENSE", "Beginning environmental scan...");
    addLog("success", "SYSTEM", "All engines operational (demo mode)");
  }, [addLog]);

  return { state, logs, agents: [], addLog };
}
