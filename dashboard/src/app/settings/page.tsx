"use client";

import { useEffect, useState } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Settings as Cog, Save } from "lucide-react";
import { useAppStore } from "@/lib/store";

interface ConfigRow { key: string; value: string; group: string; }

export default function SettingsPage() {
  const { killSwitch, autoTrade, toggleKillSwitch, toggleAutoTrade } = useAppStore();
  const [config, setConfig] = useState<ConfigRow[]>([
    { key: "PAPER_TRADING", value: "true", group: "execution" },
    { key: "MAX_POSITION_PCT", value: "5", group: "risk" },
    { key: "KELLY_FRACTION", value: "0.1", group: "risk" },
    { key: "KILL_SWITCH", value: String(killSwitch), group: "safety" },
    { key: "AUTO_TRADE", value: String(autoTrade), group: "execution" },
  ]);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setConfig((c) => c.map((r) => r.key === "KILL_SWITCH" ? { ...r, value: String(killSwitch) } : r));
  }, [killSwitch]);

  function setVal(k: string, v: string) {
    setConfig((c) => c.map((r) => r.key === k ? { ...r, value: v } : r));
    setSaved(false);
  }

  return (
    <div className="space-y-4 animate-slide-up">
      <h1 className="text-xl font-bold text-white flex items-center gap-2">
        <Cog className="w-5 h-5 text-cyan-400" /> Settings
      </h1>

      <ChartCard title="Safety Toggles" subtitle="Global runtime switches">
        <div className="space-y-3 p-2">
          <div className="flex items-center justify-between">
            <span className="text-sm text-white/70">Kill Switch</span>
            <Switch checked={killSwitch} onCheckedChange={toggleKillSwitch} />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-white/70">Auto Trade</span>
            <Switch checked={autoTrade} onCheckedChange={toggleAutoTrade} />
          </div>
        </div>
      </ChartCard>

      <ChartCard title="Configuration" subtitle="Runtime parameters">
        <div className="space-y-2 p-2">
          {config.map((r) => (
            <div key={r.key} className="flex items-center gap-2">
              <span className="text-xs text-white/50 w-40 font-mono">{r.key}</span>
              <Badge variant="default" className="text-[9px] w-16 justify-center">{r.group}</Badge>
              <Input value={r.value} onChange={(e) => setVal(r.key, e.target.value)} className="flex-1 font-mono text-xs" />
            </div>
          ))}
          <Button onClick={() => setSaved(true)} className="bg-cyan-600 hover:bg-cyan-500 mt-2">
            <Save className="w-4 h-4 mr-1" /> SAVE
          </Button>
          {saved && <p className="text-xs text-emerald-400 font-mono">✓ configuration saved (local)</p>}
        </div>
      </ChartCard>
    </div>
  );
}
