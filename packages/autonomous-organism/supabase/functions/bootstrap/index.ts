// Lovable Cloud backend function: bootstrap
// Creates org + owner profile + default scheduler config for the current user if missing.

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
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

    const { data: userData, error: userErr } = await userClient.auth.getUser();
    if (userErr || !userData.user) return new Response(JSON.stringify({ error: "Unauthorized" }), { status: 401, headers: { ...corsHeaders, "Content-Type": "application/json" } });
    const userId = userData.user.id;

    const admin = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);

    // If profile exists, no-op.
    const { data: existingProfile, error: profileErr } = await admin
      .from("profiles")
      .select("user_id, organization_id, role")
      .eq("user_id", userId)
      .maybeSingle();
    if (profileErr) throw profileErr;
    if (existingProfile) {
      return new Response(JSON.stringify({ ok: true, already: true, organization_id: existingProfile.organization_id }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    // Create organization
    const orgName = `ORG-${userId.slice(0, 8).toUpperCase()}`;
    const { data: org, error: orgErr } = await admin
      .from("organizations")
      .insert({ name: orgName, owner_id: userId })
      .select("id")
      .single();
    if (orgErr) throw orgErr;

    // Create owner profile
    const { error: insertProfileErr } = await admin.from("profiles").insert({
      user_id: userId,
      organization_id: org.id,
      role: "owner",
      display_name: userData.user.email ?? null,
    });
    if (insertProfileErr) throw insertProfileErr;

    // Default scheduler config
    const { error: schedErr } = await admin.from("scheduler_config").insert({
      organization_id: org.id,
      enabled: false,
      kill_switch: false,
      max_iterations: 25,
      timeout_seconds: 60,
      error_threshold: 5,
    });
    if (schedErr) throw schedErr;

    // Seed sources: HN global + sample RSS (can be changed later in UI)
    await admin.from("problem_sources").insert([
      {
        organization_id: org.id,
        type: "hackernews",
        name: "Hacker News (Top)",
        url: "https://hacker-news.firebaseio.com/v0/topstories.json",
        enabled: true,
      },
      {
        organization_id: org.id,
        type: "rss",
        name: "Indie Hackers (RSS)",
        url: "https://www.indiehackers.com/feed.xml",
        enabled: true,
      },
    ]);

    return new Response(JSON.stringify({ ok: true, organization_id: org.id }), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (e) {
    console.error("bootstrap error:", e);
    return new Response(JSON.stringify({ error: e instanceof Error ? e.message : "Unknown error" }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
