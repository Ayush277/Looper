"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/", label: "Home", icon: "◈" },
  { href: "/companies", label: "Companies", icon: "▤" },
  { href: "/keywords", label: "Keywords", icon: "#" },
  { href: "/discovery", label: "Discovery", icon: "◎" },
  { href: "/scheduler", label: "Scheduler", icon: "◷" },
  { href: "/email", label: "Email", icon: "✉" },
  { href: "/jobs", label: "Jobs", icon: "▣" },
  { href: "/history", label: "History", icon: "≡" },
  { href: "/stats", label: "Statistics", icon: "∿" },
  { href: "/settings", label: "Settings", icon: "⚙" },
] as const;

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="fixed inset-y-0 left-0 w-[232px] border-r border-border bg-card flex flex-col">
      <div className="px-5 py-5 flex items-center gap-2">
        <span className="text-primary text-xl leading-none">◈</span>
        <span className="font-semibold tracking-tight">LoopJob</span>
      </div>
      <nav className="flex-1 px-2 space-y-0.5">
        {NAV.map((item) => {
          const active =
            item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                active
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:text-foreground hover:bg-border/40"
              }`}
            >
              <span className="w-4 text-center">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="px-5 py-4 text-xs text-muted-foreground border-t border-border">
        Never miss another opening.
      </div>
    </aside>
  );
}
