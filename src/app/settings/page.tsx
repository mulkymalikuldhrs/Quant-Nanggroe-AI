"use client";

import React, { useState } from "react";
import {
  Settings,
  Key,
  Server,
  Cpu,
  Globe,
  Save,
  RefreshCw,
  Eye,
  EyeOff,
  AlertCircle,
  Shield,
  Bell,
  Database,
  Brain,
  Zap,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { SectionHeader } from "@/components/dashboard/shared";
import { cn } from "@/lib/utils";

interface LLMProvider {
  id: string;
  name: string;
  model: string;
  apiKey: string;
  baseUrl: string;
  enabled: boolean;
  icon: string;
}

export default function SettingsPage() {
  const [saving, setSaving] = useState(false);
  const [showApiKeys, setShowApiKeys] = useState<Record<string, boolean>>({});
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  const [llmProviders, setLlmProviders] = useState<LLMProvider[]>([
    {
      id: "openai",
      name: "OpenAI",
      model: "gpt-4o",
      apiKey: "",
      baseUrl: "https://api.openai.com/v1",
      enabled: true,
      icon: "🤖",
    },
    {
      id: "anthropic",
      name: "Anthropic",
      model: "claude-3-5-sonnet-20241022",
      apiKey: "",
      baseUrl: "https://api.anthropic.com",
      enabled: false,
      icon: "🧠",
    },
    {
      id: "google",
      name: "Google AI",
      model: "gemini-1.5-pro",
      apiKey: "",
      baseUrl: "https://generativelanguage.googleapis.com",
      enabled: false,
      icon: "🌐",
    },
    {
      id: "nvidia",
      name: "NVIDIA NIM",
      model: "meta/llama-3.1-405b-instruct",
      apiKey: "",
      baseUrl: "https://integrate.api.nvidia.com/v1",
      enabled: false,
      icon: "⚡",
    },
    {
      id: "local",
      name: "Local LLM",
      model: "llama-3-8b",
      apiKey: "",
      baseUrl: "http://localhost:11434",
      enabled: false,
      icon: "💻",
    },
  ]);

  const [systemConfig, setSystemConfig] = useState({
    defaultProvider: "openai",
    defaultModel: "gpt-4o",
    temperature: 0.0,
    logLevel: "INFO",
    riskMaxPerTrade: 0.5,
    riskMaxDailyLoss: 1.0,
    riskMaxWeeklyLoss: 3.0,
    riskMaxDrawdown: 10.0,
    backtestCommission: 0.001,
    backtestSlippage: 0.0005,
    backtestInitialCapital: 100000,
    dataCacheTTL: 300,
    enableWebSocket: true,
    enableAuditLog: true,
    autoRestart: true,
    notificationsEnabled: true,
  });

  const handleSave = async () => {
    setSaving(true);
    setSaveMessage(null);
    await new Promise((resolve) => setTimeout(resolve, 1500));
    setSaving(false);
    setSaveMessage("Settings saved successfully");
    setTimeout(() => setSaveMessage(null), 3000);
  };

  const toggleApiKeyVisibility = (id: string) => {
    setShowApiKeys((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const toggleProvider = (id: string) => {
    setLlmProviders((prev) =>
      prev.map((p) => (p.id === id ? { ...p, enabled: !p.enabled } : p))
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 animate-slide-up">
        <div className="space-y-1">
          <h1 className="text-3xl font-black gradient-text flex items-center gap-3 tracking-tight">
            <Settings className="w-8 h-8 text-foreground animate-pulse-glow" />
            System Configuration
          </h1>
          <p className="text-sm font-medium text-muted-foreground uppercase tracking-widest pl-11">
            Global Parameters & Integrations
          </p>
        </div>
        <div className="flex items-center gap-3">
          {saveMessage && (
            <Badge variant="emerald" className="px-3 py-1 text-xs font-bold uppercase tracking-widest shadow-[0_0_15px_rgba(16,185,129,0.2)] animate-fade-in">
              {saveMessage}
            </Badge>
          )}
          <Button
            className="bg-primary hover:bg-primary/90 text-primary-foreground font-bold tracking-widest uppercase cursor-pointer shadow-[0_4px_20px_rgba(0,0,0,0.5)] hover:shadow-[0_4px_25px_rgba(var(--primary-rgb),0.5)] transition-all hover-lift"
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin mr-2" />
                SAVING...
              </>
            ) : (
              <>
                <Save className="w-4 h-4 mr-2" />
                APPLY CHANGES
              </>
            )}
          </Button>
        </div>
      </div>

      <div className="animate-slide-up" style={{ animationDelay: '100ms' }}>
        <Tabs defaultValue="llm" className="w-full">
          <TabsList className="bg-secondary/20 p-1 mb-6 border border-border/50 backdrop-blur-md flex-wrap h-auto">
            <TabsTrigger value="llm" className="font-bold tracking-widest uppercase text-xs py-2">Providers</TabsTrigger>
            <TabsTrigger value="trading" className="font-bold tracking-widest uppercase text-xs py-2">Trading</TabsTrigger>
            <TabsTrigger value="risk" className="font-bold tracking-widest uppercase text-xs py-2">Risk Limits</TabsTrigger>
            <TabsTrigger value="data" className="font-bold tracking-widest uppercase text-xs py-2">Data APIs</TabsTrigger>
            <TabsTrigger value="system" className="font-bold tracking-widest uppercase text-xs py-2">Core System</TabsTrigger>
          </TabsList>

          {/* LLM Providers */}
          <TabsContent value="llm" className="m-0">
            <div className="space-y-5 stagger-children">
              {llmProviders.map((provider) => (
                <Card 
                  key={provider.id} 
                  variant="flat"
                  className={cn(
                    "transition-all border-l-4",
                    provider.enabled ? "border-l-emerald bg-emerald/5" : "border-l-border/50 hover:border-l-primary/50"
                  )}
                >
                  <CardContent className="p-5">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-4">
                        <div
                          className={cn("w-12 h-12 rounded-xl flex items-center justify-center text-2xl shadow-sm transition-colors",
                            provider.enabled ? "bg-emerald/20 border border-emerald/30 drop-shadow-[0_0_8px_rgba(16,185,129,0.4)]" : "bg-secondary/40 border border-border/40"
                          )}
                        >
                          {provider.icon}
                        </div>
                        <div>
                          <div className="flex items-center gap-3 mb-1">
                            <h3 className="text-base font-black text-foreground uppercase tracking-tight">
                              {provider.name}
                            </h3>
                            {provider.enabled && (
                              <Badge variant="emerald" className="text-[9px] font-bold uppercase tracking-widest shadow-sm">
                                Online
                              </Badge>
                            )}
                          </div>
                          <Badge variant="outline" className="text-[10px] font-mono text-muted-foreground bg-background">
                            {provider.model}
                          </Badge>
                        </div>
                      </div>
                      <Switch
                        checked={provider.enabled}
                        onCheckedChange={() => toggleProvider(provider.id)}
                        className={provider.enabled ? "shadow-[0_0_10px_rgba(16,185,129,0.5)]" : ""}
                      />
                    </div>

                    {provider.enabled && (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 pt-4 border-t border-border/30 animate-fade-in">
                        <div>
                          <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-1.5 block">
                            Active Model
                          </label>
                          <Input
                            value={provider.model}
                            onChange={(e) =>
                              setLlmProviders((prev) =>
                                prev.map((p) =>
                                  p.id === provider.id
                                    ? { ...p, model: e.target.value }
                                    : p
                                )
                              )
                            }
                            className="bg-background/50 focus-visible:ring-emerald/50 border-border/40 font-mono text-sm h-10"
                          />
                        </div>
                        <div>
                          <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-1.5 block">
                            API Authorization Key
                          </label>
                          <div className="relative">
                            <Input
                              type={
                                showApiKeys[provider.id] ? "text" : "password"
                              }
                              value={provider.apiKey}
                              onChange={(e) =>
                                setLlmProviders((prev) =>
                                  prev.map((p) =>
                                    p.id === provider.id
                                      ? { ...p, apiKey: e.target.value }
                                      : p
                                  )
                                )
                              }
                              placeholder="sk-..."
                              className="pr-10 bg-background/50 focus-visible:ring-emerald/50 border-border/40 font-mono text-sm h-10"
                            />
                            <button
                              onClick={() => toggleApiKeyVisibility(provider.id)}
                              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-emerald transition-colors cursor-pointer"
                            >
                              {showApiKeys[provider.id] ? (
                                <EyeOff className="w-4 h-4" />
                              ) : (
                                <Eye className="w-4 h-4" />
                              )}
                            </button>
                          </div>
                        </div>
                        <div className="sm:col-span-2">
                          <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-1.5 block">
                            Endpoint Base URL
                          </label>
                          <Input
                            value={provider.baseUrl}
                            onChange={(e) =>
                              setLlmProviders((prev) =>
                                prev.map((p) =>
                                  p.id === provider.id
                                    ? { ...p, baseUrl: e.target.value }
                                    : p
                                )
                              )
                            }
                            className="bg-background/50 focus-visible:ring-emerald/50 border-border/40 font-mono text-sm h-10"
                          />
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          {/* Trading Configuration */}
          <TabsContent value="trading" className="m-0">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card variant="flat">
                <CardHeader>
                  <CardTitle className="text-sm font-semibold text-foreground uppercase tracking-wider flex items-center gap-2">
                    <Cpu className="w-4 h-4 text-cyan" />
                    Neural Execution Logic
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-5">
                  <div>
                    <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-1.5 block">
                      Primary Engine
                    </label>
                    <Select
                      value={systemConfig.defaultProvider}
                      onValueChange={(v) =>
                        setSystemConfig({ ...systemConfig, defaultProvider: v })
                      }
                    >
                      <SelectTrigger className="bg-secondary/20 h-10 focus:ring-cyan/50 font-bold">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {llmProviders
                          .filter((p) => p.enabled)
                          .map((p) => (
                            <SelectItem key={p.id} value={p.id} className="font-bold">
                              {p.icon} {p.name}
                            </SelectItem>
                          ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-1.5 block">
                      Inference Model
                    </label>
                    <Input
                      value={systemConfig.defaultModel}
                      onChange={(e) =>
                        setSystemConfig({
                          ...systemConfig,
                          defaultModel: e.target.value,
                        })
                      }
                      className="font-mono bg-secondary/20 h-10 focus-visible:ring-cyan/50"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-1.5 block flex justify-between">
                      <span>Creativity / Temperature</span>
                      <span className="text-cyan">{systemConfig.temperature.toFixed(1)}</span>
                    </label>
                    <Input
                      type="range"
                      value={systemConfig.temperature}
                      onChange={(e) =>
                        setSystemConfig({
                          ...systemConfig,
                          temperature: parseFloat(e.target.value) || 0,
                        })
                      }
                      step="0.1"
                      min="0"
                      max="2"
                      className="w-full h-2 bg-secondary rounded-lg appearance-none cursor-pointer accent-cyan"
                    />
                    <div className="flex justify-between text-[9px] text-muted-foreground mt-1 uppercase tracking-widest">
                      <span>Deterministic (0.0)</span>
                      <span>Creative (2.0)</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card variant="flat">
                <CardHeader>
                  <CardTitle className="text-sm font-semibold text-foreground uppercase tracking-wider flex items-center gap-2">
                    <Database className="w-4 h-4 text-purple" />
                    Simulation Parameters
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-5">
                  <div className="grid grid-cols-2 gap-5">
                    <div>
                      <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-1.5 block">
                        Base Commission
                      </label>
                      <Input
                        type="number"
                        value={systemConfig.backtestCommission}
                        onChange={(e) =>
                          setSystemConfig({
                            ...systemConfig,
                            backtestCommission: parseFloat(e.target.value) || 0,
                          })
                        }
                        step="0.0001"
                        className="tabular-nums font-mono bg-secondary/20 focus-visible:ring-purple/50"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-1.5 block">
                        Est. Slippage
                      </label>
                      <Input
                        type="number"
                        value={systemConfig.backtestSlippage}
                        onChange={(e) =>
                          setSystemConfig({
                            ...systemConfig,
                            backtestSlippage: parseFloat(e.target.value) || 0,
                          })
                        }
                        step="0.0001"
                        className="tabular-nums font-mono bg-secondary/20 focus-visible:ring-purple/50"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-1.5 block">
                        Starting Capital
                      </label>
                      <div className="relative">
                        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-xs">$</span>
                        <Input
                          type="number"
                          value={systemConfig.backtestInitialCapital}
                          onChange={(e) =>
                            setSystemConfig({
                              ...systemConfig,
                              backtestInitialCapital: parseInt(e.target.value) || 100000,
                            })
                          }
                          className="tabular-nums font-mono pl-6 bg-secondary/20 focus-visible:ring-purple/50"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-1.5 block">
                        Cache TTL (sec)
                      </label>
                      <Input
                        type="number"
                        value={systemConfig.dataCacheTTL}
                        onChange={(e) =>
                          setSystemConfig({
                            ...systemConfig,
                            dataCacheTTL: parseInt(e.target.value) || 300,
                          })
                        }
                        className="tabular-nums font-mono bg-secondary/20 focus-visible:ring-purple/50"
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Risk Limits */}
          <TabsContent value="risk" className="m-0">
            <Card variant="gradient" className="border-rose/20">
              <CardHeader>
                <CardTitle className="text-sm font-semibold text-foreground uppercase tracking-wider flex items-center gap-2">
                  <Shield className="w-4 h-4 text-rose" />
                  Hardcoded Risk Constitution
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="p-4 rounded-xl border border-rose/30 bg-rose/10 flex items-start gap-4 shadow-[0_0_15px_rgba(244,63,94,0.1)]">
                  <AlertCircle className="w-6 h-6 text-rose shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-bold text-rose uppercase tracking-widest">
                      Immutable Safeguards
                    </p>
                    <p className="text-xs text-rose/80 mt-1 font-medium leading-relaxed">
                      These thresholds supersede all autonomous agent decisions. They are enforced synchronously at the execution core to guarantee portfolio survival during extreme volatility.
                    </p>
                  </div>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 p-4 bg-background/30 rounded-xl border border-border/30">
                  <div>
                    <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-1.5 block">
                      Max Exposure Per Trade
                    </label>
                    <div className="relative">
                       <Input
                        type="number"
                        value={systemConfig.riskMaxPerTrade}
                        onChange={(e) =>
                          setSystemConfig({
                            ...systemConfig,
                            riskMaxPerTrade: parseFloat(e.target.value) || 0,
                          })
                        }
                        step="0.1"
                        min="0.1"
                        max="2.0"
                        className="font-mono bg-secondary/30 focus-visible:ring-rose/50 text-rose font-bold"
                      />
                      <span className="absolute right-4 top-1/2 -translate-y-1/2 text-rose/50 font-mono">%</span>
                    </div>
                  </div>
                  <div>
                    <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-1.5 block">
                      Max Daily Drawdown
                    </label>
                    <div className="relative">
                      <Input
                        type="number"
                        value={systemConfig.riskMaxDailyLoss}
                        onChange={(e) =>
                          setSystemConfig({
                            ...systemConfig,
                            riskMaxDailyLoss: parseFloat(e.target.value) || 0,
                          })
                        }
                        step="0.1"
                        min="0.5"
                        max="5.0"
                        className="font-mono bg-secondary/30 focus-visible:ring-rose/50 text-rose font-bold"
                      />
                      <span className="absolute right-4 top-1/2 -translate-y-1/2 text-rose/50 font-mono">%</span>
                    </div>
                  </div>
                  <div>
                    <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-1.5 block">
                      Max Weekly Drawdown
                    </label>
                    <div className="relative">
                      <Input
                        type="number"
                        value={systemConfig.riskMaxWeeklyLoss}
                        onChange={(e) =>
                          setSystemConfig({
                            ...systemConfig,
                            riskMaxWeeklyLoss: parseFloat(e.target.value) || 0,
                          })
                        }
                        step="0.1"
                        min="1.0"
                        max="10.0"
                        className="font-mono bg-secondary/30 focus-visible:ring-rose/50 text-rose font-bold"
                      />
                      <span className="absolute right-4 top-1/2 -translate-y-1/2 text-rose/50 font-mono">%</span>
                    </div>
                  </div>
                  <div>
                    <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-1.5 block">
                      Absolute Max Drawdown
                    </label>
                    <div className="relative">
                      <Input
                        type="number"
                        value={systemConfig.riskMaxDrawdown}
                        onChange={(e) =>
                          setSystemConfig({
                            ...systemConfig,
                            riskMaxDrawdown: parseFloat(e.target.value) || 0,
                          })
                        }
                        step="0.1"
                        min="5.0"
                        max="20.0"
                        className="font-mono bg-secondary/30 focus-visible:ring-rose/50 text-rose font-bold"
                      />
                      <span className="absolute right-4 top-1/2 -translate-y-1/2 text-rose/50 font-mono">%</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Data Providers */}
          <TabsContent value="data" className="m-0">
             <Card variant="flat">
              <CardHeader>
                <CardTitle className="text-sm font-semibold text-foreground uppercase tracking-wider flex items-center gap-2">
                  <Globe className="w-4 h-4 text-sky" />
                  Telemetry Oracles
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 stagger-children">
                  {[
                    { name: "Alpha Vantage", key: "alpha_vantage", free: true, desc: "25 req/day free" },
                    { name: "Polygon.io", key: "polygon", free: false, desc: "Real-time feeds" },
                    { name: "FRED", key: "fred", free: true, desc: "Economic series" },
                    { name: "CoinGecko", key: "coingecko", free: true, desc: "Crypto metrics" },
                    { name: "Finnhub", key: "finnhub", free: true, desc: "60 calls/min free" },
                    { name: "Twelve Data", key: "twelvedata", free: true, desc: "800 credits/day" },
                    { name: "SEC EDGAR", key: "sec_edgar", free: true, desc: "Filing parsing" },
                    { name: "ECB", key: "ecb", free: true, desc: "FX reference rates" },
                  ].map((provider) => (
                    <div
                      key={provider.key}
                      className="p-4 rounded-xl bg-secondary/10 border border-border/30 hover:border-sky/30 hover:bg-secondary/20 transition-all hover-lift"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-bold text-foreground font-mono truncate">
                          {provider.name}
                        </span>
                        <Badge
                          variant={provider.free ? "emerald" : "amber"}
                          className="text-[8px] font-bold uppercase tracking-widest px-1.5 py-0"
                        >
                          {provider.free ? "FREE" : "PRO"}
                        </Badge>
                      </div>
                      <p className="text-[10px] text-muted-foreground uppercase tracking-widest font-medium mb-3 h-4">
                        {provider.desc}
                      </p>
                      <Input
                        placeholder="sk-..."
                        type="password"
                        className="text-xs bg-background/50 h-8 border-border/40 focus-visible:ring-sky/50"
                      />
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* System */}
          <TabsContent value="system" className="m-0">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card variant="flat">
                <CardHeader>
                  <CardTitle className="text-sm font-semibold text-foreground uppercase tracking-wider flex items-center gap-2">
                    <Server className="w-4 h-4 text-emerald" />
                    Process Parameters
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-5">
                  <div>
                    <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-1.5 block">
                      Diagnostic Output Level
                    </label>
                    <Select
                      value={systemConfig.logLevel}
                      onValueChange={(v) =>
                        setSystemConfig({ ...systemConfig, logLevel: v })
                      }
                    >
                      <SelectTrigger className="bg-secondary/20 h-10 font-mono font-bold focus:ring-emerald/50">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="DEBUG" className="font-mono">DEBUG</SelectItem>
                        <SelectItem value="INFO" className="font-mono">INFO</SelectItem>
                        <SelectItem value="WARNING" className="font-mono">WARNING</SelectItem>
                        <SelectItem value="ERROR" className="font-mono text-rose">ERROR</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </CardContent>
              </Card>

              <Card variant="flat">
                <CardHeader>
                  <CardTitle className="text-sm font-semibold text-foreground uppercase tracking-wider flex items-center gap-2">
                    <Cpu className="w-4 h-4 text-purple" />
                    Module Activation
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 stagger-children">
                  {[
                    {
                      key: "enableWebSocket",
                      label: "WebSocket Server",
                      desc: "Stream live telemetry data",
                      icon: <Globe className="w-5 h-5 text-sky" />,
                      color: "sky"
                    },
                    {
                      key: "enableAuditLog",
                      label: "Cryptographic Audit Log",
                      desc: "Append-only tracking of all decisions",
                      icon: <Shield className="w-5 h-5 text-emerald" />,
                      color: "emerald"
                    },
                    {
                      key: "autoRestart",
                      label: "Autonomous Process Resurrection",
                      desc: "Daemon restarts failed agent threads",
                      icon: <RefreshCw className="w-5 h-5 text-purple" />,
                      color: "purple"
                    },
                    {
                      key: "notificationsEnabled",
                      label: "High Priority Alerts",
                      desc: "Push OS-level notifications",
                      icon: <Bell className="w-5 h-5 text-amber" />,
                      color: "amber"
                    },
                  ].map((toggle) => (
                    <div
                      key={toggle.key}
                      className="flex items-center justify-between p-4 rounded-xl bg-secondary/10 border border-border/30 hover:bg-secondary/20 transition-colors"
                    >
                      <div className="flex items-center gap-4">
                        <div className="p-2 rounded-lg bg-background/50 border border-border/50 shadow-sm">
                          {toggle.icon}
                        </div>
                        <div>
                          <p className="text-sm font-bold text-foreground">
                            {toggle.label}
                          </p>
                          <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mt-0.5">
                            {toggle.desc}
                          </p>
                        </div>
                      </div>
                      <Switch
                        checked={
                          systemConfig[
                            toggle.key as keyof typeof systemConfig
                          ] as boolean
                        }
                        onCheckedChange={(checked) =>
                          setSystemConfig({
                            ...systemConfig,
                            [toggle.key]: checked,
                          })
                        }
                        className={systemConfig[toggle.key as keyof typeof systemConfig] ? `shadow-[0_0_10px_rgba(var(--${toggle.color}-rgb),0.5)]` : ""}
                      />
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
