"use client";

import { trpc } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { useState } from "react";
import { Database } from "lucide-react";

export default function ResultsPage() {
  const { data: results } = trpc.result.list.useQuery();
  const [filter, setFilter] = useState("");

  const filtered = results?.filter((r) =>
    JSON.stringify(r.data).toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div className="min-h-screen p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Results</h1>
        <p className="text-sm text-muted-foreground">Crawl and agent output data</p>
      </div>

      <div className="relative max-w-md">
        <Input
          placeholder="Filter results..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </div>

      <div className="grid grid-cols-1 gap-2">
        {filtered?.map((r) => (
          <Card key={r.id}>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Database className="h-3 w-3 text-primary" />
                  {r.job?.name || r.jobId}
                </CardTitle>
                <Badge variant="info" className="text-[10px]">{r.source}</Badge>
              </div>
            </CardHeader>
            <CardContent>
              <pre className="text-xs bg-black/40 rounded-lg p-3 overflow-auto max-h-40">
                {JSON.stringify(r.data, null, 2)}
              </pre>
              <p className="text-xs text-muted-foreground mt-2">
                {new Date(r.createdAt).toLocaleString()}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
