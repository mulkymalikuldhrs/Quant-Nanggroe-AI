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
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Settings className="w-6 h-6 text-muted-foreground" />
            System Settings
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Configure Quant Nanggroe AI trading system
          </p>
        </div>
        <div className="flex items-center gap-3">
          {saveMessage && (
            <Badge variant="emerald" className="text-xs">
              {saveMessage}
            </Badge>
          )}
          <Button
            variant="cyan"
            onClick={handleSave}
            disabled={saving}
            className="gap-2 cursor-pointer"
          >
            {saving ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                Save Changes
              </>
            )}
          </Button>
        </div>
      </div>

      <Tabs defaultValue="llm">
        <TabsList className="flex-wrap">
          <TabsTrigger value="llm">LLM Providers</TabsTrigger>
          <TabsTrigger value="trading">Trading</TabsTrigger>
          <TabsTrigger value="risk">Risk Limits</TabsTrigger>
          <TabsTrigger value="data">Data Providers</TabsTrigger>
          <TabsTrigger value="system">System</TabsTrigger>
        </TabsList>

        {/* LLM Providers */}
        <TabsContent value="llm">
          <div className="mt-4 space-y-4">
            {llmProviders.map((provider) => (
              <Card key={provider.id} className="glass-card">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div
                        className={`p-2 rounded-lg ${
                          provider.enabled
                            ? "bg-cyan/10 border border-cyan/20"
                            : "bg-secondary/30 border border-border/30"
                        }`}
                      >
                        <span className="text-lg">{provider.icon}</span>
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="text-sm font-semibold text-foreground">
                            {provider.name}
                          </h3>
                          <Badge
                            variant="outline"
                            className="text-[10px]"
                          >
                            {provider.model}
                          </Badge>
                          {provider.enabled && (
                            <Badge variant="emerald" className="text-[9px]">
                              Active
                            </Badge>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground font-mono">
                          {provider.baseUrl}
                        </p>
                      </div>
                    </div>
                    <Switch
                      checked={provider.enabled}
                      onCheckedChange={() => toggleProvider(provider.id)}
                    />
                  </div>

                  {provider.enabled && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div>
                        <label className="text-xs font-medium text-muted-foreground mb-1.5 block">
                          Model
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
                        />
                      </div>
                      <div>
                        <label className="text-xs font-medium text-muted-foreground mb-1.5 block">
                          API Key
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
                            className="pr-10"
                          />
                          <button
                            onClick={() => toggleApiKeyVisibility(provider.id)}
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground cursor-pointer"
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
                        <label className="text-xs font-medium text-muted-foreground mb-1.5 block">
                          Base URL
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
                          className="font-mono text-xs"
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
        <TabsContent value="trading">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-4">
            <Card className="glass-card">
              <CardHeader>
                <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-cyan" />
                  Default LLM Configuration
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="text-xs font-medium text-muted-foreground mb-1.5 block">
                    Default Provider
                  </label>
                  <Select
                    value={systemConfig.defaultProvider}
                    onValueChange={(v) =>
                      setSystemConfig({ ...systemConfig, defaultProvider: v })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {llmProviders
                        .filter((p) => p.enabled)
                        .map((p) => (
                          <SelectItem key={p.id} value={p.id}>
                            {p.icon} {p.name}
                          </SelectItem>
                        ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="text-xs font-medium text-muted-foreground mb-1.5 block">
                    Default Model
                  </label>
                  <Input
                    value={systemConfig.defaultModel}
                    onChange={(e) =>
                      setSystemConfig({
                        ...systemConfig,
                        defaultModel: e.target.value,
                      })
                    }
                    className="font-mono"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-muted-foreground mb-1.5 block">
                    Temperature
                  </label>
                  <Input
                    type="number"
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
                  />
                </div>
              </CardContent>
            </Card>

            <Card className="glass-card">
              <CardHeader>
                <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                  <Database className="w-4 h-4 text-purple" />
                  Backtest Configuration
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-medium text-muted-foreground mb-1.5 block">
                      Default Commission
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
                    />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-muted-foreground mb-1.5 block">
                      Default Slippage
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
                    />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-muted-foreground mb-1.5 block">
                      Initial Capital
                    </label>
                    <Input
                      type="number"
                      value={systemConfig.backtestInitialCapital}
                      onChange={(e) =>
                        setSystemConfig({
                          ...systemConfig,
                          backtestInitialCapital:
                            parseInt(e.target.value) || 100000,
                        })
                      }
                    />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-muted-foreground mb-1.5 block">
                      Data Cache TTL (s)
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
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Risk Limits */}
        <TabsContent value="risk">
          <div className="mt-4">
            <Card className="glass-card">
              <CardHeader>
                <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                  <Shield className="w-4 h-4 text-rose" />
                  Constitutional Risk Limits
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="p-3 rounded-lg border border-amber/20 bg-amber/5">
                  <div className="flex items-start gap-2">
                    <AlertCircle className="w-4 h-4 text-amber shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-amber">
                        Constitutional Limits
                      </p>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        These limits cannot be overridden by agents. They are
                        enforced at the execution level and are the final
                        safeguard against excessive risk.
                      </p>
                    </div>
                  </div>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-medium text-muted-foreground mb-1.5 block">
                      Max Risk Per Trade (%)
                    </label>
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
                    />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-muted-foreground mb-1.5 block">
                      Max Daily Loss (%)
                    </label>
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
                    />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-muted-foreground mb-1.5 block">
                      Max Weekly Loss (%)
                    </label>
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
                    />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-muted-foreground mb-1.5 block">
                      Max Drawdown (%)
                    </label>
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
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Data Providers */}
        <TabsContent value="data">
          <div className="mt-4">
            <Card className="glass-card">
              <CardHeader>
                <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                  <Globe className="w-4 h-4 text-sky" />
                  Data Provider Configuration
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {[
                    { name: "Alpha Vantage", key: "alpha_vantage", free: true, desc: "25 req/day free" },
                    { name: "Polygon.io", key: "polygon", free: false, desc: "Real-time & historical" },
                    { name: "FRED", key: "fred", free: true, desc: "Economic data, 120/min" },
                    { name: "CoinGecko", key: "coingecko", free: true, desc: "Crypto data" },
                    { name: "Finnhub", key: "finnhub", free: true, desc: "60 calls/min free" },
                    { name: "Twelve Data", key: "twelvedata", free: true, desc: "800 credits/day" },
                    { name: "SEC EDGAR", key: "sec_edgar", free: true, desc: "No key needed" },
                    { name: "ECB", key: "ecb", free: true, desc: "FX reference rates" },
                  ].map((provider) => (
                    <div
                      key={provider.key}
                      className="p-3 rounded-lg bg-secondary/20 border border-border/30"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium text-foreground">
                          {provider.name}
                        </span>
                        <Badge
                          variant={provider.free ? "emerald" : "amber"}
                          className="text-[9px]"
                        >
                          {provider.free ? "Free Tier" : "Paid"}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {provider.desc}
                      </p>
                      <Input
                        placeholder={`Enter ${provider.name} API key...`}
                        type="password"
                        className="mt-2 text-xs"
                      />
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* System */}
        <TabsContent value="system">
          <div className="mt-4 grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="glass-card">
              <CardHeader>
                <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                  <Server className="w-4 h-4 text-cyan" />
                  System Configuration
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="text-xs font-medium text-muted-foreground mb-1.5 block">
                    Log Level
                  </label>
                  <Select
                    value={systemConfig.logLevel}
                    onValueChange={(v) =>
                      setSystemConfig({ ...systemConfig, logLevel: v })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="DEBUG">Debug</SelectItem>
                      <SelectItem value="INFO">Info</SelectItem>
                      <SelectItem value="WARNING">Warning</SelectItem>
                      <SelectItem value="ERROR">Error</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </CardContent>
            </Card>

            <Card className="glass-card">
              <CardHeader>
                <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-purple" />
                  Feature Toggles
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {[
                  {
                    key: "enableWebSocket",
                    label: "WebSocket Server",
                    desc: "Real-time updates via WebSocket",
                    icon: <Globe className="w-4 h-4" />,
                  },
                  {
                    key: "enableAuditLog",
                    label: "Audit Logging",
                    desc: "Track all system actions",
                    icon: <Shield className="w-4 h-4" />,
                  },
                  {
                    key: "autoRestart",
                    label: "Auto Restart",
                    desc: "Restart failed agents automatically",
                    icon: <RefreshCw className="w-4 h-4" />,
                  },
                  {
                    key: "notificationsEnabled",
                    label: "Notifications",
                    desc: "Push notifications for events",
                    icon: <Bell className="w-4 h-4" />,
                  },
                ].map((toggle) => (
                  <div
                    key={toggle.key}
                    className="flex items-center justify-between p-3 rounded-lg bg-secondary/20"
                  >
                    <div className="flex items-center gap-3">
                      <div className="text-muted-foreground">{toggle.icon}</div>
                      <div>
                        <p className="text-sm font-medium text-foreground">
                          {toggle.label}
                        </p>
                        <p className="text-xs text-muted-foreground">
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
                    />
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
