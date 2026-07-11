import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "@/integrations/supabase/client";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const nav = useNavigate();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const init = async () => {
      const { data } = await supabase.auth.getSession();
      if (cancelled) return;
      if (!data.session) {
        nav("/login", { replace: true });
        return;
      }
      setReady(true);
    };

    init();

    const { data: sub } = supabase.auth.onAuthStateChange((_evt, session) => {
      if (!session) nav("/login", { replace: true });
    });

    return () => {
      cancelled = true;
      sub.subscription.unsubscribe();
    };
  }, [nav]);

  if (!ready) return null;
  return <>{children}</>;
}
