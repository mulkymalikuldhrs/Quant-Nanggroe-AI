// Edge Function: run-decision
// Scores problem_clean rows using sentiment + automation + money potential,
// then optionally calls an AI model (OpenAI-compatible) to pick the best theme.
// Persists idea_candidates and engine_logs.

import { serve } from "https://deno.land/std@0.168.0/http/function_handler.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

// ---- Scoring helpers (ported from decision/index.js) ----

function analyzeSentiment(text: string): number {
  const neg = ["susah","ribet","gagal","error","bug","mati","rugi","bikin cape","mahal","rumit","hard","difficult","frustrating","annoying","pain"];
  const pos = ["mantap","bagus","senang","suka","easy","simple","great","love","awesome"];
  const lower = text.toLowerCase();
  let s = 0;
  neg.forEach(w => { if (lower.includes(w)) s -= 1; });
  pos.forEach(w => { if (lower.includes(w)) s += 1; });
  return s < 0 ? 1 : s > 0 ? 0.2 : 0.5; // higher = more negative = better problem
}

function estimateAutomation(text: string): number {
  const auto = ["auto","otomatis","system","app","tools","software","digital","api","dashboard","automation"];
  const manual = ["orang","manual","kerjain sendiri","pake orang","human","person"];
  const lower = text.toLowerCase();
  let s = 0.5;
  auto.forEach(w => { if (lower.includes(w)) s += 0.15; });
  manual.forEach(w => { if (lower.includes(w)) s -= 0.15; });
  return Math.max(0, Math.min(1, s));
}

function estimateMoney(text: string): number {
  const high = ["jual","beli","uang","modal","bisnis","jualan","produk","harga","pay","money","price","revenue","subscription"];
  const low = ["cari","butuh","mau","free","gratis"];
  const lower = text.toLowerCase();
  let s = 0.5;
  high.forEach(w => { if (lower.includes(w)) s += 0.15; });
  low.forEach(w => { if (lower.includes(w)) s -= 0.15; });
  return Math.max(0, Math.min(1, s));
}

function scoreProblem(text: string, commentCount: number): { total: number; breakdown: Record<string,number> } {
  const commentScore = Math.min(commentCount / 200, 1);
  const sentimentScore = analyzeSentiment(text);
  const autoScore = estimateAutomation(text);
  const moneyScore = estimateMoney(text);
  const total = commentScore * 0.4 + sentimentScore * 0.2 + autoScore * 0.2 + moneyScore * 0.2;
  return { total: Math.round(total * 100) / 100, breakdown: { comments: commentScore, sentiment: sentimentScore, automation: autoScore, money: moneyScore } };
}

serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: corsHeaders });

  try {
    const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
    const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
    const SUPABASE_PUBLISHABLE_KEY = Deno.env.get("SUPABASE_PUBLISHABLE_KEY")!;
    if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY || !SUPABASE_PUBLISHABLE_KEY) {
      throw new Error("Backend secrets not configured");
    }

    const authHeader = req.headers.get("Authorization") ?? "";
    const userClient = createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, {
      global: { headers: { Authorization: authHeader } },
    });
    const { data: userData } = await userClient.auth.getUser();
    if (!userData.user) {
      return new Response(JSON.stringify({ error: "Unauthorized" }), { status: 401, headers: { ...corsHeaders, "Content-Type": "application/json" } });
    }

    const admin = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);
    const { data: profile } = await admin.from("profiles").select("organization_id").eq("user_id", userData.user.id).maybeSingle();
    if (!profile?.organization_id) throw new Error("Profile/org not initialized");
    const orgId = profile.organization_id as string;

    // Create engine run
    const { data: run, error: runErr } = await admin.from("engine_runs").insert({ organization_id: orgId, engine: "decision", status: "running" }).select("id").single();
    if (runErr) throw runErr;
    const runId = run.id as string;

    const log = async (level: string, source: string, message: string) => {
      await admin.from("engine_logs").insert({ organization_id: orgId, run_id: runId, level, source, message });
    };

    await log("system", "DECISION", "Decision run started");

    // Fetch problem_clean rows
    const { data: problems, error: probErr } = await admin
      .from("problem_clean")
      .select("id, text_clean, raw_id")
      .eq("organization_id", orgId)
      .order("created_at", { ascending: false })
      .limit(200);
    if (probErr) throw probErr;

    if (!problems || problems.length === 0) {
      await log("warning", "DECISION", "No problem_clean data found. Run Sense first.");
      await admin.from("engine_runs").update({ status: "failed", finished_at: new Date().toISOString() }).eq("id", runId);
      return new Response(JSON.stringify({ error: "No problems to analyze. Run Sense first." }), { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } });
    }

    // Score all problems
    const scored = problems.map((p: any) => {
      const { total, breakdown } = scoreProblem(p.text_clean, 50); // default comment count
      return { ...p, totalScore: total, breakdown };
    });
    scored.sort((a: any, b: any) => b.totalScore - a.totalScore);

    await log("info", "DECISION", `Scored ${scored.length} problems. Top score: ${scored[0]?.totalScore}`);

    // Try AI-enhanced decision if OPENAI_API_KEY is set
    const aiKey = Deno.env.get("OPENAI_API_KEY");
    const aiModel = Deno.env.get("AI_MODEL") || "gpt-4o-mini";
    let theme = "";
    let summary = "";
    let aiScore = scored[0]?.totalScore ?? 50;
    let aiRaw = "";

    if (aiKey) {
      try {
        const corpus = scored.slice(0, 30).map((p: any) => p.text_clean).join("\n\n---\n\n").slice(0, 10000);
        const prompt =
          "You are a Decision Core for an autonomous SaaS organism. From the following complaints, pick the 1 best problem theme to build as an MVP.\n" +
          "Give exactly 3 lines:\nTHEME: <theme>\nSCORE: <0-100>\nSUMMARY: <1-2 sentence summary>\n\nDATA:\n" + corpus;

        const aiResp = await fetch("https://api.openai.com/v1/chat/completions", {
          method: "POST",
          headers: { "Authorization": `Bearer ${aiKey}`, "Content-Type": "application/json" },
          body: JSON.stringify({ model: aiModel, messages: [{ role: "user", content: prompt }], max_tokens: 200, temperature: 0.7 }),
        });
        const aiJson = await aiResp.json();
        aiRaw = aiJson.choices?.[0]?.message?.content ?? "";
        theme = (aiRaw.match(/THEME:\s*(.+)/i)?.[1] ?? "").trim();
        const scoreRaw = (aiRaw.match(/SCORE:\s*(\d{1,3})/i)?.[1] ?? "50").trim();
        summary = (aiRaw.match(/SUMMARY:\s*(.+)/i)?.[1] ?? "").trim();
        aiScore = Math.max(0, Math.min(100, Number(scoreRaw) || 50));
        await log("success", "DECISION", `AI selected: ${theme} (${aiScore})`);
      } catch (e) {
        await log("warning", "DECISION", `AI call failed: ${e instanceof Error ? e.message : "unknown"}. Using heuristic fallback.`);
      }
    }

    // Fallback: use top-scored problem as theme
    if (!theme) {
      const topText = scored[0]?.text_clean ?? "General SaaS problem";
      const words = topText.split(/\s+/).slice(0, 5).map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
      theme = words || "Untitled Problem";
      summary = topText.slice(0, 200);
      aiScore = Math.round((scored[0]?.totalScore ?? 0.5) * 100);
    }

    // Persist idea candidate
    const { error: insertErr } = await admin.from("idea_candidates").insert({
      organization_id: orgId,
      theme,
      score: aiScore,
      summary,
      evidence: { model: aiKey ? aiModel : "heuristic", raw: aiRaw || "heuristic scoring", top_scored: scored.slice(0, 5).map((s: any) => ({ text: s.text_clean.slice(0, 100), score: s.totalScore })) },
    });
    if (insertErr) await log("warning", "DECISION", `Failed to insert idea_candidate: ${insertErr.message}`);
    else await log("success", "DECISION", `Idea candidate saved: ${theme}`);

    await admin.from("engine_runs").update({ status: "success", finished_at: new Date().toISOString(), meta: { theme, score: aiScore, scored_count: scored.length } }).eq("id", runId);

    return new Response(JSON.stringify({ ok: true, theme, score: aiScore, summary, scored_count: scored.length }), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (e) {
    console.error("run-decision error:", e);
    return new Response(JSON.stringify({ error: e instanceof Error ? e.message : "Unknown error" }), { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } });
  }
});
