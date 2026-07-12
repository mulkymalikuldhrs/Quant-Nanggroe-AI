"use client";

import React, { useEffect, useState } from "react";
import {
  Database,
  Search,
  Plus,
  Brain,
  Layers,
  FileStack,
  Zap,
  RefreshCw,
  ChevronRight,
  Clock,
  Hash,
  HardDrive,
  BookOpen,
} from "lucide-react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MetricCard, SectionHeader, Skeleton } from "@/components/dashboard/shared";
import { apiClient } from "@/lib/api-client";
import { cn } from "@/lib/utils";

const MEMORY_TYPES = ["knowledge", "session", "vector", "condenser", "paging"];

const categoryColors: Record<string, string> = {
  knowledge: "#06b6d4",
  session: "#8b5cf6",
  vector: "#10b981",
  condenser: "#f59e0b",
  paging: "#f43f5e",
};

const categoryIcons: Record<string, React.ReactNode> = {
  knowledge: <Brain className="w-4 h-4" />,
  session: <Clock className="w-4 h-4" />,
  vector: <Zap className="w-4 h-4" />,
  condenser: <Layers className="w-4 h-4" />,
  paging: <FileStack className="w-4 h-4" />,
};

interface MemoryEntry {
  id: string;
  key: string;
  value: string;
  category: string;
  timestamp: string;
  size: number;
  accessCount: number;
}

