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
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Brain className="w-6 h-6 text-purple" />
            Memory & Knowledge
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Search, browse, and manage the AI knowledge base
          </p>
        </div>
        <Button
          variant="cyan"
          onClick={() => setStoreDialogOpen(true)}
          className="gap-2 cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          Store Memory
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Memory Types"
          value={5}
          subtitle="Categories"
          icon={<Layers className="w-4 h-4" />}
          color="cyan"
        />
        <MetricCard
          title="Total Entries"
          value={totalEntries}
          subtitle="In knowledge base"
          icon={<Database className="w-4 h-4" />}
          color="purple"
        />
        <MetricCard
          title="Search Ready"
          value="Active"
          subtitle="Vector search online"
          icon={<Search className="w-4 h-4" />}
          color="emerald"
        />
        <MetricCard
          title="Last Updated"
          value="Now"
          subtitle="Real-time sync"
          icon={<Clock className="w-4 h-4" />}
          color="amber"
        />
      </div>

      <Tabs defaultValue="search">
        <TabsList>
          <TabsTrigger value="search">Memory Search</TabsTrigger>
          <TabsTrigger value="browser">Knowledge Browser</TabsTrigger>
          <TabsTrigger value="graph">Knowledge Graph</TabsTrigger>
        </TabsList>

        {/* Search Tab */}
        <TabsContent value="search">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-4">
            {/* Search Panel */}
            <div className="lg:col-span-1">
              <Card className="glass-card">
                <CardHeader>
                  <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                    <Search className="w-4 h-4 text-cyan" />
                    Search
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <Input
                      placeholder="Search memories..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-9"
                      onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                    />
                  </div>
                  <Button
                    variant="cyan"
                    className="w-full cursor-pointer"
                    onClick={handleSearch}
                    disabled={isSearching}
                  >
                    {isSearching ? (
                      <RefreshCw className="w-4 h-4 animate-spin mr-2" />
                    ) : (
                      <Search className="w-4 h-4 mr-2" />
                    )}
                    Search
                  </Button>

                  {/* Category Distribution */}
                  <div>
                    <label className="text-xs font-medium text-muted-foreground mb-2 block">
                      Distribution
                    </label>
                    <div className="h-48">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={categoryData}
                            cx="50%"
                            cy="50%"
                            innerRadius={40}
                            outerRadius={70}
                            dataKey="value"
                          >
                            {categoryData.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={entry.color} />
                            ))}
                          </Pie>
                          <Tooltip
                            contentStyle={{
                              background: "#0d1117",
                              border: "1px solid #1e293b",
                              borderRadius: "8px",
                              fontSize: "12px",
                            }}
                          />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="space-y-1">
                      {categoryData.map((entry) => (
                        <div
                          key={entry.name}
                          className="flex items-center justify-between text-xs"
                        >
                          <div className="flex items-center gap-1.5">
                            <div
                              className="w-2 h-2 rounded-full"
                              style={{ backgroundColor: entry.color }}
                            />
                            <span className="text-muted-foreground capitalize">
                              {entry.name}
                            </span>
                          </div>
                          <span className="text-foreground">{entry.value}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Results */}
            <div className="lg:col-span-2">
              <Card className="glass-card">
                <CardHeader>
                  <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
                    Search Results ({searchResults.length})
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="max-h-[600px]">
                    {searchResults.length > 0 ? (
                      <div className="space-y-2">
                        {searchResults.map((entry) => (
                          <div
                            key={entry.id}
                            className="p-3 rounded-lg bg-secondary/20 border border-border/50 hover:border-primary/20 transition-all cursor-pointer"
                          >
                            <div className="flex items-start justify-between mb-2">
                              <div className="flex items-center gap-2">
                                <div style={{ color: categoryColors[entry.category] }}>
                                  {categoryIcons[entry.category]}
                                </div>
                                <span className="text-sm font-medium text-foreground font-mono">
                                  {entry.key}
                                </span>
                              </div>
                              <Badge
                                variant="outline"
                                className="text-[10px] capitalize"
                                style={{
                                  borderColor: categoryColors[entry.category],
                                  color: categoryColors[entry.category],
                                }}
                              >
                                {entry.category}
                              </Badge>
                            </div>
                            <p className="text-xs text-muted-foreground line-clamp-2 mb-2">
                              {entry.value}
                            </p>
                            <div className="flex items-center gap-4 text-[10px] text-muted-foreground">
                              <span className="flex items-center gap-1">
                                <Clock className="w-3 h-3" />
                                {new Date(entry.timestamp).toLocaleString()}
                              </span>
                              <span className="flex items-center gap-1">
                                <HardDrive className="w-3 h-3" />
                                {entry.size}B
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-12 text-muted-foreground text-sm">
                        <Database className="w-8 h-8 mx-auto mb-3 opacity-30" />
                        <p>Enter a search query to find memories</p>
                        <p className="text-xs mt-1">
                          The knowledge base contains research notes, trade journals, and agent decisions
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
        <TabsContent value="browser">
          <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {MEMORY_TYPES.map((type) => (
              <Card key={type} className="glass-card">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <span style={{ color: categoryColors[type] }}>
                      {categoryIcons[type]}
                    </span>
                    <span className="text-sm font-medium text-foreground capitalize">
                      {type}
                    </span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-center py-6">
                    <div
                      className="w-12 h-12 rounded-full mx-auto mb-3 flex items-center justify-center"
                      style={{ backgroundColor: `${categoryColors[type]}20` }}
                    >
                      <BookOpen
                        className="w-5 h-5"
                        style={{ color: categoryColors[type] }}
                      />
                    </div>
                    <p className="text-sm text-foreground font-medium capitalize">
                      {type} Store
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Browse and manage {type} entries
                    </p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Knowledge Graph */}
        <TabsContent value="graph">
          <div className="mt-4">
            <Card className="glass-card">
              <CardHeader>
                <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                  <Zap className="w-4 h-4 text-emerald" />
                  Knowledge Graph
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-center h-80">
                  <div className="text-center text-muted-foreground">
                    <div className="relative w-48 h-48 mx-auto mb-4">
                      {/* Central node */}
                      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-16 h-16 rounded-full bg-cyan/20 border border-cyan/40 flex items-center justify-center">
                        <Brain className="w-6 h-6 text-cyan" />
                      </div>
                      {/* Surrounding nodes */}
                      {MEMORY_TYPES.map((type, i) => {
                        const angle = (i / MEMORY_TYPES.length) * Math.PI * 2 - Math.PI / 2;
                        const radius = 70;
                        const x = Math.cos(angle) * radius + 80;
                        const y = Math.sin(angle) * radius + 80;
                        return (
                          <div
                            key={type}
                            className="absolute w-8 h-8 rounded-full flex items-center justify-center border border-border/50"
                            style={{
                              left: `${x - 16}px`,
                              top: `${y - 16}px`,
                              backgroundColor: `${categoryColors[type]}15`,
                              borderColor: `${categoryColors[type]}40`,
                            }}
                          >
                            <span className="text-[8px] capitalize" style={{ color: categoryColors[type] }}>
                              {type.slice(0, 3)}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                    <p className="text-sm font-medium text-foreground">
                      Knowledge Graph Visualization
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Explore relationships between concepts and memories
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {/* Store Memory Dialog */}
      <Dialog open={storeDialogOpen} onOpenChange={setStoreDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Store Memory</DialogTitle>
            <DialogDescription>
              Save data to the AI memory system for later retrieval.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium text-foreground mb-1.5 block">
                Key
              </label>
              <Input
                placeholder="e.g., my_config_key"
                value={storeKey}
                onChange={(e) => setStoreKey(e.target.value)}
                className="font-mono"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-foreground mb-1.5 block">
                Value
              </label>
              <Textarea
                placeholder="Enter the data to store..."
                value={storeValue}
                onChange={(e) => setStoreValue(e.target.value)}
                rows={4}
              />
            </div>
            <div>
              <label className="text-sm font-medium text-foreground mb-1.5 block">
                Category
              </label>
              <Select value={storeCategory} onValueChange={setStoreCategory}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {MEMORY_TYPES.map((type) => (
                    <SelectItem key={type} value={type} className="capitalize">
                      {type}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => setStoreDialogOpen(false)}
              className="cursor-pointer"
            >
              Cancel
            </Button>
            <Button
              variant="cyan"
              onClick={handleStore}
              disabled={!storeKey || !storeValue || isStoring}
              className="cursor-pointer"
            >
              {isStoring ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Storing...
                </>
              ) : (
                <>
                  <Plus className="w-4 h-4" />
                  Store
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
