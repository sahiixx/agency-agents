"use client";

import { trpc } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Bot, ListTodo, Database, Shield, Globe } from "lucide-react";

const icons = {
  agents: Bot,
  jobs: ListTodo,
  results: Database,
  proxies: Shield,
  crawls: Globe,
};

const gradients = {
  agents: "from-amber-400 to-orange-500",
  jobs: "from-cyan-400 to-blue-500",
  results: "from-emerald-400 to-green-500",
  proxies: "from-rose-400 to-red-500",
  crawls: "from-violet-400 to-purple-500",
};

export function StatsCards() {
  const { data: stats } = trpc.crawl.list.useQuery();
  const { data: agents } = trpc.agent.list.useQuery();
  const { data: jobs } = trpc.job.list.useQuery();
  const { data: results } = trpc.result.list.useQuery();
  const { data: proxies } = trpc.proxy.list.useQuery();

  const data = {
    agents: agents?.length ?? 0,
    jobs: jobs?.length ?? 0,
    results: results?.length ?? 0,
    proxies: proxies?.length ?? 0,
    crawls: stats?.length ?? 0,
  };

  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
      {Object.entries(data).map(([key, value]) => {
        const Icon = icons[key as keyof typeof icons];
        const gradient = gradients[key as keyof typeof gradients];
        return (
          <Card key={key} className="relative overflow-hidden">
            <CardContent className="p-5">
              <div className="flex items-center justify-between">
                <Icon className="h-5 w-5 text-muted-foreground" />
                <div className={`bg-gradient-to-r ${gradient} bg-clip-text text-3xl font-bold text-transparent`}>
                  {value}
                </div>
              </div>
              <p className="mt-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                {key}
              </p>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
