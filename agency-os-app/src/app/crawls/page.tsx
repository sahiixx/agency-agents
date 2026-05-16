"use client";

import { trpc } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { useState } from "react";
import { Globe, RefreshCw } from "lucide-react";

export default function CrawlsPage() {
  const utils = trpc.useUtils();
  const { data: crawls } = trpc.crawl.list.useQuery();
  const queue = trpc.crawl.queue.useMutation({ onSuccess: () => utils.crawl.list.invalidate() });
  const [url, setUrl] = useState("");
  const [engine, setEngine] = useState("auto");

  return (
    <div className="min-h-screen p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Crawls</h1>
        <p className="text-sm text-muted-foreground">Manage web scraping jobs</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Globe className="h-4 w-4" />
            New Crawl
          </CardTitle>
        </CardHeader>
        <CardContent className="flex gap-3">
          <Input
            placeholder="https://example.com"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="flex-1"
          />
          <Select value={engine} onChange={(e) => setEngine(e.target.value)} className="w-32">
            <option value="auto">Auto</option>
            <option value="crawlee">Crawlee</option>
            <option value="scrapling">Scrapling</option>
            <option value="requests">Requests</option>
          </Select>
          <Button
            onClick={() => queue.mutate({ url, engine })}
            disabled={!url || queue.isPending}
          >
            {queue.isPending ? <RefreshCw className="h-4 w-4 animate-spin" /> : "Queue"}
          </Button>
        </CardContent>
      </Card>

      <div className="space-y-2">
        {crawls?.map((c) => (
          <div
            key={c.id}
            className="flex items-center justify-between rounded-xl border border-border bg-card p-4"
          >
            <div className="flex items-center gap-3">
              <div
                className={`h-2 w-2 rounded-full ${
                  c.status === "done"
                    ? "bg-emerald-500"
                    : c.status === "running"
                    ? "bg-amber-500 animate-pulse"
                    : c.status === "error"
                    ? "bg-red-500"
                    : "bg-muted"
                }`}
              />
              <div>
                <p className="text-sm font-medium">{c.url}</p>
                <p className="text-xs text-muted-foreground">
                  {c.engine} · {new Date(c.createdAt).toLocaleString()}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Badge
                variant={
                  c.status === "done"
                    ? "success"
                    : c.status === "running"
                    ? "warning"
                    : c.status === "error"
                    ? "destructive"
                    : "default"
                }
              >
                {c.status}
              </Badge>
              <span className="text-xs text-muted-foreground">{c.resultCount} results</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
