import { Eye, Brain, Factory, TrendingUp, Database, Shield, Bot, Zap } from "lucide-react";
import { NeuralBackground } from "@/components/NeuralBackground";
import { Header } from "@/components/Header";
import { OrganismCore } from "@/components/OrganismCore";
import { OrganEngine } from "@/components/OrganEngine";
import { OrganismCard, OrganismCardHeader, OrganismCardTitle, OrganismCardContent } from "@/components/ui/organism-card";
import { MetricDisplay } from "@/components/ui/metric-display";
import { ActivityLog } from "@/components/ui/activity-log";
import { Progress } from "@/components/ui/progress";
import { AuthGate } from "@/components/AuthGate";
import { useOrganismReal } from "@/hooks/useOrganismReal";
import { useToast } from "@/hooks/use-toast";
import { Button } from "@/components/ui/button";
import { useState } from "react";


export default function Index() {
  const { toast } = useToast();
  const { state, logs, engineRuns, ideas, runSense, runDecision, runFactory, runGrowth } = useOrganismReal();
  const [runningEngine, setRunningEngine] = useState<string | null>(null);

  const logEntries = logs.map((l: any) => ({
    id: l.id,
    timestamp: new Date(l.created_at),
    type: l.level,
    source: l.source,
    message: l.message,
  }));

  // Compute engine statuses from real data
  const getEngineStatus = (engineName: string): "online" | "offline" | "warning" | "error" | "processing" | "idle" => {
    const runs = engineRuns.filter((r: any) => r.engine === engineName);
    if (runs.length === 0) return "idle";
    const latest = runs[0];
    if (latest.status === "running") return "processing";
    if (latest.status === "success") return "online";
    if (latest.status === "failed") return "error";
    if (latest.status === "killed") return "warning";
    return "idle";
  };

  // Count runs per engine
  const getEngineCount = (engineName: string, status?: string): number => {
    return engineRuns.filter((r: any) => {
      if (status) return r.engine === engineName && r.status === status;
      return r.engine === engineName;
    }).length;
  };

  const handleRunEngine = async (name: string, fn: () => Promise<void>) => {
    setRunningEngine(name);
    try {
      await fn();
      toast({ title: `${name} Engine`, description: "Run completed successfully." });
    } catch (e: any) {
      toast({ title: `${name} failed`, description: e?.message ?? "Error", variant: "destructive" });
    } finally {
      setRunningEngine(null);
    }
  };

  const onRunSense = () => handleRunEngine("Sense", runSense);
  const onRunDecision = () => handleRunEngine("Decision", runDecision);
  const onRunFactory = () => handleRunEngine("Factory", runFactory);
  const onRunGrowth = () => handleRunEngine("Growth", runGrowth);



  // Compute health from scheduler/immune data
  const systemHealth = state?.engineRuns
    ? Math.min(100, Math.max(20, 100 - (getEngineCount("factory", "failed") + getEngineCount("growth", "failed")) * 10))
    : 87;

  return (
    <AuthGate>
      <div className="min-h-screen bg-background text-foreground relative overflow-hidden">
        <NeuralBackground />
        
        <div className="relative z-10">
          <Header 
            organismName="ORGANISM-ALPHA" 
            generation={state?.generation ?? 1} 
            status="online" 
          />

          <main className="container mx-auto px-4 py-8">
          {/* Hero Section - Core Status */}
          <section className="mb-12">
            <div className="grid lg:grid-cols-3 gap-8 items-center">
              {/* Left Metrics */}
              <OrganismCard variant="default" size="lg" className="lg:col-span-1">
                <OrganismCardHeader>
                  <Zap className="w-5 h-5 text-primary" />
                  <OrganismCardTitle>Vital Signs</OrganismCardTitle>
                </OrganismCardHeader>
                <OrganismCardContent className="space-y-6">
                  <MetricDisplay 
                    label="Problems Scanned" 
                    value={(state?.problemsScanned ?? 0).toLocaleString()} 
                    variant="primary"
                    trend="up"
                    trendValue="real-time"
                  />
                  <MetricDisplay 
                    label="Ideas Generated" 
                    value={state?.ideasGenerated ?? 0} 
                    variant="default"
                    trend="up"
                    trendValue="from DB"
                  />
                  <MetricDisplay 
                    label="Products Built" 
                    value={state?.productsBuilt ?? 0} 
                    variant="accent"
                    size="sm"
                  />
                  <div className="pt-2">
                    <span className="text-xs text-muted-foreground uppercase tracking-wider">System Health</span>
                    <Progress value={systemHealth} className="mt-2 h-2" />
                    <span className="text-xs text-success mt-1 block">{systemHealth}% Optimal</span>
                  </div>

                  <div className="grid grid-cols-2 gap-3 pt-2">
                    <Button onClick={onRunSense} disabled={runningEngine === "Sense"}>
                      {runningEngine === "Sense" ? "Running..." : "Run Sense"}
                    </Button>
                    <Button onClick={onRunDecision} variant="secondary" disabled={runningEngine === "Decision"}>
                      {runningEngine === "Decision" ? "Running..." : "Run Decision"}
                    </Button>
                    <Button onClick={onRunFactory} variant="outline" disabled={runningEngine === "Factory"}>
                      {runningEngine === "Factory" ? "Building..." : "Run Factory"}
                    </Button>
                    <Button onClick={onRunGrowth} variant="outline" disabled={runningEngine === "Growth"}>
                      {runningEngine === "Growth" ? "Growing..." : "Run Growth"}
                    </Button>
                  </div>
                </OrganismCardContent>
              </OrganismCard>

              {/* Center - Core Visualization */}
              <div className="flex flex-col items-center justify-center py-8 lg:col-span-1">
                <OrganismCore status="alive" className="mb-16" />
                <div className="text-center mt-8">
                  <h2 className="text-2xl font-bold gradient-text-primary mb-2">
                    Autonomous Life System
                  </h2>
                  <p className="text-sm text-muted-foreground max-w-md">
                    Self-evolving organism discovering problems, building solutions, 
                    and generating revenue without human intervention.
                  </p>
                </div>
              </div>

              {/* Right Metrics */}
              <OrganismCard variant="factory" size="lg" className="lg:col-span-1">
                <OrganismCardHeader>
                  <TrendingUp className="w-5 h-5 text-accent" />
                  <OrganismCardTitle className="text-accent">Revenue Engine</OrganismCardTitle>
                </OrganismCardHeader>
                <OrganismCardContent className="space-y-6">
                  <MetricDisplay 
                    label="Total Revenue" 
                    value={`$${(state?.revenue ?? 0).toFixed(2)}`} 
                    variant="accent"
                    trend="up"
                    trendValue="estimated"
                  />
                  <MetricDisplay 
                    label="Growth Runs" 
                    value={getEngineCount("growth", "success")} 
                    variant="success"
                    size="sm"
                  />
                  <MetricDisplay 
                    label="Failed Runs" 
                    value={getEngineCount("factory", "failed") + getEngineCount("growth", "failed")} 
                    variant="destructive"
                    size="sm"
                  />
                  <div className="pt-2">
                    <span className="text-xs text-muted-foreground uppercase tracking-wider">Efficiency</span>
                    <Progress value={Math.max(10, 100 - (getEngineCount("factory", "failed") + getEngineCount("growth", "failed")) * 15)} className="mt-2 h-2" />
                    <span className="text-xs text-primary mt-1 block">
                      {Math.max(10, 100 - (getEngineCount("factory", "failed") + getEngineCount("growth", "failed")) * 15)}% Optimal
                    </span>
                  </div>

                  {/* Top Ideas */}
                  {ideas.length > 0 && (
                    <div className="pt-2 border-t border-border/30">
                      <span className="text-xs text-muted-foreground uppercase tracking-wider">Top Idea</span>
                      <p className="text-sm text-primary font-medium mt-1 truncate">
                        {ideas[0]?.theme ?? "None yet"}
                      </p>
                      <span className="text-xs text-muted-foreground">Score: {ideas[0]?.score ?? 0}</span>
                    </div>
                  )}
                </OrganismCardContent>
              </OrganismCard>
            </div>
          </section>

          {/* Organ Engines Grid */}
          <section className="mb-12">
            <h3 className="text-lg font-semibold mb-6 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
              Organ Engines
            </h3>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              <OrganEngine
                name="Sense Engine"
                icon={Eye}
                variant="sense"
                status={getEngineStatus("sense")}
                description="Scanning the digital world for human problems and pain points."
                metrics={[
                  { label: "Sources", value: state?.engineRuns?.filter(r => r.engine === "sense" && r.status === "success").length ?? 0, trend: "up" as const, trendValue: "runs" },
                  { label: "Scanned", value: (state?.problemsScanned ?? 0).toLocaleString() },
                ]}
              />
              <OrganEngine
                name="Decision Core"
                icon={Brain}
                variant="decision"
                status={getEngineStatus("decision")}
                description="Analyzing and scoring problems by automation potential and revenue."
                metrics={[
                  { label: "Candidates", value: state?.ideasGenerated ?? 0 },
                  { label: "Runs", value: getEngineCount("decision") },
                ]}
              />
              <OrganEngine
                name="SaaS Factory"
                icon={Factory}
                variant="factory"
                status={getEngineStatus("factory")}
                description="Building and deploying MVP solutions automatically."
                metrics={[
                  { label: "In Build", value: getEngineCount("factory", "running") },
                  { label: "Deployed", value: state?.productsBuilt ?? 0 },
                ]}
              />
              <OrganEngine
                name="Growth Engine"
                icon={TrendingUp}
                variant="growth"
                status={getEngineStatus("growth")}
                description="Marketing, content generation, and user acquisition."
                metrics={[
                  { label: "Campaigns", value: getEngineCount("growth", "success") },
                  { label: "Revenue", value: `$${(state?.revenue ?? 0).toFixed(0)}` },
                ]}
              />
              <OrganEngine
                name="Memory Engine"
                icon={Database}
                variant="memory"
                status={getEngineStatus("memory")}
                description="Recording patterns, failures, and evolution data."
                metrics={[
                  { label: "Records", value: logs.length.toLocaleString() },
                  { label: "Runs", value: getEngineCount("memory") },
                ]}
              />
              <OrganEngine
                name="Immune System"
                icon={Shield}
                variant="danger"
                status="online"
                description="Preventing runaway processes and protecting resources."
                metrics={[
                  { label: "Blocked", value: getEngineCount("factory", "failed") + getEngineCount("growth", "failed") },
                  { label: "Health", value: `${systemHealth}%` },
                ]}
              />
            </div>
          </section>

          {/* Agents & Logs Section */}
          <section className="grid lg:grid-cols-2 gap-8">
            {/* Pipeline Status */}
            <div>
              <h3 className="text-lg font-semibold mb-6 flex items-center gap-2">
                <Bot className="w-5 h-5 text-intelligence" />
                Pipeline Status
              </h3>
              <OrganismCard variant="default" size="lg" className="p-6">
                <div className="space-y-4">
                  {/* Pipeline Steps */}
                  {[
                    { name: "Sense", icon: "👁️", status: getEngineStatus("sense"), count: getEngineCount("sense", "success"), action: onRunSense },
                    { name: "Decision", icon: "🧠", status: getEngineStatus("decision"), count: getEngineCount("decision", "success"), action: onRunDecision },
                    { name: "Factory", icon: "🏭", status: getEngineStatus("factory"), count: getEngineCount("factory", "success"), action: onRunFactory },
                    { name: "Growth", icon: "📢", status: getEngineStatus("growth"), count: getEngineCount("growth", "success"), action: onRunGrowth },
                  ].map((step) => (
                    <div key={step.name} className="flex items-center justify-between py-2 border-b border-border/20 last:border-0">
                      <div className="flex items-center gap-3">
                        <span className="text-lg">{step.icon}</span>
                        <div>
                          <span className="text-sm font-medium">{step.name}</span>
                          <div className="flex items-center gap-2 mt-0.5">
                            <span className={`w-1.5 h-1.5 rounded-full ${
                              step.status === "online" ? "bg-success" :
                              step.status === "processing" ? "bg-primary animate-pulse" :
                              step.status === "error" ? "bg-destructive" :
                              step.status === "warning" ? "bg-warning" :
                              "bg-muted-foreground"
                            }`} />
                            <span className="text-xs text-muted-foreground capitalize">{step.status}</span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-xs text-muted-foreground">{step.count} runs</span>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={step.action}
                          disabled={runningEngine === step.name}
                          className="h-7 text-xs"
                        >
                          {runningEngine === step.name ? "..." : "Run"}
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Latest Factory Output */}
                {engineRuns.filter((r: any) => r.engine === "factory" && r.status === "success").length > 0 && (
                  <div className="mt-4 pt-4 border-t border-border/30">
                    <span className="text-xs text-muted-foreground uppercase tracking-wider">Latest Product</span>
                    <p className="text-sm text-accent font-medium mt-1">
                      {(engineRuns.find((r: any) => r.engine === "factory" && r.status === "success")?.meta as any)?.name ?? "Unknown"}
                    </p>
                    <span className="text-xs text-muted-foreground">
                      Theme: {(engineRuns.find((r: any) => r.engine === "factory" && r.status === "success")?.meta as any)?.theme ?? "N/A"}
                    </span>
                  </div>
                )}
              </OrganismCard>
            </div>

            {/* Activity Log */}
            <div>
              <h3 className="text-lg font-semibold mb-6 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-success animate-pulse" />
                Activity Log
              </h3>
              <OrganismCard variant="default" size="lg" className="h-[400px]">
                <ActivityLog entries={logEntries} maxHeight="360px" />
              </OrganismCard>
            </div>
          </section>

          {/* Footer */}
          <footer className="mt-16 pt-8 border-t border-border/30 text-center">
            <p className="text-xs text-muted-foreground font-mono">
              ORGANISM-ALPHA • GEN-{(state?.generation ?? 1).toString().padStart(4, "0")} • Open Source • Autonomous Life System v2.0.0
            </p>
            <p className="text-[10px] text-muted-foreground/50 mt-2">
              "Pemilik bukan bikin produk. Pemilik menciptakan spesies digital."
            </p>
            <p className="text-[10px] text-muted-foreground/40 mt-1">
              ⚠️ For Education Purpose Only — mulkymalikudhr@mail.com
            </p>
          </footer>
          </main>
        </div>
      </div>
    </AuthGate>
  );
}
