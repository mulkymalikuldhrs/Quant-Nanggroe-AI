import { useEffect, useMemo, useState } from "react";

declare global {
  interface Window {
    puter?: any;
  }
}

type PuterChatOptions = {
  model?: string;
};

/** Default AI model — override via VITE_AI_MODEL env var */
const DEFAULT_MODEL = import.meta.env.VITE_AI_MODEL || "gpt-4o-mini";

export function usePuterAi() {
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Load Puter.js without touching index.html
    if (window.puter?.ai?.chat) {
      setReady(true);
      return;
    }

    const existing = document.querySelector('script[data-puter="true"]') as HTMLScriptElement | null;
    if (existing) {
      existing.addEventListener("load", () => setReady(true));
      existing.addEventListener("error", () => setError("Gagal memuat Puter.js"));
      return;
    }

    const s = document.createElement("script");
    s.src = "https://js.puter.com/v2/";
    s.async = true;
    s.dataset.puter = "true";
    s.onload = () => setReady(true);
    s.onerror = () => setError("Gagal memuat Puter.js");
    document.head.appendChild(s);
  }, []);

  const api = useMemo(() => {
    const chat = async (prompt: string, options?: PuterChatOptions) => {
      if (!window.puter?.ai?.chat) throw new Error("Puter AI belum siap");
      const res = await window.puter.ai.chat(prompt, { model: options?.model ?? DEFAULT_MODEL });
      // Puter returns either string or object depending on mode; normalize
      if (typeof res === "string") return res;
      if (res?.message?.content) return res.message.content;
      if (res?.content) return res.content;
      return JSON.stringify(res);
    };

    return { chat };
  }, []);

  return { ready, error, ...api };
}
