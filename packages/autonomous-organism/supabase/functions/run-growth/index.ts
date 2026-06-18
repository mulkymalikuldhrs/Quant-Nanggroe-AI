// Edge Function: run-growth
// Simulates growth/marketing engine: generates campaign ideas from the top idea_candidate,
// logs activity, and returns campaign metadata.
// In production, this would connect to marketing APIs, content generators, etc.

import { serve } from "https://deno.land/std@0.168.0/http/function_handler.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

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
    const { data: run, error: runErr } = await admin.from("engine_runs").insert({ organization_id: orgId, engine: "growth", status: "running" }).select("id").single();
    if (runErr) throw runErr;
    const runId = run.id as string;

    const log = async (level: string, source: string, message: string) => {
      await admin.from("engine_logs").insert({ organization_id: orgId, run_id: runId, level, source, message });
    };

    await log("system", "GROWTH", "Growth run started");

    // Get latest factory output
    const { data: factoryRuns } = await admin
      .from("engine_runs")
      .select("id, meta, started_at")
      .eq("organization_id", orgId)
      .eq("engine", "factory")
      .eq("status", "success")
      .order("started_at", { ascending: false })
      .limit(1);

    let productName = "Product";
    let productTheme = "";

    if (factoryRuns && factoryRuns.length > 0 && factoryRuns[0].meta) {
      const meta = factoryRuns[0].meta as any;
      productName = meta.name || "Product";
      productTheme = meta.theme || "";
    }

    // Generate campaign ideas
    const aiKey = Deno.env.get("OPENAI_API_KEY");
    const aiModel = Deno.env.get("AI_MODEL") || "gpt-4o-mini";
    let campaigns: Array<{ type: string; title: string; description: string }> = [];
    let aiRaw = "";

    if (aiKey && productTheme) {
      try {
        const prompt = `Generate 3 short marketing campaign ideas for a SaaS product called "${productName}" that solves: "${productTheme}". For each campaign give: type (blog/social/seo/email), title, and a 1-sentence description. Return as JSON array.`;
        const aiResp = await fetch("https://api.openai.com/v1/chat/completions", {
          method: "POST",
          headers: { "Authorization": `Bearer ${aiKey}`, "Content-Type": "application/json" },
          body: JSON.stringify({ model: aiModel, messages: [{ role: "user", content: prompt }], max_tokens: 500, temperature: 0.8 }),
        });
        const aiJson = await aiResp.json();
        aiRaw = aiJson.choices?.[0]?.message?.content ?? "";
        // Try parse JSON from response
        const jsonMatch = aiRaw.match(/\[[\s\S]*\]/);
        if (jsonMatch) {
          campaigns = JSON.parse(jsonMatch[0]);
        }
        await log("success", "GROWTH", `AI generated ${campaigns.length} campaign ideas`);
      } catch (e) {
        await log("warning", "GROWTH", `AI generation failed: ${e instanceof Error ? e.message : "unknown"}. Using template fallback.`);
      }
    }

    // Fallback campaigns
    if (campaigns.length === 0) {
      campaigns = [
        { type: "blog", title: `Why ${productTheme || "this problem"} needs solving in 2025`, description: `SEO-optimized blog post targeting people searching for ${productTheme || "SaaS solutions"}.` },
        { type: "social", title: `${productName} Launch Thread`, description: "Twitter/X thread announcing the product with key benefits and CTA." },
        { type: "email", title: "Early Access Invite", description: "Email campaign targeting early adopters with exclusive access offer." },
      ];
    }

    // Simulate metrics
    const metrics = {
      reach: Math.floor(Math.random() * 5000) + 500,
      clicks: Math.floor(Math.random() * 200) + 20,
      signups: Math.floor(Math.random() * 30) + 2,
      conversionRate: (Math.random() * 5 + 1).toFixed(1) + "%",
    };

    await log("info", "GROWTH", `Campaign: ${campaigns[0]?.title ?? "Untitled"}`);
    await log("info", "GROWTH", `Simulated reach: ${metrics.reach}, signups: ${metrics.signups}`);

    await admin.from("engine_runs").update({
      status: "success",
      finished_at: new Date().toISOString(),
      meta: { product: productName, campaigns, metrics, generator: aiKey ? `ai-${aiModel}` : "template" },
    }).eq("id", runId);

    return new Response(JSON.stringify({ ok: true, product: productName, campaigns, metrics }), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (e) {
    console.error("run-growth error:", e);
    return new Response(JSON.stringify({ error: e instanceof Error ? e.message : "Unknown error" }), { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } });
  }
});
