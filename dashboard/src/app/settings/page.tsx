"use client";

import React, { useState } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { ScrollArea } from "@/components/ui/scroll-area";
import { mockExchanges } from "@/lib/mock-data";
import {
  Settings,
  Key,
  Shield,
  Bot,
  Server,
  Eye,
  EyeOff,
  Save,
} from "lucide-react";

interface ApiKeyEntry {
  id: string;
  name: string;
  key: string;
  status: "connected" | "disconnected" | "error";
  lastUsed: string;
}

export default function SettingsPage() {
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [apiKeys] = useState<ApiKeyEntry[]>([
    { id: "alpaca", name: "Alpaca API", key: "PKALPACA****X9K2", status: "connected", lastUsed: "2m ago" },
    { id: "binance", name: "Binance API", key: "BIN****mK7p", status: "connected", lastUsed: "5m ago" },
    { id: "coinbase", name: "Coinbase API", key: "CBPRO****j3Ln", status: "connected", lastUsed: "12m ago" },
    { id: "polygon", name: "Polygon.io", key: "POLY****qR5v", status: "connected", lastUsed: "1h ago" },
    { id: "openai", name: "OpenAI API", key: "sk-****wM8p", status: "connected", lastUsed: "3m ago" },
    { id: "anthropic", name: "Anthropic API", key: "sk-ant-****kL2n", status: "disconnected", lastUsed: "never" },
  ]);

  const [riskLimits, setRiskLimits] = useState({
    maxPositionSize: 10,
    maxSectorExposure: 40,
    maxVaR: 10000,
    maxDrawdown: 5,
    maxLeverage: 2.0,
    defaultStopLoss: 2,
    defaultTakeProfit: 5,
  });

  const [agentModels, setAgentModels] = useState<Record<string, string>>({
    research: "gpt-4o",
    market_intel: "gpt-4o",
    portfolio: "claude-3.5-sonnet",
    risk: "gpt-4o",
    strategy: "gpt-4o",
    execution: "gpt-4o-mini",
    crypto: "gpt-4o",
    forex: "gpt-4o",
    macro: "claude-3.5-sonnet",
    prediction: "gpt-4o-mini",
    trader: "gpt-4o",
  });

  const [systemToggles, setSystemToggles] = useState<Record<string, boolean>>({
    liveTrading: true,
    autoRebalance: false,
    killSwitchOnLoss: false,
    emotionalLockout: true,
    riskChecksRequired: true,
    logAllDecisions: true,
    paperTradingMode: false,
    notificationsEnabled: true,
  });

  const toggleShowKey = (id: string) => {
    setShowKeys((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const modelOptions = [
    { value: "gpt-4o", label: "GPT-4o" },
    { value: "gpt-4o-mini", label: "GPT-4o Mini" },
    { value: "claude-3.5-sonnet", label: "Claude 3.5 Sonnet" },
    { value: "claude-3-haiku", label: "Claude 3 Haiku" },
    { value: "gemini-1.5-pro", label: "Gemini 1.5 Pro" },
    { value: "local-llama3", label: "Local Llama 3" },
  ];

  const agentNames: Record<string, string> = {
    research: "Research",
    market_intel: "Market Intel",
    portfolio: "Portfolio",
    risk: "Risk",
    strategy: "Strategy",
    execution: "Execution",
    crypto: "Crypto",
    forex: "Forex",
    macro: "Macro",
    prediction: "Prediction",
    trader: "Trader",
  };

  return (
    <div className="space-y-4 animate-slide-up">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <Settings className="w-5 h-5 text-white/60" />
          Settings
        </h1>
        <p className="text-sm text-white/40 mt-0.5">API keys, risk limits, model selection & system config</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* API Keys */}
        <ChartCard title="API Keys" subtitle="Encrypted credential management" action={<Badge variant="info"><Key className="w-3 h-3 mr-1" />Encrypted</Badge>}>
          <ScrollArea className="max-h-96">
            <div className="space-y-2">
              {apiKeys.map((apiKey) => (
                <div
                  key={apiKey.id}
                  className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]"
                >
                  <div className="flex items-center gap-3">
                    <Key className="w-3.5 h-3.5 text-white/30" />
                    <div>
                      <p className="text-xs font-medium text-white/70">{apiKey.name}</p>
                      <div className="flex items-center gap-2">
                        <p className="text-[10px] font-mono text-white/30">
                          {showKeys[apiKey.id] ? apiKey.key.replace(/\*/g, "X") : apiKey.key}
                        </p>
                        <button onClick={() => toggleShowKey(apiKey.id)}>
                          {showKeys[apiKey.id] ? (
                            <EyeOff className="w-3 h-3 text-white/20" />
                          ) : (
                            <Eye className="w-3 h-3 text-white/20" />
                          )}
                        </button>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={apiKey.status === "connected" ? "success" : apiKey.status === "error" ? "danger" : "warning"} className="text-[10px]">
                      {apiKey.status}
                    </Badge>
                    <span className="text-[10px] text-white/20">{apiKey.lastUsed}</span>
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>
        </ChartCard>

        {/* Exchange Credentials */}
        <ChartCard title="Exchange Credentials" subtitle="Connected exchanges" action={<Badge variant="success">8/10 Active</Badge>}>
          <ScrollArea className="max-h-96">
            <div className="space-y-2">
              {mockExchanges.map((exchange) => (
                <div
                  key={exchange.id}
                  className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]"
                >
                  <div className="flex items-center gap-3">
                    <Server className="w-3.5 h-3.5 text-white/30" />
                    <div>
                      <p className="text-xs font-medium text-white/70">{exchange.name}</p>
                      <p className="text-[10px] text-white/30">{exchange.type}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={exchange.status === "connected" ? "success" : "danger"} className="text-[10px]">
                      {exchange.status}
                    </Badge>
                    <Button variant="ghost" size="sm" className="h-6 px-2 text-[10px]">
                      Configure
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>
        </ChartCard>
      </div>

      {/* Risk Limits */}
      <ChartCard title="Risk Limits" subtitle="System-wide risk boundaries" action={<Badge variant="warning"><Shield className="w-3 h-3 mr-1" />Constitutional</Badge>}>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { label: "Max Position Size", key: "maxPositionSize", value: riskLimits.maxPositionSize, unit: "%", max: 100 },
            { label: "Max Sector Exposure", key: "maxSectorExposure", value: riskLimits.maxSectorExposure, unit: "%", max: 100 },
            { label: "Max VaR", key: "maxVaR", value: riskLimits.maxVaR, unit: "$", max: 50000 },
            { label: "Max Drawdown", key: "maxDrawdown", value: riskLimits.maxDrawdown, unit: "%", max: 20 },
            { label: "Max Leverage", key: "maxLeverage", value: riskLimits.maxLeverage, unit: "x", max: 5 },
            { label: "Default Stop Loss", key: "defaultStopLoss", value: riskLimits.defaultStopLoss, unit: "%", max: 10 },
            { label: "Default Take Profit", key: "defaultTakeProfit", value: riskLimits.defaultTakeProfit, unit: "%", max: 20 },
          ].map((item) => (
            <div key={item.key} className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
              <p className="text-xs text-white/40 mb-2">{item.label}</p>
              <div className="flex items-center gap-2">
                <Input
                  type="number"
                  value={item.value}
                  onChange={(e) =>
                    setRiskLimits((prev) => ({
                      ...prev,
                      [item.key]: parseFloat(e.target.value) || 0,
                    }))
                  }
                  className="w-20 text-center"
                />
                <span className="text-xs text-white/30">{item.unit}</span>
              </div>
            </div>
          ))}
        </div>
        <Button variant="glow" className="mt-4">
          <Save className="w-3.5 h-3.5 mr-1.5" />
          Save Risk Limits
        </Button>
      </ChartCard>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Agent Model Selection */}
        <ChartCard title="Agent Model Selection" subtitle="LLM model per agent" action={<Badge variant="info"><Bot className="w-3 h-3 mr-1" />11 Agents</Badge>}>
          <ScrollArea className="max-h-80">
            <div className="space-y-2">
              {Object.entries(agentModels).map(([agentId, model]) => (
                <div key={agentId} className="flex items-center justify-between p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                  <span className="text-xs font-medium text-white/60">{agentNames[agentId] || agentId}</span>
                  <Select
                    value={model}
                    onChange={(e) => setAgentModels((prev) => ({ ...prev, [agentId]: e.target.value }))}
                    options={modelOptions}
                    className="w-40"
                  />
                </div>
              ))}
            </div>
          </ScrollArea>
        </ChartCard>

        {/* System Toggles */}
        <ChartCard title="System Configuration" subtitle="Feature toggles & preferences">
          <div className="space-y-3">
            {[
              { key: "liveTrading", label: "Live Trading", desc: "Enable real money trading", variant: "danger" },
              { key: "autoRebalance", label: "Auto Rebalance", desc: "Automatically rebalance portfolio" },
              { key: "killSwitchOnLoss", label: "Kill Switch on Loss", desc: "Auto kill switch at drawdown limit", variant: "warning" },
              { key: "emotionalLockout", label: "Emotional Lockout", desc: "Lock trading during high emotion" },
              { key: "riskChecksRequired", label: "Risk Checks Required", desc: "Require all 9 risk checks before trading" },
              { key: "logAllDecisions", label: "Log All Decisions", desc: "Record every agent decision" },
              { key: "paperTradingMode", label: "Paper Trading Mode", desc: "Simulate trades without real execution", variant: "info" },
              { key: "notificationsEnabled", label: "Notifications", desc: "Push notifications for events" },
            ].map((toggle) => (
              <div
                key={toggle.key}
                className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]"
              >
                <div>
                  <p className="text-sm text-white/70">{toggle.label}</p>
                  <p className="text-xs text-white/30">{toggle.desc}</p>
                </div>
                <Switch
                  checked={systemToggles[toggle.key]}
                  onCheckedChange={(checked) =>
                    setSystemToggles((prev) => ({ ...prev, [toggle.key]: checked }))
                  }
                />
              </div>
            ))}
          </div>
        </ChartCard>
      </div>

      {/* Data Provider Preferences */}
      <ChartCard title="Data Provider Preferences" subtitle="Primary data sources">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {[
            { category: "Equity Data", primary: "Alpaca", secondary: "Polygon" },
            { category: "Crypto Data", primary: "Binance", secondary: "CoinGecko" },
            { category: "Forex Data", primary: "Alpaca", secondary: "TwelveData" },
            { category: "Economic Data", primary: "FRED", secondary: "SEC EDGAR" },
          ].map((provider) => (
            <div key={provider.category} className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
              <p className="text-xs text-white/40 mb-2">{provider.category}</p>
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-white/50">Primary</span>
                  <Badge variant="success" className="text-[10px]">{provider.primary}</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-white/50">Secondary</span>
                  <Badge variant="default" className="text-[10px]">{provider.secondary}</Badge>
                </div>
              </div>
            </div>
          ))}
        </div>
      </ChartCard>
    </div>
  );
}
