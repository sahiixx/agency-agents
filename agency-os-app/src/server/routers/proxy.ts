import { z } from "zod";
import { createTRPCRouter, publicProcedure } from "@/server/trpc";

export const proxyRouter = createTRPCRouter({
  list: publicProcedure.query(async ({ ctx }) => {
    return ctx.prisma.proxy.findMany({ orderBy: { lastUsedAt: "desc" } });
  }),

  create: publicProcedure
    .input(z.object({ host: z.string(), port: z.number(), protocol: z.string().default("http") }))
    .mutation(async ({ ctx, input }) => {
      return ctx.prisma.proxy.create({ data: input });
    }),

  delete: publicProcedure
    .input(z.object({ id: z.string() }))
    .mutation(async ({ ctx, input }) => {
      return ctx.prisma.proxy.delete({ where: { id: input.id } });
    }),
});
