"use client";
export const dynamic = "force-dynamic";

import React, { useState, useEffect, useCallback } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { configFilesApi, type ConfigFileMeta, type ConfigFileContent } from "@/lib/api-client";
import {
  FileCode,
  Save,
  RefreshCw,
  Check,
  X,
  Plus,
  Trash2,
  Eye,
  AlertTriangle,
  Settings2,
  Database,
  Key,
  FileText,
} from "lucide-react";

type Mt5Account = {
  name: string;
  broker?: string;
  login: number | string;
  server: string;
  password?: string;
  paper?: boolean;
};

const FILE_ICON: Record<string, React.ReactNode> = {
  "mt5_accounts.yaml": <Database className="w-3.5 h-3.5" />,
  "system_config.yaml": <Settings2 className="w-3.5 h-3.5" />,
  "prompts.yaml": <FileText className="w-3.5 h-3.5" />,
  "credentials.json": <Key className="w-3.5 h-3.5" />,
  "config.yaml": <FileCode className="w-3.5 h-3.5" />,
};

export default function ConfigCenterPage() {
  const [files, setFiles] = useState<ConfigFileMeta[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [content, setContent] = useState<ConfigFileContent | null>(null);
  const [raw, setRaw] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  // mt5 structured state
  const [mt5Accounts, setMt5Accounts] = useState<Mt5Account[]>([]);
  const [mt5Mode, setMt5Mode] = useState<"structured" | "raw">("structured");

  const loadFiles = useCallback(async () => {
    try {
      const res = await configFilesApi.list();
      setFiles(res.files);
      if (!selected && res.files.length > 0) {
        setSelected(res.files[0].name);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to list config files");
    }
  }, [selected]);

  const loadFile = useCallback(async (name: string) => {
    setLoading(true);
    setError(null);
    try {
      const c = await configFilesApi.read(name);
      setContent(c);
      setRaw(c.raw || "");
      // hydrate mt5 structured
      if (name === "mt5_accounts.yaml" && c.parsed && typeof c.parsed === "object") {
        const p = c.parsed as { accounts?: Mt5Account[] };
        setMt5Accounts(Array.isArray(p.accounts) ? p.accounts : []);
        setMt5Mode("structured");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to read file");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadFiles(); }, [loadFiles]);
  useEffect(() => { if (selected) loadFile(selected); }, [selected, loadFile]);

  const saveRaw = async () => {
    if (!selected || !content) return;
    const meta = files.find(f => f.name === selected);
    if (meta && !meta.editable) {
      setMsg({ ok: false, text: `${selected} is read-only (use /api/credentials)` });
      setTimeout(() => setMsg(null), 3000);
      return;
    }
    // for mt5 structured mode, reconstruct raw from accounts
    let toSave = raw;
    if (selected === "mt5_accounts.yaml" && mt5Mode === "structured") {
      const data: Record<string, unknown> = { accounts: mt5Accounts };
      // keep raw as YAML dump via backend data path
      setSaving(true);
      setMsg(null);
      try {
        const res = await configFilesApi.write(selected, { data });
        setContent(res);
        setRaw(res.raw);
        setMsg({ ok: true, text: `${selected} saved` });
      } catch (e) {
        setMsg({ ok: false, text: e instanceof Error ? e.message : "Save failed" });
      } finally {
        setSaving(false);
        setTimeout(() => setMsg(null), 3000);
      }
      return;
    }
    setSaving(true);
    setMsg(null);
    try {
      const res = await configFilesApi.write(selected, { raw: toSave });
      setContent(res);
      setRaw(res.raw);
      setMsg({ ok: true, text: `${selected} saved` });
    } catch (e) {
      setMsg({ ok: false, text: e instanceof Error ? e.message : "Save failed" });
    } finally {
      setSaving(false);
      setTimeout(() => setMsg(null), 3000);
    }
  };

  const isMt5 = selected === "mt5_accounts.yaml";
  const selectedMeta = files.find(f => f.name === selected);

  return (
    <div className="space-y-4 animate-slide-up">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <FileCode className="w-5 h-5 text-white/60" />
            Config Center
          </h1>
          <p className="text-sm text-white/40 mt-0.5">
            Every config file under <span className="font-mono text-white/60">config/</span> — editable from the dashboard. Changes persist to disk.
          </p>
        </div>
        {msg && (
          <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium ${msg.ok ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"}`}>
            {msg.ok ? <Check className="w-3 h-3" /> : <X className="w-3 h-3" />}
            {msg.text}
          </div>
        )}
      </div>

      {error && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-300">
          <AlertTriangle className="w-3.5 h-3.5" /> {error}
        </div>
      )}

      <div className="grid grid-cols-12 gap-4">
        {/* file list */}
        <div className="col-span-12 lg:col-span-3">
          <ChartCard title="Config Files" subtitle={`${files.length} whitelisted`}>
            <div className="space-y-1.5">
              {files.map(f => (
                <button
                  key={f.name}
                  onClick={() => setSelected(f.name)}
                  className={`w-full text-left flex items-center gap-2.5 px-3 py-2.5 rounded-lg border transition-colors ${
                    selected === f.name
                      ? "bg-white/[0.06] border-white/10 text-white"
                      : "bg-white/[0.02] border-white/[0.04] text-white/60 hover:bg-white/[0.04] hover:text-white/80"
                  }`}
                >
                  <span className="text-white/40">{FILE_ICON[f.name] ?? <FileCode className="w-3.5 h-3.5" />}</span>
                  <span className="flex-1 min-w-0">
                    <span className="block text-xs font-medium truncate">{f.name}</span>
                    <span className="block text-[10px] text-white/30 truncate">{f.description}</span>
                  </span>
                  <Badge variant={f.exists ? "success" : "warning"} className="text-[10px] shrink-0">
                    {f.exists ? `${(f.size / 1024).toFixed(1)}k` : "missing"}
                  </Badge>
                </button>
              ))}
            </div>
            <div className="mt-3 flex items-center gap-2 text-[10px] text-white/20">
              <Eye className="w-3 h-3" /> secrets are masked when reading
            </div>
          </ChartCard>
        </div>

        {/* editor */}
        <div className="col-span-12 lg:col-span-9">
          <ChartCard
            title={selected ?? "Select a file"}
            subtitle={selectedMeta ? `${selectedMeta.description} — ${selectedMeta.kind.toUpperCase()}${selectedMeta.editable ? "" : " (read-only)"}` : undefined}
            action={
              <div className="flex items-center gap-2">
                {isMt5 && selectedMeta?.editable && (
                  <div className="flex rounded overflow-hidden border border-white/10 text-[10px]">
                    <button
                      onClick={() => setMt5Mode("structured")}
                      className={`px-2.5 py-1 ${mt5Mode === "structured" ? "bg-white/10 text-white" : "bg-transparent text-white/40"}`}
                    >
                      Structured
                    </button>
                    <button
                      onClick={() => setMt5Mode("raw")}
                      className={`px-2.5 py-1 ${mt5Mode === "raw" ? "bg-white/10 text-white" : "bg-transparent text-white/40"}`}
                    >
                      Raw YAML
                    </button>
                  </div>
                )}
                <Button variant="ghost" size="sm" className="h-7 text-[11px]" onClick={() => selected && loadFile(selected)} disabled={loading}>
                  <RefreshCw className={`w-3 h-3 mr-1 ${loading ? "animate-spin" : ""}`} /> Reload
                </Button>
                <Button variant="glow" size="sm" className="h-7 text-[11px]" onClick={saveRaw} disabled={saving || loading || !selectedMeta?.editable}>
                  {saving ? <RefreshCw className="w-3 h-3 mr-1 animate-spin" /> : <Save className="w-3 h-3 mr-1" />}
                  Save
                </Button>
              </div>
            }
          >
            {!selected ? (
              <p className="text-sm text-white/30 py-8 text-center">Select a config file on the left</p>
            ) : loading ? (
              <p className="text-sm text-white/30 py-8 text-center flex items-center justify-center gap-2">
                <RefreshCw className="w-4 h-4 animate-spin" /> Loading {selected}…
              </p>
            ) : !selectedMeta?.editable ? (
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-xs text-amber-300/80">
                  <AlertTriangle className="w-3.5 h-3.5" /> This file is read-only here. Use the dedicated Credentials UI.
                </div>
                <pre className="text-xs font-mono bg-black/30 border border-white/5 rounded-lg p-3 max-h-[60vh] overflow-auto text-white/60 whitespace-pre-wrap break-words">
                  {raw || "(empty — file does not exist yet)"}
                </pre>
              </div>
            ) : isMt5 && mt5Mode === "structured" ? (
              <div className="space-y-3">
                <p className="text-xs text-white/40">
                  Structured MT5 accounts editor. Passwords are written as <span className="font-mono text-white/60">$&#123;QNA_MT5_PASSWORD&#125;</span> references — set the real value in <span className="font-mono">.env</span>.
                </p>
                <div className="space-y-2">
                  {mt5Accounts.map((acc, idx) => (
                    <div key={idx} className="flex flex-wrap items-end gap-2 p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                      <div className="flex-1 min-w-[120px]">
                        <label className="text-[10px] text-white/30 mb-1 block">Name</label>
                        <input
                          className="w-full text-xs bg-white/5 border border-white/10 rounded px-2 py-1.5 text-white/80"
                          value={acc.name}
                          onChange={e => { const c = [...mt5Accounts]; c[idx] = { ...c[idx], name: e.target.value }; setMt5Accounts(c); }}
                          placeholder="MT5 Live-1"
                        />
                      </div>
                      <div className="flex-1 min-w-[90px]">
                        <label className="text-[10px] text-white/30 mb-1 block">Login</label>
                        <input
                          className="w-full text-xs bg-white/5 border border-white/10 rounded px-2 py-1.5 text-white/80"
                          value={String(acc.login)}
                          onChange={e => { const c = [...mt5Accounts]; c[idx] = { ...c[idx], login: e.target.value }; setMt5Accounts(c); }}
                          placeholder="372044706"
                        />
                      </div>
                      <div className="flex-1 min-w-[130px]">
                        <label className="text-[10px] text-white/30 mb-1 block">Server</label>
                        <input
                          className="w-full text-xs bg-white/5 border border-white/10 rounded px-2 py-1.5 text-white/80"
                          value={acc.server}
                          onChange={e => { const c = [...mt5Accounts]; c[idx] = { ...c[idx], server: e.target.value }; setMt5Accounts(c); }}
                          placeholder="ValetaxIntl-Live2"
                        />
                      </div>
                      <div className="flex-1 min-w-[130px]">
                        <label className="text-[10px] text-white/30 mb-1 block">Password ref</label>
                        <input
                          className="w-full text-xs bg-white/5 border border-white/10 rounded px-2 py-1.5 text-white/80 font-mono"
                          value={acc.password ?? "${QNA_MT5_PASSWORD}"}
                          onChange={e => { const c = [...mt5Accounts]; c[idx] = { ...c[idx], password: e.target.value }; setMt5Accounts(c); }}
                        />
                      </div>
                      <label className="flex items-center gap-1.5 text-xs text-white/50 pb-1.5">
                        <input
                          type="checkbox"
                          checked={!!acc.paper}
                          onChange={e => { const c = [...mt5Accounts]; c[idx] = { ...c[idx], paper: e.target.checked }; setMt5Accounts(c); }}
                        />
                        paper
                      </label>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 w-8 p-0 text-red-400/50 hover:text-red-400"
                        onClick={() => setMt5Accounts(mt5Accounts.filter((_, i) => i !== idx))}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  ))}
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 text-emerald-400/70 hover:text-emerald-400"
                  onClick={() => setMt5Accounts([...mt5Accounts, { name: `MT5 Live-${mt5Accounts.length + 1}`, login: "", server: "ValetaxIntl-Live2", password: "${QNA_MT5_PASSWORD}", paper: false }])}
                >
                  <Plus className="w-3.5 h-3.5 mr-1" /> Add account
                </Button>
              </div>
            ) : (
              <div className="space-y-2">
                <ScrollArea className="max-h-[60vh]">
                  <textarea
                    value={raw}
                    onChange={e => setRaw(e.target.value)}
                    spellCheck={false}
                    className="w-full min-h-[420px] text-xs font-mono bg-black/30 border border-white/10 rounded-lg p-3 text-white/80 leading-relaxed focus:outline-none focus:border-white/20"
                    placeholder={content?.kind === "yaml" ? "# YAML — edit and Save" : "{ /* JSON */ }"}
                  />
                </ScrollArea>
                <p className="text-[10px] text-white/20">
                  Raw {content?.kind?.toUpperCase()} — validated on save. Invalid syntax → 422 with details.
                </p>
              </div>
            )}
          </ChartCard>
        </div>
      </div>
    </div>
  );
}
