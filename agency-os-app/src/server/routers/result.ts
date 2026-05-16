import { z } from "zod";
import { createTRPCRouter, publicProcedure } from "@/server/trpc";

export const resultRouter = createTRPCRouter({
  list: publicProcedure.query(async ({ ctx }) => {
    return ctx.prisma.result.findMany({
      include: { job: { select: { name: true, url: true } } },
      orderBy: { createdAt: "desc" },
      take: 200,
    });
  }),

  byJob: publicProcedure
    .input(z.object({ jobId: z.string() }))
    .query(async ({ ctx, input }) => {
      return ctx.prisma.result.findMany({ where: { jobId: input.jobId }, orderBy: { createdAt: "desc" } });
    }),
});
