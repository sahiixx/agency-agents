"use client";

import { trpc } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useState } from "react";
import { Bot, Search, Play } from "lucide-react";

export default function AgentsPage() {
  const { data: agents } = trpc.agent.list.useQuery();
  const runAgent = trpc.agent.run.useMutation();
  const [filter, setFilter] = useState("");
  const [running, setRunning] = useState<string | null>(null);

  const filtered = agents?.filter(
    (a) =>
      a.name.toLowerCase().includes(filter.toLowerCase()) ||
      (a.description && a.description.toLowerCase().includes(filter.toLowerCase()))
  );

  const handleRun = (id: string) => {
    setRunning(id);
    runAgent.mutate(
      { agentId: id, query: "Execute your primary function" },
      { onSettled: () => setRunning(null) }
    );
  };

  return (
    <div className="min-h-screen p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Agents</h1>
        <p className="text-sm text-muted-foreground">{agents?.length ?? 0} skills loaded</p>
      </div>

      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search agents..."
          className="pl-9"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered?.map((agent) => (
          <Card key={agent.id} className="group transition-all hover:border-primary/50">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Bot className="h-4 w-4 text-primary" />
                  <CardTitle className="text-sm">{agent.name}</CardTitle>
                </div>
                {agent.category && (
                  <Badge variant="info" className="text-[10px]">
                    {agent.category}
                  </Badge>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-xs text-muted-foreground line-clamp-2">
                {agent.description || "No description"}
              </p>
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">
                  Runs: {agent.runCount}
                </span>
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-7 gap-1"
                  onClick={() => handleRun(agent.id)}
                  disabled={running === agent.id}
                >
                  <Play className="h-3 w-3" />
                  {running === agent.id ? "..." : "Run"}
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
