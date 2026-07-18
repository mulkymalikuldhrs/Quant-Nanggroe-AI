"use client";

import { useState, useEffect, useCallback } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { schedulerApi } from "@/lib/api-client";
import type { SchedulerStatus, PipelineCycleResult } from "@/lib/api-client";
import { Play, Square, RefreshCw, Clock, Zap } from "lucide-react";

export function SchedulerControls() {
  const [status, setStatus] = useState<SchedulerStatus | null>(null);
  const [intervalMinutes, setIntervalMinutes] = useState(15);
  const [loading, setLoading] = useState(false);
  const [lastCycle, setLastCycle] = useState<PipelineCycleResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refreshStatus = useCallback(async () => {
    try {
      const s = await schedulerApi.getStatus();
      setStatus(s);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to get status");
    }
  }, []);

  useEffect(() => {
    refreshStatus();
    const id = window.setInterval(refreshStatus, 10000);
    return () => window.clearInterval(id);
  }, [refreshStatus]);

  const handleStart = async () => {
    setLoading(true);
    try {
      await schedulerApi.start(intervalMinutes);
      await refreshStatus();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start");
    }
    setLoading(false);
  };

  const handleStop = async () => {
    setLoading(true);
    try {
      await schedulerApi.stop();
      await refreshStatus();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to stop");
    }
    setLoading(false);
  };

  const handleTriggerCycle = async () => {
    setLoading(true);
    try {
      const result = await schedulerApi.triggerCycle();
      setLastCycle(result);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Cycle failed");
    }
    setLoading(false);
  };

  const isRunning = status?.running ?? false;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Zap className="h-5 w-5" />
          Autonomous Trading Scheduler
          <Badge variant={isRunning ? "success" : "default"}>
            {isRunning ? "RUNNING" : "STOPPED"}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <div className="text-sm text-red-500 bg-red-50 p-2 rounded">{error}</div>
        )}

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4" />
            <span className="text-sm">Interval:</span>
            <Input
              type="number"
              value={intervalMinutes}
              onChange={(e) => setIntervalMinutes(Number(e.target.value))}
              className="w-20"
              min={1}
              disabled={isRunning}
            />
            <span className="text-sm text-muted-foreground">min</span>
          </div>
        </div>

        <div className="flex gap-2">
          {!isRunning ? (
            <Button onClick={handleStart} disabled={loading} size="sm">
              <Play className="h-4 w-4 mr-1" />
              Start Scheduler
            </Button>
          ) : (
            <Button onClick={handleStop} disabled={loading} variant="danger" size="sm">
              <Square className="h-4 w-4 mr-1" />
              Stop Scheduler
            </Button>
          )}
          <Button onClick={handleTriggerCycle} disabled={loading} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-1" />
            Run Cycle Now
          </Button>
        </div>

        {status?.symbols && (
          <div className="text-sm text-muted-foreground">
            Symbols: {status.symbols.join(", ")}
          </div>
        )}

        {lastCycle && (
          <div className="mt-4 space-y-2">
            <h4 className="text-sm font-medium">Last Cycle Result</h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
              {lastCycle.results.map((r) => (
                <div key={r.symbol} className="border rounded p-2 text-sm">
                  <div className="flex justify-between">
                    <span className="font-medium">{r.symbol}</span>
                    <Badge variant={r.success ? "success" : "danger"}>
                      {r.success ? r.signal.toUpperCase() : "FAILED"}
                    </Badge>
                  </div>
                  <div className="text-muted-foreground mt-1">
                    Confidence: {(r.confidence * 100).toFixed(1)}%
                  </div>
                  <div className="text-xs text-muted-foreground truncate">
                    {r.reason}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
