import { z } from "zod";
import { createTRPCRouter, publicProcedure } from "@/server/trpc";
import { spawn } from "child_process";
import { broadcast } from "@/server/ws";

export const jobRouter = createTRPCRouter({
  list: publicProcedure.query(async ({ ctx }) => {
    return ctx.prisma.job.findMany({
      include: { agent: { select: { name: true } } },
      orderBy: { createdAt: "desc" },
      take: 100,
    });
  }),

  create: publicProcedure
    .input(z.object({ name: z.string(), agentId: z.string(), query: z.string() }))
    .mutation(async ({ ctx, input }) => {
      return ctx.prisma.job.create({
        data: { name: input.name, agentId: input.agentId, query: input.query, status: "pending" },
      });
    }),

  run: publicProcedure
    .input(z.object({ id: z.string() }))
    .mutation(async ({ ctx, input }) => {
      const job = await ctx.prisma.job.update({
        where: { id: input.id },
        data: { status: "running", startedAt: new Date() },
      });
      const agent = await ctx.prisma.agent.findUnique({ where: { id: job.agentId } });
      if (!agent) throw new Error("Agent not found");

      broadcast({ type: "job_started", jobId: job.id, line: `Job ${job.name} started` });

      const proc = spawn("kimi", ["--quiet", "--yolo", "--agent-file", agent.filePath || "", "--prompt", job.query], {
        env: { ...process.env, WORK_DIR: `/tmp/agency-job-${job.id}` },
        timeout: 300000,
      });

      let output = "";
      proc.stdout.on("data", (d) => {
        const line = d.toString();
        output += line;
        broadcast({ type: "log", jobId: job.id, line });
      });
      proc.stderr.on("data", (d) => {
        const line = d.toString();
        output += line;
        broadcast({ type: "log", jobId: job.id, line: `[ERR] ${line}` });
      });

      proc.on("close", async (code) => {
        await ctx.prisma.job.update({
          where: { id: job.id },
          data: { status: code === 0 ? "completed" : "failed", completedAt: new Date(), output },
        });
        broadcast({ type: "job_completed", jobId: job.id, status: code === 0 ? "done" : "error", line: `Job ${job.name} ${code === 0 ? "completed" : "failed"}` });
      });

      return job;
    }),

  delete: publicProcedure
    .input(z.object({ id: z.string() }))
    .mutation(async ({ ctx, input }) => {
      return ctx.prisma.job.delete({ where: { id: input.id } });
    }),
});
