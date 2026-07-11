import { useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";

export type RealOrganismState = {
  problemsScanned: number;
  ideasGenerated: number;
  productsBuilt: number;
  revenue: number;
  generation: number;
  agentsActive: number;
  agentsTerminated: number;
  engineRuns: { engine: string; status: string; count: number }[];
};

export function useOrganismReal() {
  const qc = useQueryClient();

  const sessionQuery = useQuery({
    queryKey: ["auth", "session"],
    queryFn: async () => {
      const { data, error } = await supabase.auth.getSession();
      if (error) throw error;
      return data.session;
    },
  });

  const profileQuery = useQuery({
    queryKey: ["profile"],
    enabled: !!sessionQuery.data,
    queryFn: async () => {
      const { data, error } = await supabase
        .from("profiles")
        .select("organization_id, role, display_name")
        .eq("user_id", sessionQuery.data!.user.id)
        .maybeSingle();
      if (error) throw error;
      return data;
    },
  });

  const logsQuery = useQuery({
    queryKey: ["engine_logs"],
    enabled: !!profileQuery.data?.organization_id,
    queryFn: async () => {
      const orgId = profileQuery.data!.organization_id;
      const { data, error } = await supabase
        .from("engine_logs")
        .select("id, level, source, message, created_at")
        .eq("organization_id", orgId)
        .order("created_at", { ascending: false })
        .limit(100);
      if (error) throw error;
      return data;
    },
    refetchInterval: 4000,
  });

  const metricsQuery = useQuery({
    queryKey: ["metrics"],
    enabled: !!profileQuery.data?.organization_id,
    queryFn: async () => {
      const orgId = profileQuery.data!.organization_id;

      // Fetch counts in parallel
      const [
        { count: rawCount },
        { count: ideaCount },
        { count: factoryCount },
        { count: growthCount },
        { data: allRuns },
      ] = await Promise.all([
        supabase.from("problem_raw").select("id", { count: "exact", head: true }).eq("organization_id", orgId),
        supabase.from("idea_candidates").select("id", { count: "exact", head: true }).eq("organization_id", orgId),
        supabase.from("engine_runs").select("id", { count: "exact", head: true }).eq("organization_id", orgId).eq("engine", "factory").eq("status", "success"),
        supabase.from("engine_runs").select("id", { count: "exact", head: true }).eq("organization_id", orgId).eq("engine", "growth").eq("status", "success"),
        supabase.from("engine_runs").select("engine, status").eq("organization_id", orgId),
      ]);

      // Count factory successes as products built
      const productsBuilt = factoryCount ?? 0;

      // Aggregate engine run counts
      const runMap: Record<string, { engine: string; status: string; count: number }> = {};
      (allRuns ?? []).forEach((r: any) => {
        const key = `${r.engine}-${r.status}`;
        if (!runMap[key]) runMap[key] = { engine: r.engine, status: r.status, count: 0 };
        runMap[key].count++;
      });

      // Calculate a simple revenue estimate based on growth runs
      let revenue = 0;
      // Revenue would come from actual growth run meta data in production
      // For now, estimate from number of successful growth runs
      const growthSuccessCount = growthCount ?? 0;
      revenue = growthSuccessCount * 24.99; // Simulated subscription revenue

      return {
        problemsScanned: rawCount ?? 0,
        ideasGenerated: ideaCount ?? 0,
        productsBuilt,
        revenue: Math.round(revenue * 100) / 100,
        generation: 1,
        agentsActive: 0,
        agentsTerminated: 0,
        engineRuns: Object.values(runMap),
      } satisfies RealOrganismState;
    },
    refetchInterval: 6000,
  });

  // Get latest engine run results for display
  const engineRunsQuery = useQuery({
    queryKey: ["engine_runs_latest"],
    enabled: !!profileQuery.data?.organization_id,
    queryFn: async () => {
      const orgId = profileQuery.data!.organization_id;
      const { data, error } = await supabase
        .from("engine_runs")
        .select("id, engine, status, started_at, finished_at, meta")
        .eq("organization_id", orgId)
        .order("started_at", { ascending: false })
        .limit(20);
      if (error) throw error;
      return data;
    },
    refetchInterval: 5000,
  });

  // Get top idea candidates
  const ideasQuery = useQuery({
    queryKey: ["idea_candidates"],
    enabled: !!profileQuery.data?.organization_id,
    queryFn: async () => {
      const orgId = profileQuery.data!.organization_id;
      const { data, error } = await supabase
        .from("idea_candidates")
        .select("id, theme, score, summary, created_at")
        .eq("organization_id", orgId)
        .order("score", { ascending: false })
        .limit(10);
      if (error) throw error;
      return data;
    },
    refetchInterval: 8000,
  });

  // Get problem sources
  const sourcesQuery = useQuery({
    queryKey: ["problem_sources"],
    enabled: !!profileQuery.data?.organization_id,
    queryFn: async () => {
      const orgId = profileQuery.data!.organization_id;
      const { data, error } = await supabase
        .from("problem_sources")
        .select("id, type, name, url, enabled")
        .eq("organization_id", orgId);
      if (error) throw error;
      return data;
    },
  });

  // Get scheduler config
  const schedulerQuery = useQuery({
    queryKey: ["scheduler_config"],
    enabled: !!profileQuery.data?.organization_id,
    queryFn: async () => {
      const orgId = profileQuery.data!.organization_id;
      const { data, error } = await supabase
        .from("scheduler_config")
        .select("enabled, kill_switch, max_iterations, timeout_seconds, error_threshold")
        .eq("organization_id", orgId)
        .maybeSingle();
      if (error) throw error;
      return data;
    },
  });

  const invalidateAll = useCallback(async () => {
    await Promise.all([
      qc.invalidateQueries({ queryKey: ["engine_logs"] }),
      qc.invalidateQueries({ queryKey: ["metrics"] }),
      qc.invalidateQueries({ queryKey: ["engine_runs_latest"] }),
      qc.invalidateQueries({ queryKey: ["idea_candidates"] }),
    ]);
  }, [qc]);

  const runSense = useCallback(async () => {
    const { error } = await supabase.functions.invoke("ingest-sense", { body: {} });
    if (error) throw error;
    await invalidateAll();
  }, [invalidateAll]);

  const runDecision = useCallback(async () => {
    const { error } = await supabase.functions.invoke("run-decision", { body: {} });
    if (error) throw error;
    await invalidateAll();
  }, [invalidateAll]);

  const runFactory = useCallback(async () => {
    const { error } = await supabase.functions.invoke("run-factory", { body: {} });
    if (error) throw error;
    await invalidateAll();
  }, [invalidateAll]);

  const runGrowth = useCallback(async () => {
    const { error } = await supabase.functions.invoke("run-growth", { body: {} });
    if (error) throw error;
    await invalidateAll();
  }, [invalidateAll]);

  const runDecisionClient = useCallback(
    async ({ theme, score, summary, evidence }: { theme: string; score: number; summary: string; evidence: any }) => {
      const orgId = profileQuery.data?.organization_id;
      if (!orgId) throw new Error("Org belum siap");
      const { error } = await supabase.from("idea_candidates").insert({
        organization_id: orgId,
        theme,
        score,
        summary,
        evidence,
      });
      if (error) throw error;
      await invalidateAll();
    },
    [profileQuery.data?.organization_id, invalidateAll]
  );

  return {
    session: sessionQuery.data,
    profile: profileQuery.data,
    logs: logsQuery.data ?? [],
    logsLoading: logsQuery.isLoading,
    state: metricsQuery.data,
    stateLoading: metricsQuery.isLoading,
    engineRuns: engineRunsQuery.data ?? [],
    ideas: ideasQuery.data ?? [],
    sources: sourcesQuery.data ?? [],
    schedulerConfig: schedulerQuery.data,
    runSense,
    runDecision,
    runFactory,
    runGrowth,
    runDecisionClient,
  };
}
