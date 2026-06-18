import { create } from "zustand";

interface AppState {
  sidebarOpen: boolean;
  killSwitch: boolean;
  activeAgents: string[];
  selectedSymbol: string;
  selectedExchange: string;
  notifications: Notification[];
  toggleSidebar: () => void;
  toggleKillSwitch: () => void;
  setActiveAgents: (agents: string[]) => void;
  setSelectedSymbol: (symbol: string) => void;
  setSelectedExchange: (exchange: string) => void;
  addNotification: (notification: Notification) => void;
  clearNotifications: () => void;
}

interface Notification {
  id: string;
  type: "info" | "warning" | "error" | "success";
  message: string;
  timestamp: number;
}

export const useAppStore = create<AppState>((set) => ({
  sidebarOpen: true,
  killSwitch: false,
  activeAgents: [],
  selectedSymbol: "BTC",
  selectedExchange: "binance",
  notifications: [],
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  toggleKillSwitch: () => set((state) => ({ killSwitch: !state.killSwitch })),
  setActiveAgents: (agents) => set({ activeAgents: agents }),
  setSelectedSymbol: (symbol) => set({ selectedSymbol: symbol }),
  setSelectedExchange: (exchange) => set({ selectedExchange: exchange }),
  addNotification: (notification) =>
    set((state) => ({
      notifications: [...state.notifications, notification],
    })),
  clearNotifications: () => set({ notifications: [] }),
}));
