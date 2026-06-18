"use client";

import React, { useState } from "react";
import {
  FileCode2,
  Plus,
  CheckCircle2,
  AlertTriangle,
  Code2,
  Copy,
  Play,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { SectionHeader } from "@/components/dashboard/shared";
import { useAppStore } from "@/lib/store";

const STRATEGY_TEMPLATES = [
  {
    name: "SMA Crossover",
    yaml: `strategy:
  name: sma_crossover
  type: trend_following
  universe: [AAPL, MSFT, GOOGL]
  parameters:
    fast_period: 20
    slow_period: 50
    position_size: 0.1
  risk:
    max_position_pct: 0.2
    stop_loss_pct: 0.03
    take_profit_pct: 0.06
  schedule: "0 9:30 * * 1-5"`,
  },
  {
    name: "Mean Reversion",
    yaml: `strategy:
  name: mean_reversion
  type: mean_reversion
  universe: [SPY, QQQ, IWM]
  parameters:
    lookback: 20
    z_score_threshold: 2.0
    position_size: 0.05
  risk:
    max_position_pct: 0.15
    stop_loss_pct: 0.02
  schedule: "0 10:00 * * 1-5"`,
  },
  {
    name: "Momentum",
    yaml: `strategy:
  name: momentum
  type: momentum
  universe: [BTC-USD, ETH-USD]
  parameters:
    lookback: 14
    threshold: 0.02
    position_size: 0.08
  risk:
    max_position_pct: 0.25
    stop_loss_pct: 0.05
    trailing_stop: true
    trailing_stop_pct: 0.03
  schedule: "*/30 * * * *"`,
  },
  {
    name: "Breakout",
    yaml: `strategy:
  name: breakout
  type: breakout
  universe: [AAPL, TSLA, NVDA]
  parameters:
    channel_period: 20
    breakout_threshold: 0.01
    position_size: 0.1
  risk:
    max_position_pct: 0.2
    stop_loss_pct: 0.03
    max_daily_trades: 5
  schedule: "0 9:30 * * 1-5"`,
  },
  {
    name: "Statistical Arbitrage",
    yaml: `strategy:
  name: stat_arb
  type: pairs_trading
  universe: [AAPL/MSFT, GOOGL/META]
  parameters:
    lookback: 60
    entry_z: 2.0
    exit_z: 0.5
    position_size: 0.05
  risk:
    max_position_pct: 0.1
    stop_loss_pct: 0.02
    max_correlation: 0.8
  schedule: "0 */2 * * 1-5"`,
  },
  {
    name: "Crypto Momentum",
    yaml: `strategy:
  name: crypto_momentum
  type: momentum
  universe: [BTC-USD, ETH-USD, SOL-USD]
  parameters:
    rsi_period: 14
    rsi_overbought: 70
    rsi_oversold: 30
    position_size: 0.06
  risk:
    max_position_pct: 0.2
    stop_loss_pct: 0.05
    kill_switch_drawdown: 0.10
  schedule: "*/15 * * * *"`,
  },
];

export default function StrategiesPage() {
  const [selectedStrategy, setSelectedStrategy] = useState<string | null>(null);
  const [yamlContent, setYamlContent] = useState("");
  const [isEditing, setIsEditing] = useState(false);
  const [newName, setNewName] = useState("");

  const handleSelectTemplate = (template: (typeof STRATEGY_TEMPLATES)[0]) => {
    setSelectedStrategy(template.name);
    setYamlContent(template.yaml);
    setIsEditing(true);
  };

  const handleNewStrategy = () => {
    setSelectedStrategy(null);
    setYamlContent(STRATEGY_TEMPLATES[0].yaml);
    setIsEditing(true);
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <FileCode2 className="w-6 h-6 text-cyan" />
            Strategy Manager
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Create, edit, and validate YAML-based trading strategies
          </p>
        </div>
        <Button variant="cyan" onClick={handleNewStrategy} className="gap-2 cursor-pointer">
          <Plus className="w-4 h-4" />
          New Strategy
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Strategy Templates List */}
        <div className="space-y-4">
          <SectionHeader title="Strategy Templates" description="Pre-built strategy patterns" />
          <ScrollArea className="max-h-[calc(100vh-250px)]">
            <div className="space-y-2">
              {STRATEGY_TEMPLATES.map((template) => (
                <button
                  key={template.name}
                  onClick={() => handleSelectTemplate(template)}
                  className={`w-full p-3 rounded-lg text-left transition-all cursor-pointer ${
                    selectedStrategy === template.name
                      ? "glass-card border-primary/40 bg-primary/5"
                      : "glass-card hover:border-primary/20"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-foreground">
                      {template.name}
                    </span>
                    <Badge variant="outline" className="text-[9px]">
                      YAML
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground line-clamp-1">
                    {template.yaml.split("\n")[2]?.replace("  type: ", "") || "Strategy"}
                  </p>
                </button>
              ))}
            </div>
          </ScrollArea>
        </div>

        {/* Editor */}
        <div className="lg:col-span-2 space-y-4">
          {isEditing ? (
            <>
              <Card className="glass-card">
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                      <Code2 className="w-4 h-4 text-cyan" />
                      {selectedStrategy || "New Strategy"}
                    </span>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-xs cursor-pointer"
                        onClick={() => {
                          navigator.clipboard.writeText(yamlContent);
                        }}
                      >
                        <Copy className="w-3 h-3 mr-1" />
                        Copy
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-xs text-emerald cursor-pointer"
                      >
                        <CheckCircle2 className="w-3 h-3 mr-1" />
                        Validate
                      </Button>
                    </div>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <Textarea
                    value={yamlContent}
                    onChange={(e) => setYamlContent(e.target.value)}
                    className="font-mono text-sm min-h-[400px] bg-background/50"
                    spellCheck={false}
                  />
                </CardContent>
              </Card>

              {/* Validation Preview */}
              <Card className="glass-card">
                <CardHeader>
                  <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
                    Parsed Preview
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {yamlContent.split("\n").filter(l => l.includes(":")).slice(0, 8).map((line, i) => {
                      const [key, ...rest] = line.trim().split(":");
                      const value = rest.join(":").trim();
                      return (
                        <div key={i} className="flex items-center gap-3 text-sm">
                          <span className="text-cyan font-mono min-w-[140px]">{key}</span>
                          <span className="text-muted-foreground">→</span>
                          <span className="text-foreground">{value}</span>
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
            </>
          ) : (
            <Card className="glass-card p-12">
              <div className="text-center">
                <FileCode2 className="w-12 h-12 text-muted-foreground/30 mx-auto mb-4" />
                <p className="text-sm text-muted-foreground">
                  Select a template or create a new strategy
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Strategies are defined in YAML format
                </p>
                <Button
                  variant="outline"
                  className="mt-4 cursor-pointer"
                  onClick={handleNewStrategy}
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Create New
                </Button>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
