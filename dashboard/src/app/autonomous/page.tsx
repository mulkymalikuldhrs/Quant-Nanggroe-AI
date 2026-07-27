"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Play,
  Pause,
  Activity,
  Brain,
  TrendingUp,
  RefreshCw,
  Zap,
  Target,
  BarChart3,
  Clock,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
} from "recharts";

interface AutonomousStatus {
  is_running: boolean;
  cycle_count: number;
  total_trades_evaluated: number;
  strategies_evolved: number;
  strategies_validated: number;
  capital_deployed: number;
  current_equity: number;
  drawdown: number;
  sharpe_ratio: number;
  last_evaluation: string | null;
  last_evolution: string | null;
  last_validation: string | null;
  error_count: number;
  last_error: string | null;
}

interface SelfAwarenessReflection {
  assessment: string;
  confidence: number;
  recommendations: string[];
  risks: string[];
  timestamp: string;
}

export default function AutonomousPage() {
  const [status, setStatus] = useState<AutonomousStatus | null>(null);
  const [reflection, setReflection] = useState<SelfAwarenessReflection | null>(null);
  const [loading, setLoading] = useState(true);
  const [isStarting, setIsStarting] = useState(false);
  const [isStopping, setIsStopping] = useState(false);

  useEffect(() => {
    fetchStatus();
    fetchReflection();
    const interval = setInterval(() => {
      fetchStatus();
      fetchReflection();
    }, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, []);

  const fetchStatus = async () => {
    try {
      const res = await fetch("/api/autonomous/status");
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
      }
    } catch (err) {
      console.error("Failed to fetch autonomous status:", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchReflection = async () => {
    try {
      const res = await fetch("/api/autonomous/self-awareness");
      if (res.ok) {
        const data = await res.json();
        setReflection(data.reflection);
      }
    } catch (err) {
      // Self-awareness not available
    }
  };

  const handleStart = async () => {
    setIsStarting(true);
    try {
      await fetch("/api/autonomous/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          evaluation_interval_minutes: 30,
          evolution_interval_hours: 6,
          validation_interval_hours: 12,
          min_trades_for_evaluation: 10,
          max_strategies_to_evolve: 5,
          capital_allocation_pct: 0.8,
        }),
      });
      await fetchStatus();
    } catch (err) {
      console.error("Failed to start autonomous loop:", err);
    } finally {
      setIsStarting(false);
    }
  };

  const handleStop = async () => {
    setIsStopping(true);
    try {
      await fetch("/api/autonomous/stop", { method: "POST" });
      await fetchStatus();
    } catch (err) {
      console.error("Failed to stop autonomous loop:", err);
    } finally {
      setIsStopping(false);
    }
  };

  const handleTrigger = async (action: "evaluate" | "evolve" | "validate" | "reallocate") => {
    try {
      await fetch(`/api/autonomous/${action}`, { method: "POST" });
      await fetchStatus();
    } catch (err) {
      console.error(`Failed to trigger ${action}:`, err);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-500" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Autonomous Self-Loop</h1>
          <p className="text-muted-foreground mt-1">
            Continuous trade → evaluate → evolve → validate → redeploy cycle
          </p>
        </div>
        <div className="flex items-center gap-3">
          {status?.is_running ? (
            <Badge variant="success" className="gap-1.5">
              <Activity className="w-3 h-3 animate-pulse" />
              Running
            </Badge>
          ) : (
            <Badge>Stopped</Badge>
          )}
          {status?.is_running ? (
            <Button
              variant="outline"
              onClick={handleStop}
              disabled={isStopping}
              className="gap-2"
            >
              <Pause className="w-4 h-4" />
              Stop
            </Button>
          ) : (
            <Button
              variant="glow"
              onClick={handleStart}
              disabled={isStarting}
              className="gap-2"
            >
              <Play className="w-4 h-4" />
              Start
            </Button>
          )}
        </div>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Cycles Completed</CardTitle>
            <RefreshCw className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{status?.cycle_count || 0}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {status?.total_trades_evaluated || 0} trades evaluated
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Strategies Evolved</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{status?.strategies_evolved || 0}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {status?.strategies_validated || 0} validated
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Capital Deployed</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {((status?.capital_deployed || 0) * 100).toFixed(1)}%
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Equity: ${status?.current_equity?.toFixed(2) || "0.00"}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Performance</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {status?.sharpe_ratio?.toFixed(2) || "0.00"}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Drawdown: {((status?.drawdown || 0) * 100).toFixed(1)}%
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Self-Awareness Reflection */}
      {reflection && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Brain className="w-5 h-5 text-purple-500" />
              <CardTitle>Self-Awareness Reflection</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-2">
              <Badge variant={reflection.assessment === "HEALTHY" ? "success" : "warning"}>
                {reflection.assessment}
              </Badge>
              <span className="text-sm text-muted-foreground">
                Confidence: {(reflection.confidence * 100).toFixed(0)}%
              </span>
            </div>
            
            {reflection.recommendations && reflection.recommendations.length > 0 && (
              <div>
                <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                  Recommendations
                </h4>
                <ul className="space-y-1">
                  {reflection.recommendations.map((rec, i) => (
                    <li key={i} className="text-sm text-muted-foreground flex items-start gap-2">
                      <span className="text-emerald-500 mt-0.5">•</span>
                      {rec}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {reflection.risks && reflection.risks.length > 0 && (
              <div>
                <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-amber-500" />
                  Identified Risks
                </h4>
                <ul className="space-y-1">
                  {reflection.risks.map((risk, i) => (
                    <li key={i} className="text-sm text-muted-foreground flex items-start gap-2">
                      <span className="text-amber-500 mt-0.5">•</span>
                      {risk}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Manual Controls */}
      <Tabs defaultValue="controls" className="space-y-4">
        <TabsList>
          <TabsTrigger value="controls">Manual Controls</TabsTrigger>
          <TabsTrigger value="timeline">Timeline</TabsTrigger>
          <TabsTrigger value="errors">Errors</TabsTrigger>
        </TabsList>

        <TabsContent value="controls" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="w-5 h-5" />
                  Performance Evaluation
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  Evaluate recent trade performance across all strategies
                </p>
                <Button
                  variant="outline"
                  onClick={() => handleTrigger("evaluate")}
                  className="w-full gap-2"
                  disabled={!status?.is_running}
                >
                  <Activity className="w-4 h-4" />
                  Trigger Evaluation
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="w-5 h-5" />
                  Strategy Evolution
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  Evolve underperforming strategies with genetic algorithms
                </p>
                <Button
                  variant="outline"
                  onClick={() => handleTrigger("evolve")}
                  className="w-full gap-2"
                  disabled={!status?.is_running}
                >
                  <Zap className="w-4 h-4" />
                  Trigger Evolution
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <RefreshCw className="w-5 h-5" />
                  Walk-Forward Validation
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  Validate evolved strategies via rolling window analysis
                </p>
                <Button
                  variant="outline"
                  onClick={() => handleTrigger("validate")}
                  className="w-full gap-2"
                  disabled={!status?.is_running}
                >
                  <RefreshCw className="w-4 h-4" />
                  Trigger Validation
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Target className="w-5 h-5" />
                  Capital Reallocation
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  Reallocate capital based on strategy performance
                </p>
                <Button
                  variant="outline"
                  onClick={() => handleTrigger("reallocate")}
                  className="w-full gap-2"
                  disabled={!status?.is_running}
                >
                  <Target className="w-4 h-4" />
                  Trigger Reallocation
                </Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="timeline">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="w-5 h-5" />
                Self-Loop Timeline
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 rounded-lg bg-white/5">
                  <div className="flex items-center gap-3">
                    <Activity className="w-5 h-5 text-emerald-500" />
                    <div>
                      <p className="text-sm font-medium">Last Evaluation</p>
                      <p className="text-xs text-muted-foreground">
                        {status?.last_evaluation
                          ? new Date(status.last_evaluation).toLocaleString()
                          : "Never"}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between p-3 rounded-lg bg-white/5">
                  <div className="flex items-center gap-3">
                    <Zap className="w-5 h-5 text-amber-500" />
                    <div>
                      <p className="text-sm font-medium">Last Evolution</p>
                      <p className="text-xs text-muted-foreground">
                        {status?.last_evolution
                          ? new Date(status.last_evolution).toLocaleString()
                          : "Never"}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between p-3 rounded-lg bg-white/5">
                  <div className="flex items-center gap-3">
                    <RefreshCw className="w-5 h-5 text-blue-500" />
                    <div>
                      <p className="text-sm font-medium">Last Validation</p>
                      <p className="text-xs text-muted-foreground">
                        {status?.last_validation
                          ? new Date(status.last_validation).toLocaleString()
                          : "Never"}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="errors">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertCircle className="w-5 h-5" />
                Error Log
              </CardTitle>
            </CardHeader>
            <CardContent>
              {status?.error_count && status.error_count > 0 ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                    <div>
                      <p className="text-sm font-medium text-red-500">
                        {status.error_count} Error{status.error_count > 1 ? "s" : ""} Detected
                      </p>
                      {status.last_error && (
                        <p className="text-xs text-red-400 mt-1 font-mono">
                          {status.last_error}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-center py-12 text-muted-foreground">
                  <CheckCircle2 className="w-12 h-12 text-emerald-500 mb-3" />
                  <p className="text-sm">No errors detected</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
