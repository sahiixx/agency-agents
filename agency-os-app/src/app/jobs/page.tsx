"use client";

import { trpc } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { useState } from "react";
import { ListTodo, Play, Trash2 } from "lucide-react";

export default function JobsPage() {
  const utils = trpc.useUtils();
  const { data: jobs } = trpc.job.list.useQuery();
  const create = trpc.job.create.useMutation({ onSuccess: () => utils.job.list.invalidate() });
  const run = trpc.job.run.useMutation({ onSuccess: () => utils.job.list.invalidate() });
  const remove = trpc.job.delete.useMutation({ onSuccess: () => utils.job.list.invalidate() });

  const [name, setName] = useState("");
  const [agentId, setAgentId] = useState("");
  const [query, setQuery] = useState("");
  const { data: agents } = trpc.agent.list.useQuery();

  return (
    <div className="min-h-screen p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Jobs</h1>
        <p className="text-sm text-muted-foreground">Agent execution jobs</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ListTodo className="h-4 w-4" />
            New Job
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Input placeholder="Job name" value={name} onChange={(e) => setName(e.target.value)} />
          <Select value={agentId} onChange={(e) => setAgentId(e.target.value)}>
            <option value="">Select agent...</option>
            {agents?.map((a) => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </Select>
          <Input placeholder="Query / prompt" value={query} onChange={(e) => setQuery(e.target.value)} />
          <Button
            className="w-full"
            onClick={() => create.mutate({ name, agentId, query })}
            disabled={!name || !agentId || create.isPending}
          >
            {create.isPending ? "Creating..." : "Create Job"}
          </Button>
        </CardContent>
      </Card>

      <div className="space-y-2">
        {jobs?.map((job) => (
          <div key={job.id} className="flex items-center justify-between rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-3">
              <div className={`h-2 w-2 rounded-full ${
                job.status === "completed" ? "bg-emerald-500" :
                job.status === "running" ? "bg-amber-500 animate-pulse" :
                job.status === "failed" ? "bg-red-500" : "bg-muted"
              }`} />
              <div>
                <p className="text-sm font-medium">{job.name}</p>
                <p className="text-xs text-muted-foreground">
                  {job.agent?.name} · {new Date(job.createdAt).toLocaleString()}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant={job.status === "completed" ? "success" : job.status === "running" ? "warning" : job.status === "failed" ? "destructive" : "default"}>
                {job.status}
              </Badge>
              <Button size="sm" variant="ghost" className="h-7" onClick={() => run.mutate({ id: job.id })} disabled={job.status === "running"}>
                <Play className="h-3 w-3" />
              </Button>
              <Button size="sm" variant="ghost" className="h-7 text-destructive" onClick={() => remove.mutate({ id: job.id })}>
                <Trash2 className="h-3 w-3" />
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
