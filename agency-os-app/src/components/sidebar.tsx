"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Home, Bot, Globe, ListTodo, Database, Shield, Command } from "lucide-react";

const navItems = [
  { href: "/", label: "Dashboard", icon: Home },
  { href: "/agents", label: "Agents", icon: Bot },
  { href: "/crawls", label: "Crawls", icon: Globe },
  { href: "/jobs", label: "Jobs", icon: ListTodo },
  { href: "/results", label: "Results", icon: Database },
  { href: "/proxies", label: "Proxies", icon: Shield },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 z-40 flex h-screen w-16 flex-col border-r border-border bg-background/80 backdrop-blur-xl">
      <div className="flex h-14 items-center justify-center border-b border-border">
        <Command className="h-5 w-5 text-primary" />
      </div>
      <nav className="flex flex-1 flex-col items-center gap-1 py-4">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "group relative flex h-10 w-10 items-center justify-center rounded-lg text-muted-foreground transition-all hover:bg-primary/10 hover:text-primary",
              pathname === item.href && "bg-primary/15 text-primary shadow-[0_0_20px_rgba(56,189,248,0.2)]"
            )}
          >
            <item.icon className="h-4 w-4" />
            <span className="absolute left-12 rounded-md bg-popover px-2 py-1 text-xs font-medium opacity-0 transition-all group-hover:opacity-100 border border-border">
              {item.label}
            </span>
          </Link>
        ))}
      </nav>
    </aside>
  );
}
