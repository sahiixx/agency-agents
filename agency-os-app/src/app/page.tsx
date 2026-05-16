"use client";

import { trpc } from "@/lib/api";
import { StatsCards } from "@/components/stats-cards";
import { Terminal } from "@/components/terminal";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { useState } from "react";
import { Zap, Activity } from "lucide-react";

export default function Home() {
  const utils = trpc.useUtils();
  const { data: agents } = trpc.agent.list.useQuery();
  const { data: crawls } = trpc.crawl.list.useQuery();
  const queue = trpc.crawl.queue.useMutation({ onSuccess: () => utils.crawl.list.invalidate() });
  const runAgent = trpc.agent.run.useMutation();

  const [url, setUrl] = useState("");
  const [engine, setEngine] = useState("auto");
  const [agentInput, setAgentInput] = useState("");

  return (
    <div className="min-h-screen p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-primary to-blue-500 bg-clip-text text-transparent">
            Agency OS
          </h1>
          <p className="text-sm text-muted-foreground mt-1">The Control Plane for The Agency</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-xs text-muted-foreground">System Online</span>
        </div>
      </div>

      <StatsCards />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-amber-400" />
              Quick Crawl
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Input
              placeholder="https://example.com"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
            <Select value={engine} onChange={(e) => setEngine(e.target.value)}>
              <option value="auto">Auto</option>
              <option value="crawlee">Crawlee</option>
              <option value="scrapling">Scrapling</option>
              <option value="requests">Requests</option>
            </Select>
            <Button
              className="w-full"
              onClick={() => queue.mutate({ url, engine })}
              disabled={!url || queue.isPending}
            >
              {queue.isPending ? "Queueing..." : "Queue Crawl"}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-emerald-400" />
              Agent Quick Run
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Select
              value={agentInput}
              onChange={(e) => setAgentInput(e.target.value)}
            >
              <option value="">Select agent...</option>
              {agents?.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </Select>
            <Button
              className="w-full"
              onClick={() =>
                agentInput && runAgent.mutate({ agentId: agentInput, query: "Execute your primary function" })
              }
              disabled={!agentInput || runAgent.isPending}
            >
              {runAgent.isPending ? "Running..." : "Run Agent"}
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card className="h-[400px]">
        <CardHeader>
          <CardTitle>Live Terminal</CardTitle>
        </CardHeader>
        <CardContent className="h-[calc(100%-80px)]">
          <Terminal />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Recent Crawls</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {crawls?.slice(0, 5).map((c) => (
              <div
                key={c.id}
                className="flex items-center justify-between rounded-lg border border-border px-4 py-2"
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`h-2 w-2 rounded-full ${
                      c.status === "done"
                        ? "bg-emerald-500"
                        : c.status === "running"
                        ? "bg-amber-500 animate-pulse"
                        : "bg-muted"
                    }`}
                  />
                  <span className="text-sm font-medium truncate max-w-[300px]">{c.url}</span>
                </div>
                <span className="text-xs text-muted-foreground uppercase">{c.status}</span>
              </div>
            ))}
            {(!crawls || crawls.length === 0) && (
              <p className="text-sm text-muted-foreground">No crawls yet. Queue one above.</p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
