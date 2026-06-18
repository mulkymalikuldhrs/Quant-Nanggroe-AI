import { Activity, Settings, Power, Skull, LogOut } from "lucide-react";
import { Button } from "./ui/button";
import { StatusIndicator } from "./ui/status-indicator";
import { useToast } from "@/hooks/use-toast";
import { supabase } from "@/integrations/supabase/client";

interface HeaderProps {
  organismName: string;
  generation: number;
  status: "online" | "offline" | "warning" | "error" | "processing";
}

export function Header({ organismName, generation, status }: HeaderProps) {
  const { toast } = useToast();

  const handleSettings = () => {
    toast({ title: "Settings", description: "Settings panel coming soon." });
  };

  const handlePower = () => {
    toast({ title: "Power", description: "Power controls toggled.", variant: "default" });
  };

  const handleKill = () => {
    toast({
      title: "Kill Switch",
      description: "Organism termination requested. Use with caution.",
      variant: "destructive",
    });
  };

  const handleLogout = async () => {
    const { error } = await supabase.auth.signOut();
    if (error) {
      toast({ title: "Logout failed", description: error.message, variant: "destructive" });
    } else {
      toast({ title: "Logged out", description: "Session ended." });
    }
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/50 bg-background/80 backdrop-blur-xl">
      <div className="container flex h-16 items-center justify-between px-4">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="relative">
              <Activity className="w-6 h-6 text-primary" />
              <span className="absolute -top-1 -right-1 w-2 h-2 bg-success rounded-full animate-pulse" />
            </div>
            <div>
              <h1 className="text-lg font-bold gradient-text-primary">
                {organismName}
              </h1>
              <span className="text-[10px] text-muted-foreground font-mono">
                GEN-{generation.toString().padStart(4, "0")}
              </span>
            </div>
          </div>

          <StatusIndicator status={status} className="ml-4">
            System {status}
          </StatusIndicator>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            className="text-muted-foreground hover:text-foreground"
            onClick={handleSettings}
          >
            <Settings className="w-4 h-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="text-warning hover:text-warning hover:bg-warning/10"
            onClick={handlePower}
          >
            <Power className="w-4 h-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="text-destructive hover:text-destructive hover:bg-destructive/10"
            onClick={handleKill}
          >
            <Skull className="w-4 h-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="text-muted-foreground hover:text-foreground"
            onClick={handleLogout}
          >
            <LogOut className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </header>
  );
}
