import { z } from "zod";
import { createTRPCRouter, publicProcedure } from "@/server/trpc";
import { spawn } from "child_process";
import { broadcast } from "@/server/ws";

export const crawlRouter = createTRPCRouter({
  list: publicProcedure.query(async ({ ctx }) => {
    return ctx.prisma.crawlJob.findMany({ orderBy: { createdAt: "desc" } });
  }),

  queue: publicProcedure
    .input(z.object({ url: z.string().url(), engine: z.string().default("auto"), selector: z.string().optional() }))
    .mutation(async ({ ctx, input }) => {
      const job = await ctx.prisma.crawlJob.create({
        data: { url: input.url, engine: input.engine, selector: input.selector || null, status: "queued" },
      });

      broadcast({ type: "job_started", jobId: job.id, line: `Crawl queued: ${input.url}` });

      // Auto-start crawl in background
      const script = `
import json, sys, time, os
sys.path.insert(0, "${process.cwd()}")
from scraping_os.unified_crawler import UnifiedCrawler
crawler = UnifiedCrawler(engine="${input.engine}")
result = crawler.run("${input.url}", selector="${input.selector or ""}")
print(json.dumps({"count": len(result), "items": result[:50]}))
`;
      const proc = spawn("python3", ["-c", script], { timeout: 60000 });
      let stdout = "";
      proc.stdout.on("data", (d) => { stdout += d.toString(); });

      proc.on("close", async () => {
        try {
          const out = JSON.parse(stdout.trim().split("\\n").pop() || "{}");
          const items = out.items || [];
          await ctx.prisma.crawlJob.update({
            where: { id: job.id },
            data: { status: "done", resultCount: items.length, completedAt: new Date() },
          });
          for (const item of items) {
            await ctx.prisma.result.create({
              data: { jobId: job.id, source: input.url, data: item },
            });
          }
          broadcast({ type: "job_completed", jobId: job.id, status: "done", line: `Crawl done: ${items.length} items` });
        } catch (e) {
          await ctx.prisma.crawlJob.update({
            where: { id: job.id },
            data: { status: "failed", error: String(e), completedAt: new Date() },
          });
          broadcast({ type: "job_completed", jobId: job.id, status: "error", line: `Crawl failed: ${String(e)}` });
        }
      });

      return job;
    }),

  delete: publicProcedure
    .input(z.object({ id: z.string() }))
    .mutation(async ({ ctx, input }) => {
      await ctx.prisma.crawlJob.delete({ where: { id: input.id } });
      return { deleted: true };
    }),
});
