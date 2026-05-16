"use client";

import { trpc } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useState } from "react";
import { Shield, Plus, Trash2 } from "lucide-react";

export default function ProxiesPage() {
  const utils = trpc.useUtils();
  const { data: proxies } = trpc.proxy.list.useQuery();
  const create = trpc.proxy.create.useMutation({ onSuccess: () => utils.proxy.list.invalidate() });
  const remove = trpc.proxy.delete.useMutation({ onSuccess: () => utils.proxy.list.invalidate() });

  const [host, setHost] = useState("");
  const [port, setPort] = useState("");
  const [protocol, setProtocol] = useState("http");

  return (
    <div className="min-h-screen p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Proxies</h1>
        <p className="text-sm text-muted-foreground">Proxy rotation management</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-4 w-4" />
            Add Proxy
          </CardTitle>
        </CardHeader>
        <CardContent className="flex gap-3">
          <Input placeholder="Host" value={host} onChange={(e) => setHost(e.target.value)} className="flex-1" />
          <Input placeholder="Port" value={port} onChange={(e) => setPort(e.target.value)} className="w-24" />
          <Input placeholder="Protocol" value={protocol} onChange={(e) => setProtocol(e.target.value)} className="w-24" />
          <Button
            onClick={() => {
              create.mutate({ host, port: parseInt(port) || 8080, protocol });
              setHost(""); setPort("");
            }}
            disabled={!host || !port}
          >
            <Plus className="h-4 w-4" />
          </Button>
        </CardContent>
      </Card>

      <div className="space-y-2">
        {proxies?.map((p) => (
          <div key={p.id} className="flex items-center justify-between rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-3">
              <Shield className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-sm font-medium">{p.host}:{p.port}</p>
                <p className="text-xs text-muted-foreground">{p.protocol}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Badge variant={p.status === "active" ? "success" : "destructive"}>{p.status}</Badge>
              <Button size="sm" variant="ghost" className="h-7 text-destructive" onClick={() => remove.mutate({ id: p.id })}>
                <Trash2 className="h-3 w-3" />
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
