// Lovable Cloud backend function: ingest-sense
// Pulls from enabled sources (RSS + HackerNews) and stores problem_raw + problem_clean + logs.

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

function stripHtml(input: string) {
  return input
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

async function sha256Hex(input: string) {
  const data = new TextEncoder().encode(input);
  const hash = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(hash)).map((b) => b.toString(16).padStart(2, "0")).join("");
}

function getXmlTag(xml: string, tag: string) {
  const m = xml.match(new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag}>`, "i"));
  return m?.[1]?.trim() ?? null;
}

function getXmlTagAttr(xml: string, tag: string, attr: string) {
  const m = xml.match(new RegExp(`<${tag}[^>]*${attr}="([^"]+)"[^>]*\\/?>`, "i"));
  return m?.[1]?.trim() ?? null;
}

async function fetchRssItems(url: string, limit: number) {
  const resp = await fetch(url, { headers: { "User-Agent": "OrganismSense/1.0" } });
  if (!resp.ok) throw new Error(`RSS fetch failed (${resp.status})`);
  const xml = await resp.text();

  // RSS 2.0: <item>...</item>
  const items = Array.from(xml.matchAll(/<item>([\s\S]*?)<\/item>/gi)).map((m) => m[1]);
  if (items.length) {
    return items.slice(0, limit).map((raw) => {
      const title = stripHtml(getXmlTag(raw, "title") ?? "");
      const link = stripHtml(getXmlTag(raw, "link") ?? "");
      const guid = stripHtml(getXmlTag(raw, "guid") ?? link);
      const pubDate = getXmlTag(raw, "pubDate");
      const desc = stripHtml(getXmlTag(raw, "description") ?? "");
      const content = stripHtml(getXmlTag(raw, "content:encoded") ?? desc);
      return {
        external_id: guid || link,
        title,
        url: link,
        author: stripHtml(getXmlTag(raw, "dc:creator") ?? ""),
        published_at: pubDate ? new Date(pubDate).toISOString() : null,
        content: content || desc || title,
      };
    });
  }

  // Atom: <entry>...</entry>
  const entries = Array.from(xml.matchAll(/<entry>([\s\S]*?)<\/entry>/gi)).map((m) => m[1]);
  return entries.slice(0, limit).map((raw) => {
    const title = stripHtml(getXmlTag(raw, "title") ?? "");
    const link = getXmlTagAttr(raw, "link", "href") ?? stripHtml(getXmlTag(raw, "link") ?? "");
    const id = stripHtml(getXmlTag(raw, "id") ?? link);
    const updated = getXmlTag(raw, "updated") ?? getXmlTag(raw, "published");
    const summary = stripHtml(getXmlTag(raw, "summary") ?? "");
    const content = stripHtml(getXmlTag(raw, "content") ?? summary);
    return {
      external_id: id || link,
      title,
      url: link,
      author: stripHtml(getXmlTag(raw, "name") ?? ""),
      published_at: updated ? new Date(updated).toISOString() : null,
      content: content || summary || title,
    };
  });
}

async function fetchHnTop(limit: number) {
  const idsResp = await fetch("https://hacker-news.firebaseio.com/v0/topstories.json");
  if (!idsResp.ok) throw new Error(`HN ids fetch failed (${idsResp.status})`);
  const ids = (await idsResp.json()) as number[];
  const top = ids.slice(0, limit);

  const items = await Promise.all(
    top.map(async (id) => {
      const r = await fetch(`https://hacker-news.firebaseio.com/v0/item/${id}.json`);
      if (!r.ok) return null;
      const j = await r.json();
      const title = typeof j?.title === "string" ? j.title : "";
      const text = typeof j?.text === "string" ? stripHtml(j.text) : "";
      const url = typeof j?.url === "string" ? j.url : `https://news.ycombinator.com/item?id=${id}`;
      const author = typeof j?.by === "string" ? j.by : "";
      const published_at = typeof j?.time === "number" ? new Date(j.time * 1000).toISOString() : null;
      return {
        external_id: `hn:${id}`,
        title,
        url,
        author,
        published_at,
        content: [title, text].filter(Boolean).join("\n\n").trim() || title,
      };
    })
  );

  return items.filter(Boolean) as Array<{
    external_id: string;
    title: string;
    url: string;
    author: string;
    published_at: string | null;
    content: string;
  }>;
}

serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: corsHeaders });

  const startedAt = new Date();

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
      return new Response(JSON.stringify({ error: "Unauthorized" }), {
        status: 401,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const admin = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);

    // Resolve org id via profiles
    const { data: profile, error: profileErr } = await admin
      .from("profiles")
      .select("organization_id")
      .eq("user_id", userData.user.id)
      .maybeSingle();
    if (profileErr) throw profileErr;
    if (!profile?.organization_id) throw new Error("Profile/org not initialized. Login again.");
    const orgId = profile.organization_id as string;

    // Guardrails
    const { data: sched, error: schedErr } = await admin
      .from("scheduler_config")
      .select("enabled, kill_switch, max_iterations, timeout_seconds")
      .eq("organization_id", orgId)
      .maybeSingle();
    if (schedErr) throw schedErr;
    if (sched?.kill_switch) throw new Error("Kill-switch aktif. Matikan dulu untuk menjalankan engine.");

    const timeoutMs = Math.max(5, Math.min(120, sched?.timeout_seconds ?? 60)) * 1000;
    const maxIter = Math.max(5, Math.min(200, sched?.max_iterations ?? 25));

    const run = await admin
      .from("engine_runs")
      .insert({ organization_id: orgId, engine: "sense", status: "running" })
      .select("id")
      .single();
    if (run.error) throw run.error;
    const runId = run.data.id as string;

    const log = async (level: string, source: string, message: string) => {
      await admin.from("engine_logs").insert({
        organization_id: orgId,
        run_id: runId,
        level,
        source,
        message,
      });
    };

    await log("system", "SENSE", "Run started");

    const deadline = Date.now() + timeoutMs;

    const { data: sources, error: sourcesErr } = await admin
      .from("problem_sources")
      .select("id, type, name, url")
      .eq("organization_id", orgId)
      .eq("enabled", true);
    if (sourcesErr) throw sourcesErr;

    let inserted = 0;
    let cleaned = 0;

    for (const s of sources ?? []) {
      if (Date.now() > deadline) break;
      if (inserted >= maxIter) break;

      await log("info", "SENSE", `Fetching ${s.type}: ${s.name}`);

      let items: any[] = [];
      try {
        if (s.type === "rss") items = await fetchRssItems(s.url, Math.min(20, maxIter - inserted));
        if (s.type === "hackernews") items = await fetchHnTop(Math.min(20, maxIter - inserted));
      } catch (e) {
        await log("warning", "SENSE", `Fetch failed for ${s.name}`);
        continue;
      }

      for (const it of items) {
        if (Date.now() > deadline) break;
        if (inserted >= maxIter) break;

        const base = [it.external_id, it.title, it.url, it.content].filter(Boolean).join("|");
        const contentHash = await sha256Hex(base);

        const { data: rawRow, error: rawErr } = await admin
          .from("problem_raw")
          .insert({
            organization_id: orgId,
            source_id: s.id,
            external_id: it.external_id ?? null,
            title: it.title ?? null,
            url: it.url ?? null,
            author: it.author ?? null,
            published_at: it.published_at ?? null,
            content: it.content,
            content_hash: contentHash,
          })
          .select("id")
          .single();

        if (rawErr) {
          // likely duplicate content_hash
          continue;
        }
        inserted += 1;

        const textClean = stripHtml(it.content).slice(0, 5000);
        const { error: cleanErr } = await admin
          .from("problem_clean")
          .insert({ organization_id: orgId, raw_id: rawRow.id, text_clean: textClean, language: null });
        if (!cleanErr) cleaned += 1;
      }
    }

    await log("success", "SENSE", `Inserted raw=${inserted}, clean=${cleaned}`);

    await admin
      .from("engine_runs")
      .update({ status: "success", finished_at: new Date().toISOString(), meta: { inserted, cleaned } })
      .eq("id", runId);

    return new Response(JSON.stringify({ ok: true, inserted, cleaned, duration_ms: Date.now() - startedAt.getTime() }), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (e) {
    console.error("ingest-sense error:", e);
    return new Response(JSON.stringify({ error: e instanceof Error ? e.message : "Unknown error" }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
