import { createTRPCRouter } from "@/server/trpc";
import { agentRouter } from "@/server/routers/agent";
import { crawlRouter } from "@/server/routers/crawl";
import { jobRouter } from "@/server/routers/job";
import { resultRouter } from "@/server/routers/result";
import { proxyRouter } from "@/server/routers/proxy";

export const appRouter = createTRPCRouter({
  agent: agentRouter,
  crawl: crawlRouter,
  job: jobRouter,
  result: resultRouter,
  proxy: proxyRouter,
});

export type AppRouter = typeof appRouter;
