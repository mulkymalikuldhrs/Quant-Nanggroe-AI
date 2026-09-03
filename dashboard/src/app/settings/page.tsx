"use client";
export const dynamic = "force-dynamic";

import React, { useState, useCallback, useEffect } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { ScrollArea } from "@/components/ui/scroll-area";
import { apiRequest } from "@/lib/api-client";
import { ErrorBoundary } from "@/components/shared/error-boundary";

import {
  Settings,
  Key,
  Shield,
  Bot,
  Server,
  Eye,
  EyeOff,
  Save,
  Plus,
  Trash2,
  Link,
  Check,
  X,
  RefreshCw,
  Activity,
} from "lucide-react";

interface ApiKeyEntry {
  id: string; name: string; key: string; secret?: string;
  status: "connected" | "disconnected" | "error"; lastUsed?: string;
}

interface BrokerEntry {
  id: string; name: string; type: string;
  login: string; password: string; server: string;
  leverage: string; status: string; accountType?: string;
}

interface ExchangeEntry {
  id: string; name: string; type: string;
  apiKey: string; secret: string; status: string;
}

interface LlmKeyEntry {
  id: string; provider: string; key: string; status: string;
}

function SettingsContent() {
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [saving, setSaving] = useState<string | null>(null);
  const [saveMsg, setSaveMsg] = useState<{ok: boolean; text: string} | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [apiKeys, setApiKeys] = useState<ApiKeyEntry[]>([]);
  const [brokers, setBrokers] = useState<BrokerEntry[]>([]);
  const [exchanges, setExchanges] = useState<ExchangeEntry[]>([]);
  const [llmKeys, setLlmKeys] = useState<LlmKeyEntry[]>([]);
  const [riskLimits, setRiskLimits] = useState<Record<string, number>>({});
  const [perSymbol, setPerSymbol] = useState<Record<string, Record<string, number>>>({});
  const [newPerSymbol, setNewPerSymbol] = useState<{ symbol: string; key: string; value: string }>({ symbol: "", key: "maxRiskPerTrade", value: "" });
  const [perRegime, setPerRegime] = useState<Record<string, Record<string, number>>>({});
  const [newPerRegime, setNewPerRegime] = useState<{ regime: string; key: string; value: string }>({ regime: "trending", key: "maxRiskPerTrade", value: "" });
  const [systemToggles, setSystemToggles] = useState<Record<string, boolean>>({});

  const [agentModels, setAgentModels] = useState<Record<string, string>>({
    research: "gpt-4o", market_intel: "gpt-4o", portfolio: "claude-3.5-sonnet",
    risk: "gpt-4o", strategy: "gpt-4o", execution: "gpt-4o-mini",
    crypto: "gpt-4o", forex: "gpt-4o", macro: "claude-3.5-sonnet",
    prediction: "gpt-4o-mini", trader: "gpt-4o",
  });

  const load = useCallback(async () => {
    try {
      const d = await apiRequest<{
        apiKeys?: ApiKeyEntry[]; brokers?: BrokerEntry[]; exchanges?: ExchangeEntry[];
        llmKeys?: LlmKeyEntry[]; riskLimits?: Record<string, number>; systemToggles?: Record<string, boolean>;
      }>("/api/credentials");
      setApiKeys(d.apiKeys ?? []);
      setBrokers(d.brokers ?? []);
      setExchanges(d.exchanges ?? []);
      setLlmKeys(d.llmKeys ?? []);
      // riskLimits from credentials (legacy) + live risk-config (entire QNA follows)
      let mergedRisk = { ...(d.riskLimits ?? {}) };
      try {
        const rc = await apiRequest<Record<string, any>>("/api/risk-config");
        if (rc.maxRiskPerTrade != null) mergedRisk.maxRiskPerTrade = Math.round(rc.maxRiskPerTrade * 100 * 100) / 100;
        if (rc.maxDailyLoss != null) mergedRisk.maxDailyLoss = Math.round(rc.maxDailyLoss * 100 * 100) / 100;
        if (rc.maxWeeklyLoss != null) mergedRisk.maxWeeklyLoss = Math.round(rc.maxWeeklyLoss * 100 * 100) / 100;
        if (rc.maxDrawdown != null) mergedRisk.maxDrawdown = Math.round(rc.maxDrawdown * 100 * 100) / 100;
        if (rc.maxPositionSize != null) mergedRisk.maxPositionSize = Math.round(rc.maxPositionSize * 100);
        if (rc.maxLeverage != null) mergedRisk.maxLeverage = rc.maxLeverage;
        if (rc.maxDailyTrades != null) mergedRisk.maxDailyTrades = rc.maxDailyTrades;
        if (rc.minRiskReward != null) mergedRisk.minRiskReward = rc.minRiskReward;
        if (rc.maxCorrelatedPositions != null) mergedRisk.maxCorrelatedPositions = rc.maxCorrelatedPositions;
        if (rc.perSymbol) setPerSymbol(rc.perSymbol as Record<string, Record<string, number>>);
        if (rc.perRegime) setPerRegime(rc.perRegime as Record<string, Record<string, number>>);
      } catch { /* risk-config optional */ }
      setRiskLimits(mergedRisk);
      setSystemToggles(d.systemToggles ?? {});
    } catch {
      setError("Backend unavailable — configure credentials via environment variables");
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const save = async (section: string, data: Record<string, unknown>) => {
    setSaving(section);
    setSaveMsg(null);
    try {
      await apiRequest("/api/credentials", { method: "PUT", body: data });
      // riskLimits → also push to live risk-config (entire QNA follows without restart)
      if (section === "riskLimits" && data.riskLimits) {
        const rl = data.riskLimits as Record<string, number>;
        const payload: Record<string, number> = {};
        if (rl.maxRiskPerTrade != null) payload.maxRiskPerTrade = rl.maxRiskPerTrade / 100;
        if (rl.maxDailyLoss != null) payload.maxDailyLoss = rl.maxDailyLoss / 100;
        if (rl.maxWeeklyLoss != null) payload.maxWeeklyLoss = rl.maxWeeklyLoss / 100;
        if (rl.maxDrawdown != null) payload.maxDrawdown = rl.maxDrawdown / 100;
        if (rl.maxPositionSize != null) payload.maxPositionSize = rl.maxPositionSize / 100;
        if (rl.maxLeverage != null) payload.maxLeverage = rl.maxLeverage;
        if (rl.maxDailyTrades != null) payload.maxDailyTrades = rl.maxDailyTrades;
        if (rl.minRiskReward != null) payload.minRiskReward = rl.minRiskReward;
        if (Object.keys(payload).length) {
          await apiRequest("/api/risk-config", { method: "PUT", body: payload });
        }
      }
      setSaveMsg({ ok: true, text: `${section} saved — live risk updated` });
    } catch (e: unknown) {
      setSaveMsg({ ok: false, text: `${section}: ${e instanceof Error ? e.message : 'error'}` });
    }
    setSaving(null);
    setTimeout(() => setSaveMsg(null), 3000);
  };

  const toggleShowKey = (id: string) => setShowKeys(v => ({ ...v, [id]: !v[id] }));

  const modelOptions = [
    { value: "gpt-4o", label: "GPT-4o" },
    { value: "gpt-4o-mini", label: "GPT-4o Mini" },
    { value: "claude-3.5-sonnet", label: "Claude 3.5 Sonnet" },
    { value: "claude-3-haiku", label: "Claude 3 Haiku" },
    { value: "gemini-1.5-pro", label: "Gemini 1.5 Pro" },
    { value: "local-llama3", label: "Local Llama 3" },
  ];
  const agentNames: Record<string, string> = {
    research: "Research", market_intel: "Market Intel", portfolio: "Portfolio",
    risk: "Risk", strategy: "Strategy", execution: "Execution",
    crypto: "Crypto", forex: "Forex", macro: "Macro",
    prediction: "Prediction", trader: "Trader",
  };

  const [newBroker, setNewBroker] = useState<Partial<BrokerEntry>>({ type: "mt5" });
  const addBroker = () => {
    if (!newBroker.name || !newBroker.login) return;
    const id = newBroker.id || newBroker.name.toLowerCase().replace(/\s+/g, "_");
    if (brokers.find(b => b.id === id)) return;
    setBrokers([...brokers, { id, name: newBroker.name, type: newBroker.type || "mt5", login: newBroker.login || "", password: newBroker.password || "", server: newBroker.server || "", leverage: newBroker.leverage || "1:500", status: "disconnected" }]);
    setNewBroker({ type: "mt5" });
  };
  const removeBroker = (id: string) => setBrokers(brokers.filter(b => b.id !== id));

  const brokerTypes = [
    { value: "mt5", label: "MetaTrader 5" },
    { value: "mt4", label: "MetaTrader 4" },
    { value: "ctrader", label: "cTrader" },
  ];

  return (
    <div className="space-y-4 animate-slide-up">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Settings className="w-5 h-5 text-white/60" />
            Settings
          </h1>
          <p className="text-sm text-white/40 mt-0.5">Credentials, brokers, risk limits & system config</p>
        </div>
        {saveMsg && (
          <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium ${
            saveMsg.ok ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"
          }`}>
            {saveMsg.ok ? <Check className="w-3 h-3" /> : <X className="w-3 h-3" />}
            {saveMsg.text}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* API Keys */}
        <ChartCard title="API Keys" subtitle="Third-party API credentials" action={
          <Button variant="glow" size="sm" className="h-6 text-[10px]" onClick={() => save("apiKeys", { apiKeys })} disabled={saving === "apiKeys"}>
            {saving === "apiKeys" ? <RefreshCw className="w-3 h-3 mr-1 animate-spin" /> : <Save className="w-3 h-3 mr-1" />}
            Save Keys
          </Button>
        }>
          <ScrollArea className="max-h-64">
            <div className="space-y-2">
              {apiKeys.map((apiKey) => (
                <div key={apiKey.id} className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <Key className="w-3.5 h-3.5 text-white/30 shrink-0" />
                    <div className="min-w-0">
                      <p className="text-xs font-medium text-white/70">{apiKey.name}</p>
                      <div className="flex items-center gap-2">
                        <input
                          className="text-[10px] font-mono text-white/30 bg-transparent border-0 outline-none w-28"
                          value={showKeys[apiKey.id] ? apiKey.key : apiKey.key.replace(/.(?=.{4})/g, "*")}
                          onChange={e => { const k = [...apiKeys]; const i = k.findIndex(a => a.id === apiKey.id); if (i>=0) { k[i] = {...k[i], key: e.target.value}; setApiKeys(k); } }}
                        />
                        <button onClick={() => toggleShowKey(apiKey.id)}>
                          {showKeys[apiKey.id] ? <EyeOff className="w-3 h-3 text-white/20" /> : <Eye className="w-3 h-3 text-white/20" />}
                        </button>
                      </div>
                    </div>
                  </div>
                  <Badge variant={apiKey.status === "connected" ? "success" : apiKey.status === "error" ? "danger" : "warning"} className="text-[10px] shrink-0">
                    {apiKey.status}
                  </Badge>
                </div>
              ))}
            </div>
          </ScrollArea>
        </ChartCard>

        {/* Exchange Credentials */}
        <ChartCard title="Exchange Credentials" subtitle="Connected exchanges" action={
          <Button variant="glow" size="sm" className="h-6 text-[10px]" onClick={() => save("exchanges", { exchanges })} disabled={saving === "exchanges"}>
            {saving === "exchanges" ? <RefreshCw className="w-3 h-3 mr-1 animate-spin" /> : <Save className="w-3 h-3 mr-1" />}
            Save Exchanges
          </Button>
        }>
          <ScrollArea className="max-h-64">
            <div className="space-y-2">
              {(exchanges || []).map((exchange) => (
                <div key={exchange.id} className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                  <div className="flex items-center gap-3">
                    <Server className="w-3.5 h-3.5 text-white/30" />
                    <div>
                      <p className="text-xs font-medium text-white/70">{exchange.name}</p>
                      <p className="text-[10px] text-white/30">{exchange.type}</p>
                    </div>
                  </div>
                  <Badge variant={exchange.status === "connected" ? "success" : "danger"} className="text-[10px]">
                    {exchange.status}
                  </Badge>
                </div>
              ))}
            </div>
          </ScrollArea>
        </ChartCard>
      </div>

      {/* Broker Credentials (Multi-Broker) */}
      <ChartCard title="Broker Credentials" subtitle="MT4/MT5/cTrader account management — Exness, IC Markets, etc." action={
        <Badge variant="info"><Link className="w-3 h-3 mr-1" />{brokers.length} Broker{brokers.length !== 1 ? "s" : ""}</Badge>
      }>
        <div className="space-y-3 mb-4">
          {brokers.map((broker) => (
            <div key={broker.id} className="flex flex-wrap items-end gap-2 p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
              <div className="flex-1 min-w-[120px]">
                <label className="text-[10px] text-white/30 mb-1 block">Name</label>
                <input className="w-full text-xs bg-white/5 border border-white/10 rounded px-2 py-1.5 text-white/80"
                  value={broker.name} onChange={e => setBrokers(brokers.map(b => b.id === broker.id ? {...b, name: e.target.value} : b))} />
              </div>
              <div className="w-20">
                <label className="text-[10px] text-white/30 mb-1 block">Type</label>
                <select className="w-full text-xs bg-white/5 border border-white/10 rounded px-2 py-1.5 text-white/80"
                  value={broker.type} onChange={e => setBrokers(brokers.map(b => b.id === broker.id ? {...b, type: e.target.value} : b))}>
                  {brokerTypes.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </div>
              <div className="flex-1 min-w-[100px]">
                <label className="text-[10px] text-white/30 mb-1 block">Login</label>
                <input className="w-full text-xs bg-white/5 border border-white/10 rounded px-2 py-1.5 text-white/80"
                  value={broker.login} onChange={e => setBrokers(brokers.map(b => b.id === broker.id ? {...b, login: e.target.value} : b))} />
              </div>
              <div className="flex-1 min-w-[100px]">
                <label className="text-[10px] text-white/30 mb-1 block">Password</label>
                <input type="password" className="w-full text-xs bg-white/5 border border-white/10 rounded px-2 py-1.5 text-white/80"
                  value={broker.password} onChange={e => setBrokers(brokers.map(b => b.id === broker.id ? {...b, password: e.target.value} : b))} />
              </div>
              <div className="flex-1 min-w-[120px]">
                <label className="text-[10px] text-white/30 mb-1 block">Server</label>
                <input className="w-full text-xs bg-white/5 border border-white/10 rounded px-2 py-1.5 text-white/80"
                  value={broker.server} onChange={e => setBrokers(brokers.map(b => b.id === broker.id ? {...b, server: e.target.value} : b))} />
              </div>
              <div className="w-20">
                <label className="text-[10px] text-white/30 mb-1 block">Leverage</label>
                <input className="w-full text-xs bg-white/5 border border-white/10 rounded px-2 py-1.5 text-white/80"
                  value={broker.leverage} onChange={e => setBrokers(brokers.map(b => b.id === broker.id ? {...b, leverage: e.target.value} : b))} />
              </div>
              <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-red-400/50 hover:text-red-400"
                onClick={() => removeBroker(broker.id)}>
                <Trash2 className="w-3.5 h-3.5" />
              </Button>
            </div>
          ))}
          {/* Add broker form */}
          <div className="flex flex-wrap items-end gap-2 p-3 rounded-lg bg-white/[0.04] border border-dashed border-white/[0.08]">
            <div className="flex-1 min-w-[120px]">
              <label className="text-[10px] text-white/30 mb-1 block">Broker Name</label>
              <input className="w-full text-xs bg-white/5 border border-white/10 rounded px-2 py-1.5 text-white/80"
                placeholder="Exness" value={newBroker.name || ""}
                onChange={e => setNewBroker({...newBroker, name: e.target.value, id: e.target.value.toLowerCase().replace(/\s+/g,"_")})} />
            </div>
            <div className="w-20">
              <label className="text-[10px] text-white/30 mb-1 block">Type</label>
              <select className="w-full text-xs bg-white/5 border border-white/10 rounded px-2 py-1.5 text-white/80"
                value={newBroker.type || "mt5"} onChange={e => setNewBroker({...newBroker, type: e.target.value})}>
                {brokerTypes.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
            <div className="flex-1 min-w-[100px]">
              <label className="text-[10px] text-white/30 mb-1 block">Login</label>
              <input className="w-full text-xs bg-white/5 border border-white/10 rounded px-2 py-1.5 text-white/80"
                placeholder="414016058" value={newBroker.login || ""}
                onChange={e => setNewBroker({...newBroker, login: e.target.value})} />
            </div>
            <div className="flex-1 min-w-[100px]">
              <label className="text-[10px] text-white/30 mb-1 block">Password</label>
              <input type="password" className="w-full text-xs bg-white/5 border border-white/10 rounded px-2 py-1.5 text-white/80"
                placeholder="password" value={newBroker.password || ""}
                onChange={e => setNewBroker({...newBroker, password: e.target.value})} />
            </div>
            <div className="flex-1 min-w-[120px]">
              <label className="text-[10px] text-white/30 mb-1 block">Server</label>
              <input className="w-full text-xs bg-white/5 border border-white/10 rounded px-2 py-1.5 text-white/80"
                placeholder="Exness-MT5Trial6" value={newBroker.server || ""}
                onChange={e => setNewBroker({...newBroker, server: e.target.value})} />
            </div>
            <div className="w-20">
              <label className="text-[10px] text-white/30 mb-1 block">Leverage</label>
              <input className="w-full text-xs bg-white/5 border border-white/10 rounded px-2 py-1.5 text-white/80"
                placeholder="1:2000" value={newBroker.leverage || ""}
                onChange={e => setNewBroker({...newBroker, leverage: e.target.value})} />
            </div>
            <Button variant="ghost" size="sm" className="h-8 text-emerald-400/70 hover:text-emerald-400"
              onClick={addBroker}>
              <Plus className="w-3.5 h-3.5 mr-1" />Add
            </Button>
          </div>
        </div>
        <Button variant="glow" size="sm" onClick={() => save("brokers", { brokers })} disabled={saving === "brokers"}>
          {saving === "brokers" ? <RefreshCw className="w-3.5 h-3.5 mr-1.5 animate-spin" /> : <Save className="w-3.5 h-3.5 mr-1.5" />}
          Save All Brokers
        </Button>
      </ChartCard>

      {/* LLM API Keys */}
      <ChartCard title="LLM API Keys" subtitle="AI provider credentials" action={
        <Badge variant="info"><Bot className="w-3 h-3 mr-1" />{llmKeys.length} Key{llmKeys.length !== 1 ? "s" : ""}</Badge>
      }>
        <div className="space-y-2">
          {(["openai", "anthropic", "groq", "deepseek"] as const).map(provider => {
            const entry = llmKeys.find(k => k.provider === provider);
            return (
              <div key={provider} className="flex items-center gap-3 p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                <span className="text-xs font-medium text-white/50 w-20 capitalize">{provider}</span>
                <input
                  className="flex-1 text-xs bg-white/5 border border-white/10 rounded px-2 py-1.5 text-white/60 font-mono"
                  placeholder="sk-..." value={entry?.key || ""}
                  onChange={e => {
                    const arr = llmKeys.filter(k => k.provider !== provider);
                    if (e.target.value) arr.push({ id: provider, provider, key: e.target.value, status: "disconnected" });
                    setLlmKeys(arr);
                  }}
                />
              </div>
            );
          })}
        </div>
        <Button variant="glow" size="sm" className="mt-3" onClick={() => save("llmKeys", { llmKeys })} disabled={saving === "llmKeys"}>
          {saving === "llmKeys" ? <RefreshCw className="w-3.5 h-3.5 mr-1.5 animate-spin" /> : <Save className="w-3.5 h-3.5 mr-1.5" />}
          Save LLM Keys
        </Button>
      </ChartCard>

      {/* Risk Limits — LIVE, entire QNA follows */}
      <ChartCard title="Risk Limits" subtitle="Live — entire QNA follows (per-trade, daily, weekly, drawdown) — no restart needed" action={
        <Badge variant="warning"><Shield className="w-3 h-3 mr-1" />Constitutional • Live</Badge>
      }>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { label: "Max Risk / Trade", key: "maxRiskPerTrade", unit: "%", max: 2, step: 0.1 },
            { label: "Max Daily Loss", key: "maxDailyLoss", unit: "%", max: 5, step: 0.1 },
            { label: "Max Weekly Loss", key: "maxWeeklyLoss", unit: "%", max: 10, step: 0.1 },
            { label: "Max Drawdown", key: "maxDrawdown", unit: "%", max: 30, step: 1 },
            { label: "Max Position Size", key: "maxPositionSize", unit: "%", max: 50, step: 1 },
            { label: "Max Leverage", key: "maxLeverage", unit: "x", max: 10, step: 0.5 },
            { label: "Max Daily Trades", key: "maxDailyTrades", unit: "", max: 20, step: 1 },
            { label: "Min Risk Reward", key: "minRiskReward", unit: ":1", max: 5, step: 0.5 },
            { label: "Max Correlated", key: "maxCorrelatedPositions", unit: "", max: 10, step: 1 },
          ].map((item) => (
            <div key={item.key} className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
              <p className="text-xs text-white/40 mb-2">{item.label}</p>
              <div className="flex items-center gap-2">
                <Input
                  type="number" value={riskLimits[item.key] ?? 0}
                  onChange={(e) => setRiskLimits(p => ({ ...p, [item.key]: parseFloat(e.target.value) || 0 }))}
                  className="w-20 text-center"
                />
                <span className="text-xs text-white/30">{item.unit}</span>
              </div>
            </div>
          ))}
        </div>
        <Button variant="glow" className="mt-4" onClick={() => save("riskLimits", { riskLimits })} disabled={saving === "riskLimits"}>
          {saving === "riskLimits" ? <RefreshCw className="w-3.5 h-3.5 mr-1.5 animate-spin" /> : <Save className="w-3.5 h-3.5 mr-1.5" />}
          Save Risk Limits
        </Button>
      </ChartCard>

      {/* Per-Symbol Risk Overrides — more configurable */}
      <ChartCard title="Per-Symbol Risk" subtitle="More configurable — overrides global (e.g., EURUSD 0.3%, XAU 0.7%, all 28) — entire QNA follows" action={
        <Badge variant="info"><Shield className="w-3 h-3 mr-1" />Per-Symbol</Badge>
      }>
        <div className="space-y-2">
          {Object.entries(perSymbol).map(([sym, ov]) => (
            <div key={sym} className="flex items-center gap-2 p-2 rounded-lg bg-white/[0.02] border border-white/[0.04]">
              <span className="text-xs font-mono text-white/70 w-20">{sym}</span>
              <span className="text-xs text-white/30 flex-1 truncate">{Object.entries(ov).map(([k, v]) => `${k}=${v}`).join(", ")}</span>
              <Button variant="ghost" size="sm" className="h-7 text-xs text-red-400/70" onClick={async () => {
                const next = { ...perSymbol }; delete next[sym];
                setPerSymbol(next);
                await apiRequest("/api/risk-config", { method: "PUT", body: { perSymbol: next } });
              }}><Trash2 className="w-3 h-3" /></Button>
            </div>
          ))}
          <div className="flex flex-wrap items-end gap-2 p-3 rounded-lg bg-white/[0.04] border border-dashed border-white/[0.08]">
            <div className="flex-1 min-w-[100px]">
              <label className="text-[10px] text-white/30 mb-1 block">Symbol (e.g., EURUSD, XAUUSD, all 28)</label>
              <Input placeholder="EURUSD" value={newPerSymbol.symbol} onChange={(e) => setNewPerSymbol({ ...newPerSymbol, symbol: e.target.value.toUpperCase() })} />
            </div>
            <div className="w-40">
              <label className="text-[10px] text-white/30 mb-1 block">Key</label>
              <Select value={newPerSymbol.key} onChange={(e) => setNewPerSymbol({ ...newPerSymbol, key: e.target.value })} options={[
                { value: "maxRiskPerTrade", label: "Risk/Trade %" },
                { value: "maxPositionSize", label: "Pos Size %" },
                { value: "maxDailyLoss", label: "Daily Loss %" },
                { value: "maxWeeklyLoss", label: "Weekly Loss %" },
              ]} />
            </div>
            <div className="w-28">
              <label className="text-[10px] text-white/30 mb-1 block">Value</label>
              <Input type="number" placeholder="0.003" value={newPerSymbol.value} onChange={(e) => setNewPerSymbol({ ...newPerSymbol, value: e.target.value })} />
            </div>
            <Button variant="glow" size="sm" onClick={async () => {
              if (!newPerSymbol.symbol || !newPerSymbol.value) return;
              const v = parseFloat(newPerSymbol.value);
              const k = newPerSymbol.key;
              // UI value is human: % or fraction? For Risk/Trade, UI is % 0.3 → backend 0.003
              const backendVal = k.includes("Risk") || k.includes("Loss") || k.includes("Drawdown") || k.includes("PositionSize") ? v / 100 : v;
              const next = { ...perSymbol, [newPerSymbol.symbol]: { ...(perSymbol[newPerSymbol.symbol] || {}), [k]: backendVal } };
              setPerSymbol(next);
              await apiRequest("/api/risk-config", { method: "PUT", body: { perSymbol: next } });
              setNewPerSymbol({ symbol: "", key: "maxRiskPerTrade", value: "" });
            }}><Plus className="w-3.5 h-3.5 mr-1" />Add Override</Button>
          </div>
        </div>
      </ChartCard>

      {/* Per-Regime Risk Overrides — v8.0.23 (A1) */}
      <ChartCard title="Per-Regime Risk" subtitle="More configurable — overrides global by HMM regime (trending, ranging, crisis, bullish, bearish, neutral) — entire QNA follows" action={
        <Badge variant="info"><Activity className="w-3 h-3 mr-1" />Per-Regime</Badge>
      }>
        <div className="space-y-2">
          {Object.entries(perRegime).map(([regime, ov]) => (
            <div key={regime} className="flex items-center gap-2 p-2 rounded-lg bg-white/[0.02] border border-white/[0.04]">
              <span className="text-xs font-mono text-white/70 w-24">{regime}</span>
              <span className="text-xs text-white/30 flex-1 truncate">{Object.entries(ov).map(([k, v]) => `${k}=${v}`).join(", ")}</span>
              <Button variant="ghost" size="sm" className="h-7 text-xs text-red-400/70" onClick={async () => {
                const next = { ...perRegime }; delete next[regime];
                setPerRegime(next);
                await apiRequest("/api/risk-config", { method: "PUT", body: { perRegime: next } });
              }}><Trash2 className="w-3 h-3" /></Button>
            </div>
          ))}
          <div className="flex flex-wrap items-end gap-2 p-3 rounded-lg bg-white/[0.04] border border-dashed border-white/[0.08]">
            <div className="w-40">
              <label className="text-[10px] text-white/30 mb-1 block">Regime</label>
              <Select value={newPerRegime.regime} onChange={(e) => setNewPerRegime({ ...newPerRegime, regime: e.target.value })} options={[
                { value: "trending", label: "trending" },
                { value: "ranging", label: "ranging" },
                { value: "crisis", label: "crisis" },
                { value: "bullish", label: "bullish" },
                { value: "bearish", label: "bearish" },
                { value: "neutral", label: "neutral" },
              ]} />
            </div>
            <div className="w-40">
              <label className="text-[10px] text-white/30 mb-1 block">Key</label>
              <Select value={newPerRegime.key} onChange={(e) => setNewPerRegime({ ...newPerRegime, key: e.target.value })} options={[
                { value: "maxRiskPerTrade", label: "Risk/Trade %" },
                { value: "maxPositionSize", label: "Pos Size %" },
                { value: "maxDailyLoss", label: "Daily Loss %" },
                { value: "maxWeeklyLoss", label: "Weekly Loss %" },
              ]} />
            </div>
            <div className="w-28">
              <label className="text-[10px] text-white/30 mb-1 block">Value</label>
              <Input type="number" placeholder="0.003" value={newPerRegime.value} onChange={(e) => setNewPerRegime({ ...newPerRegime, value: e.target.value })} />
            </div>
            <Button variant="glow" size="sm" onClick={async () => {
              if (!newPerRegime.regime || !newPerRegime.value) return;
              const v = parseFloat(newPerRegime.value);
              const k = newPerRegime.key;
              const backendVal = k.includes("Risk") || k.includes("Loss") || k.includes("Drawdown") || k.includes("PositionSize") ? v / 100 : v;
              const next = { ...perRegime, [newPerRegime.regime]: { ...(perRegime[newPerRegime.regime] || {}), [k]: backendVal } };
              setPerRegime(next);
              await apiRequest("/api/risk-config", { method: "PUT", body: { perRegime: next } });
              setNewPerRegime({ regime: "trending", key: "maxRiskPerTrade", value: "" });
            }}><Plus className="w-3.5 h-3.5 mr-1" />Add Override</Button>
          </div>
        </div>
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
                    onChange={(e) => setAgentModels(p => ({ ...p, [agentId]: e.target.value }))}
                    options={modelOptions}
                    className="w-40"
                  />
                </div>
              ))}
            </div>
          </ScrollArea>
        </ChartCard>

        {/* System Toggles */}
        <ChartCard title="System Configuration" subtitle="Feature toggles & preferences" action={
          <Button variant="glow" size="sm" className="h-6 text-[10px]" onClick={() => save("systemToggles", { systemToggles })} disabled={saving === "systemToggles"}>
            {saving === "systemToggles" ? <RefreshCw className="w-3 h-3 mr-1 animate-spin" /> : <Save className="w-3 h-3 mr-1" />}
            Save Config
          </Button>
        }>
          <div className="space-y-3">
            {[
              { key: "liveTrading", label: "Live Trading", desc: "Enable real money trading", variant: "danger" },
              { key: "autoRebalance", label: "Auto Rebalance", desc: "Automatically rebalance portfolio" },
              { key: "killSwitchOnLoss", label: "Kill Switch on Loss", desc: "Auto kill switch at drawdown limit", variant: "warning" },
              { key: "emotionalLockout", label: "Emotional Lockout", desc: "Lock trading during high emotion" },
              { key: "riskChecksRequired", label: "Risk Checks Required", desc: "Require all 9 risk checks before trading" },
              { key: "paperTradingMode", label: "Paper Trading Mode", desc: "Simulate trades without real execution", variant: "info" },
            ].map((toggle) => (
              <div key={toggle.key} className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                <div>
                  <p className="text-sm text-white/70">{toggle.label}</p>
                  <p className="text-xs text-white/30">{toggle.desc}</p>
                </div>
                <Switch
                  checked={systemToggles[toggle.key] ?? false}
                  onCheckedChange={(c: boolean) => setSystemToggles(p => ({ ...p, [toggle.key]: c }))}
                />
              </div>
            ))}
          </div>
        </ChartCard>
      </div>
    </div>
  );
}

export default function SettingsPage() {
  return (
    <ErrorBoundary>
      <SettingsContent />
    </ErrorBoundary>
  );
}