export default function MemoryPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<MemoryEntry[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [storeDialogOpen, setStoreDialogOpen] = useState(false);
  const [storeKey, setStoreKey] = useState("");
  const [storeValue, setStoreValue] = useState("");
  const [storeCategory, setStoreCategory] = useState("knowledge");
  const [isStoring, setIsStoring] = useState(false);

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setIsSearching(true);
    try {
      const result = await apiClient.searchMemory(searchQuery);
      // Transform results to MemoryEntry format
      const entries: MemoryEntry[] = Array.isArray(result)
        ? result.map((item: unknown, i: number) => {
            const record = item as Record<string, unknown>;
            return {
              id: `mem-${i}`,
              key: String(record.key || ""),
              value: String(record.value || ""),
              category: String(record.category || "knowledge"),
              timestamp: String(record.timestamp || new Date().toISOString()),
              size: Number(record.size || 0),
              accessCount: Number(record.accessCount || 0),
            };
          })
        : [];
      setSearchResults(entries);
    } catch {
      setSearchResults([]);
    }
    setIsSearching(false);
  };

  const handleStore = async () => {
    if (!storeKey || !storeValue) return;
    setIsStoring(true);
    try {
      await apiClient.storeMemory({
        key: storeKey,
        value: storeValue,
        category: storeCategory,
      });
    } catch {
      // ignore
    }
    setIsStoring(false);
    setStoreDialogOpen(false);
    setStoreKey("");
    setStoreValue("");
  };

  // Sample data for distribution visualization
  const categoryData = MEMORY_TYPES.map((type) => ({
    name: type,
    value: Math.floor(Math.random() * 20) + 5,
    color: categoryColors[type],
  }));

  const totalEntries = categoryData.reduce((acc, d) => acc + d.value, 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 animate-slide-up">
        <div className="space-y-1">
          <h1 className="text-3xl font-black gradient-text flex items-center gap-3 tracking-tight">
            <Database className="w-8 h-8 text-purple animate-pulse-glow" />
            Neural Knowledge Base
          </h1>
          <p className="text-sm font-medium text-muted-foreground uppercase tracking-widest pl-11">
            Distributed Agent Memory & Vector Store
          </p>
        </div>
        <Button
          variant="cyan"
          onClick={() => setStoreDialogOpen(true)}
          className="gap-2 cursor-pointer font-bold tracking-wide shadow-[0_4px_20px_rgba(6,182,212,0.3)] hover:shadow-[0_4px_25px_rgba(6,182,212,0.5)] transition-all hover-lift"
        >
          <Plus className="w-4 h-4" />
          INJECT MEMORY
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 animate-slide-up stagger-children" style={{ animationDelay: '100ms' }}>
        <MetricCard
          title="Memory Types"
          value={5}
          subtitle="Categories"
          icon={<Layers className="w-5 h-5" />}
          color="cyan"
        />
        <MetricCard
          title="Total Entries"
          value={totalEntries}
          subtitle="In knowledge base"
          icon={<Database className="w-5 h-5" />}
          color="purple"
        />
        <MetricCard
          title="Search Ready"
          value="Active"
          subtitle="Vector search online"
          icon={<Search className="w-5 h-5" />}
          color="emerald"
        />
        <MetricCard
          title="Last Updated"
          value="Now"
          subtitle="Real-time sync"
          icon={<Clock className="w-5 h-5" />}
          color="amber"
        />
      </div>

      <div className="animate-slide-up" style={{ animationDelay: '200ms' }}>
        <Tabs defaultValue="search" className="w-full">
          <TabsList className="bg-secondary/20 p-1 mb-4 border border-border/50 backdrop-blur-md">
            <TabsTrigger value="search" className="font-bold tracking-widest uppercase text-xs">Vector Search</TabsTrigger>
            <TabsTrigger value="browser" className="font-bold tracking-widest uppercase text-xs">Knowledge Base</TabsTrigger>
            <TabsTrigger value="graph" className="font-bold tracking-widest uppercase text-xs">Neural Graph</TabsTrigger>
          </TabsList>

          {/* Search Tab */}
          <TabsContent value="search" className="m-0">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Search Panel */}
              <div className="lg:col-span-1 space-y-6">
                <Card variant="flat" className="border-t-4 border-t-cyan relative overflow-hidden group">
                  <div className="absolute right-0 top-0 w-32 h-32 bg-cyan/5 rounded-bl-full translate-x-16 -translate-y-16 group-hover:bg-cyan/10 transition-colors pointer-events-none" />
                  <CardHeader className="relative z-10">
                    <CardTitle className="text-sm font-semibold text-foreground uppercase tracking-wider flex items-center gap-2">
                      <Search className="w-4 h-4 text-cyan" />
                      Semantic Query
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4 relative z-10">
                    <div className="relative group">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground group-focus-within:text-cyan transition-colors" />
                      <Input
                        placeholder="Query vector store..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-9 bg-secondary/20 h-12 text-sm focus-visible:ring-cyan/50 font-mono shadow-[inset_0_2px_4px_rgba(0,0,0,0.1)]"
                        onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                      />
                    </div>
                    <Button
                      variant="cyan"
                      className="w-full cursor-pointer h-10 font-bold tracking-widest shadow-lg hover-lift"
                      onClick={handleSearch}
                      disabled={isSearching || !searchQuery}
                    >
                      {isSearching ? (
                        <>
                          <RefreshCw className="w-4 h-4 animate-spin mr-2" />
                          SEARCHING...
                        </>
                      ) : (
                        <>
                          <Search className="w-4 h-4 mr-2" />
                          EXECUTE QUERY
                        </>
                      )}
                    </Button>
                  </CardContent>
                </Card>

                <Card variant="flat">
                  <CardHeader>
                    <CardTitle className="text-sm font-semibold text-foreground uppercase tracking-wider flex items-center gap-2">
                      <PieChart className="w-4 h-4 text-purple" />
                      Memory Distribution
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-48 mb-4">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <defs>
                            <filter id="glowPie" x="-20%" y="-20%" width="140%" height="140%">
                              <feGaussianBlur stdDeviation="3" result="blur" />
                              <feComposite in="SourceGraphic" in2="blur" operator="over" />
                            </filter>
                          </defs>
                          <Pie
                            data={categoryData}
                            cx="50%"
                            cy="50%"
                            innerRadius={50}
                            outerRadius={80}
                            paddingAngle={5}
                            dataKey="value"
                            stroke="rgba(0,0,0,0.5)"
                            strokeWidth={2}
                          >
                            {categoryData.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={entry.color} style={{ filter: "url(#glowPie)" }} />
                            ))}
                          </Pie>
                          <Tooltip
                            contentStyle={{
                              background: "rgba(10, 15, 26, 0.95)",
                              backdropFilter: "blur(10px)",
                              border: "1px solid rgba(255,255,255,0.1)",
                              borderRadius: "8px",
                              boxShadow: "0 4px 20px rgba(0,0,0,0.4)",
                              fontSize: "12px",
                              fontWeight: 600,
                            }}
                          />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="space-y-2 stagger-children">
                      {categoryData.map((entry) => (
                        <div
                          key={entry.name}
                          className="flex items-center justify-between p-2 rounded-lg bg-secondary/20 hover:bg-secondary/40 transition-colors"
                        >
                          <div className="flex items-center gap-2">
                            <div
                              className="w-2 h-2 rounded-full shadow-[0_0_8px_currentColor]"
                              style={{ backgroundColor: entry.color, color: entry.color }}
                            />
                            <span className="text-xs font-bold uppercase tracking-widest text-foreground">
                              {entry.name}
                            </span>
                          </div>
                          <span className="text-sm font-mono font-bold text-muted-foreground">{entry.value}</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Results */}
              <div className="lg:col-span-2">
                <Card variant="flat" className="h-full">
                  <CardHeader>
                    <CardTitle className="text-sm font-semibold text-foreground uppercase tracking-wider flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Database className="w-4 h-4 text-cyan" />
                        Search Results
                      </div>
                      <Badge variant="outline" className="text-cyan border-cyan/30 bg-cyan/5">
                        {searchResults.length} FOUND
                      </Badge>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ScrollArea className="h-[650px] pr-4">
                      {searchResults.length > 0 ? (
                        <div className="space-y-4 stagger-children">
                          {searchResults.map((entry) => (
                            <div
                              key={entry.id}
                              className="p-4 rounded-xl bg-secondary/10 border border-border/40 hover:border-cyan/40 hover:bg-cyan/5 hover:shadow-[0_4px_20px_rgba(6,182,212,0.1)] transition-all cursor-pointer group"
                            >
                              <div className="flex items-start justify-between mb-3">
                                <div className="flex items-center gap-3">
                                  <div 
                                    className="p-2 rounded-lg shadow-sm"
                                    style={{ backgroundColor: `${categoryColors[entry.category]}20`, color: categoryColors[entry.category] }}
                                  >
                                    {categoryIcons[entry.category]}
                                  </div>
                                  <div>
                                    <span className="text-sm font-bold text-foreground font-mono block group-hover:text-cyan transition-colors">
                                      {entry.key}
                                    </span>
                                  </div>
                                </div>
                                <Badge
                                  variant="outline"
                                  className="text-[9px] font-bold uppercase tracking-widest shadow-sm bg-background/50"
                                  style={{
                                    borderColor: `${categoryColors[entry.category]}50`,
                                    color: categoryColors[entry.category],
                                  }}
                                >
                                  {entry.category}
                                </Badge>
                              </div>
                              <p className="text-xs text-muted-foreground line-clamp-3 mb-4 leading-relaxed bg-background/30 p-3 rounded-lg border border-border/20">
                                {entry.value}
                              </p>
                              <div className="flex items-center gap-4 text-[10px] font-bold tracking-widest uppercase text-muted-foreground">
                                <span className="flex items-center gap-1.5">
                                  <Clock className="w-3 h-3 text-emerald" />
                                  {new Date(entry.timestamp).toLocaleString()}
                                </span>
                                <span className="flex items-center gap-1.5">
                                  <HardDrive className="w-3 h-3 text-purple" />
                                  {entry.size} BYTES
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="flex flex-col items-center justify-center h-full text-muted-foreground text-sm py-20">
                          <div className="w-20 h-20 rounded-full bg-secondary/30 flex items-center justify-center mb-6 shadow-[inset_0_0_20px_rgba(255,255,255,0.02)] border border-border/30">
                            <Database className="w-8 h-8 opacity-50" />
                          </div>
                          <p className="text-lg font-bold text-foreground mb-1">Awaiting Query</p>
                          <p className="text-xs font-medium text-center max-w-sm">
                            The semantic knowledge base contains research notes, trade journals, and autonomous agent decisions. Enter a query to retrieve vectors.
                          </p>
                        </div>
                      )}
                    </ScrollArea>
                  </CardContent>
                </Card>
              </div>
            </div>
          </TabsContent>

          {/* Knowledge Browser */}
          <TabsContent value="browser" className="m-0">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
              {MEMORY_TYPES.map((type) => (
                <Card key={type} className="glass-card hover:border-cyan/30 hover:shadow-[0_0_20px_rgba(6,182,212,0.1)] transition-all cursor-pointer group">
                  <CardContent className="p-6">
                    <div className="text-center">
                      <div
                        className="w-16 h-16 rounded-2xl mx-auto mb-4 flex items-center justify-center group-hover:scale-110 transition-transform shadow-[0_0_15px_currentColor]"
                        style={{ backgroundColor: `${categoryColors[type]}15`, color: categoryColors[type] }}
                      >
                        <BookOpen className="w-8 h-8" />
                      </div>
                      <p className="text-sm font-black text-foreground uppercase tracking-widest block mb-1">
                        {type}
                      </p>
                      <p className="text-xs text-muted-foreground font-medium">
                        Store Explorer
                      </p>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          {/* Knowledge Graph */}
          <TabsContent value="graph" className="m-0">
            <Card variant="gradient" className="h-[600px] border-emerald/20 flex flex-col items-center justify-center relative overflow-hidden bg-[radial-gradient(ellipse_at_center,rgba(16,185,129,0.05),transparent_70%)]">
              <div className="absolute inset-0 bg-[url('/grid.svg')] bg-center [mask-image:radial-gradient(white,transparent_80%)] opacity-20" />
              <div className="relative z-10 w-full max-w-2xl h-full flex items-center justify-center">
                <div className="relative w-[400px] h-[400px]">
                  {/* Central node */}
                  <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-24 h-24 rounded-full bg-cyan/10 border-2 border-cyan/40 flex items-center justify-center shadow-[0_0_50px_rgba(6,182,212,0.3)] z-20 animate-pulse">
                    <Brain className="w-10 h-10 text-cyan drop-shadow-[0_0_10px_rgba(6,182,212,0.8)]" />
                  </div>
                  
                  {/* Neural Links (SVG) */}
                  <svg className="absolute inset-0 w-full h-full z-10 pointer-events-none opacity-40">
                     {MEMORY_TYPES.map((_, i) => {
                       const angle = (i / MEMORY_TYPES.length) * Math.PI * 2 - Math.PI / 2;
                       const radius = 140;
                       const x2 = Math.cos(angle) * radius + 200;
                       const y2 = Math.sin(angle) * radius + 200;
                       return (
                         <line key={i} x1="200" y1="200" x2={x2} y2={y2} stroke="url(#lineGrad)" strokeWidth="2" strokeDasharray="4 4" className="animate-shimmer" />
                       )
                     })}
                     <defs>
                       <linearGradient id="lineGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                          <stop offset="0%" stopColor="#06b6d4" stopOpacity="1" />
                          <stop offset="100%" stopColor="#10b981" stopOpacity="0.1" />
                       </linearGradient>
                     </defs>
                  </svg>

                  {/* Surrounding nodes */}
                  {MEMORY_TYPES.map((type, i) => {
                    const angle = (i / MEMORY_TYPES.length) * Math.PI * 2 - Math.PI / 2;
                    const radius = 140;
                    const x = Math.cos(angle) * radius + 200;
                    const y = Math.sin(angle) * radius + 200;
                    return (
                      <div
                        key={type}
                        className="absolute w-16 h-16 rounded-full flex flex-col items-center justify-center border-2 shadow-[0_0_20px_currentColor] z-20 transition-transform hover:scale-125 cursor-pointer backdrop-blur-sm"
                        style={{
                          left: `${x - 32}px`,
                          top: `${y - 32}px`,
                          backgroundColor: `${categoryColors[type]}20`,
                          borderColor: `${categoryColors[type]}60`,
                          color: categoryColors[type],
                        }}
                      >
                        {categoryIcons[type]}
                        <span className="text-[9px] font-bold uppercase tracking-widest mt-1">
                          {type.slice(0, 4)}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
              <div className="absolute bottom-10 text-center z-10">
                <p className="text-lg font-black text-foreground uppercase tracking-widest mb-1 drop-shadow-md">
                  Neural Knowledge Graph
                </p>
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-widest">
                  Real-time mapping of memory vectors
                </p>
              </div>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      {/* Store Memory Dialog */}
      <Dialog open={storeDialogOpen} onOpenChange={setStoreDialogOpen}>
        <DialogContent className="border-cyan/50 shadow-[0_0_50px_rgba(6,182,212,0.15)]">
          <DialogHeader>
            <DialogTitle className="text-xl font-black text-foreground flex items-center gap-2 uppercase tracking-tight">
              <Plus className="w-5 h-5 text-cyan" />
              Inject Memory Data
            </DialogTitle>
            <DialogDescription className="text-sm font-medium">
              Manually insert structured or unstructured data into the distributed vector store for autonomous agent retrieval.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-5 my-2">
            <div>
              <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-1.5 block">
                Memory Key
              </label>
              <Input
                placeholder="e.g., config_node_alpha"
                value={storeKey}
                onChange={(e) => setStoreKey(e.target.value)}
                className="font-mono bg-secondary/30 h-10 border-border/50 focus-visible:ring-cyan/50"
              />
            </div>
            <div>
              <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-1.5 block">
                Content Payload
              </label>
              <Textarea
                placeholder="Enter stringified JSON, raw text, or embeddings..."
                value={storeValue}
                onChange={(e) => setStoreValue(e.target.value)}
                rows={5}
                className="font-mono text-sm bg-secondary/30 border-border/50 focus-visible:ring-cyan/50 resize-none"
              />
            </div>
            <div>
              <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-1.5 block">
                Destination Store
              </label>
              <Select value={storeCategory} onValueChange={setStoreCategory}>
                <SelectTrigger className="bg-secondary/30 border-border/50 focus:ring-cyan/50">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {MEMORY_TYPES.map((type) => (
                    <SelectItem key={type} value={type} className="uppercase tracking-widest text-xs font-bold">
                      {type} Store
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter className="gap-3">
            <Button
              variant="ghost"
              onClick={() => setStoreDialogOpen(false)}
              className="cursor-pointer font-bold tracking-widest uppercase text-xs"
            >
              Cancel
            </Button>
            <Button
              variant="cyan"
              onClick={handleStore}
              disabled={!storeKey || !storeValue || isStoring}
              className="cursor-pointer font-bold tracking-widest uppercase shadow-[0_4px_20px_rgba(6,182,212,0.3)] hover:shadow-[0_4px_25px_rgba(6,182,212,0.5)] transition-shadow"
            >
              {isStoring ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin mr-2" />
                  INJECTING...
                </>
              ) : (
                <>
                  <Plus className="w-4 h-4 mr-2" />
                  CONFIRM INJECTION
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
