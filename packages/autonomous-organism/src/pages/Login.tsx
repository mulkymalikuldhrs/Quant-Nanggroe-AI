import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "@/integrations/supabase/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { OrganismCard, OrganismCardHeader, OrganismCardTitle, OrganismCardContent } from "@/components/ui/organism-card";
import { useToast } from "@/hooks/use-toast";

export default function Login() {
  const nav = useNavigate();
  const { toast } = useToast();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    supabase.auth.getSession().then(({ data }) => {
      if (!cancelled && data.session) nav("/");
    });
    return () => {
      cancelled = true;
    };
  }, [nav]);

  const bootstrap = async () => {
    // Creates org+profile+defaults for the logged-in user if missing.
    const { error } = await supabase.functions.invoke("bootstrap", { body: {} });
    if (error) throw error;
  };

  const onLogin = async () => {
    setLoading(true);
    try {
      const { data, error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) throw error;
      if (data.session) await bootstrap();
      nav("/");
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : 'Terjadi kesalahan';
      toast({
        title: "Login gagal",
        description: message,
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const onSignup = async () => {
    setLoading(true);
    try {
      const { data, error } = await supabase.auth.signUp({ email, password });
      if (error) throw error;
      // auto-confirm enabled → should have session; still handle edge case
      const session = data.session ?? (await supabase.auth.getSession()).data.session;
      if (session) await bootstrap();
      toast({ title: "Akun dibuat", description: "Masuk ke sistem…" });
      nav("/");
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : 'Terjadi kesalahan';
      toast({
        title: "Signup gagal",
        description: message,
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex items-center justify-center px-4">
      <OrganismCard variant="default" size="lg" className="w-full max-w-md">
        <OrganismCardHeader>
          <OrganismCardTitle>Access Control</OrganismCardTitle>
        </OrganismCardHeader>
        <OrganismCardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Login untuk mengaktifkan mode otonom (database + engine runs). Akun pertama akan menjadi <span className="font-semibold">owner</span>.
          </p>

          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input id="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@domain.com" autoComplete="email" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input id="password" value={password} onChange={(e) => setPassword(e.target.value)} type="password" autoComplete="current-password" />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Button onClick={onLogin} disabled={loading || !email || !password}>
              Login
            </Button>
            <Button onClick={onSignup} variant="secondary" disabled={loading || !email || !password}>
              Signup
            </Button>
          </div>
        </OrganismCardContent>
      </OrganismCard>
    </div>
  );
}
