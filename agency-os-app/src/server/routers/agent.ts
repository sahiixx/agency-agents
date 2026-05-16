import { z } from "zod";
import { createTRPCRouter, publicProcedure } from "@/server/trpc";
import { spawn } from "child_process";
import path from "path";
import { broadcast } from "@/server/ws";
import fs from "fs";

const SKILLS_DIR = process.env.HOME
  ? path.join(process.env.HOME, ".agents", "skills")
  : path.join(process.cwd(), ".agents", "skills");

function scanAgents() {
  if (!fs.existsSync(SKILLS_DIR)) return [];
  const agents: { id: string; name: string; description: string; category: string; filePath: string }[] = [];
  for (const dir of fs.readdirSync(SKILLS_DIR)) {
    const skillFile = path.join(SKILLS_DIR, dir, "SKILL.md");
    if (!fs.existsSync(skillFile)) continue;
    const content = fs.readFileSync(skillFile, "utf-8");
    const lines = content.split("\n");
    const name = lines[0]?.replace(/^#\s*/, "").trim() || dir;
    const desc = lines.slice(1, 5).join(" ").trim().slice(0, 200);
    const category = dir.split("-")[0] || "general";
    agents.push({ id: dir, name, description: desc, category, filePath: skillFile });
  }
  return agents;
}

export const agentRouter = createTRPCRouter({
  list: publicProcedure.query(async ({ ctx }) => {
    const dbAgents = await ctx.prisma.agent.findMany({ orderBy: { category: "asc" } });
    if (dbAgents.length > 0) return dbAgents;
    // Seed from filesystem on first run
    const scanned = scanAgents();
    for (const a of scanned) {
      await ctx.prisma.agent.upsert({
        where: { id: a.id },
        update: {},
        create: a,
      });
    }
    return scanned;
  }),

  run: publicProcedure
    .input(z.object({ agentId: z.string(), query: z.string() }))
    .mutation(async ({ ctx, input }) => {
      const agent = await ctx.prisma.agent.findUnique({ where: { id: input.agentId } });
      if (!agent) throw new Error("Agent not found");

      broadcast({ type: "job_started", jobId: input.agentId, line: `Running agent: ${agent.name}` });

      const proc = spawn("kimi", [
        "--quiet", "--yolo",
        "--agent-file", agent.filePath || "",
        "--prompt", input.query,
      ], { timeout: 300000, env: { ...process.env, WORK_DIR: `/tmp/agency-${input.agentId}` } });

      let output = "";
      let error = "";
      proc.stdout.on("data", (d) => {
        output += d.toString();
        broadcast({ type: "log", jobId: input.agentId, line: d.toString() });
      });
      proc.stderr.on("data", (d) => {
        error += d.toString();
        broadcast({ type: "log", jobId: input.agentId, line: `[ERR] ${d.toString()}` });
      });

      return new Promise((resolve) => {
        proc.on("close", async (code) => {
          const isOk = code === 0;
          await ctx.prisma.agent.update({
            where: { id: agent.id },
            data: { runCount: { increment: 1 }, lastRunAt: new Date() },
          });
          broadcast({ type: "job_completed", jobId: input.agentId, status: isOk ? "done" : "error", line: `Agent ${agent.name} ${isOk ? "done" : "failed"}` });
          resolve({ ok: isOk, output, error: error || null });
        });
      });
    }),
});
