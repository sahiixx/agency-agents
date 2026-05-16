import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";
import { Sidebar } from "@/components/sidebar";
import { WSProvider } from "@/components/ws-provider";

export const metadata: Metadata = {
  title: "Agency OS",
  description: "The Control Plane for The Agency",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="bg-background text-foreground antialiased">
        <Providers>
          <WSProvider>
            <Sidebar />
            <main className="pl-16">{children}</main>
          </WSProvider>
        </Providers>
      </body>
    </html>
  );
}
