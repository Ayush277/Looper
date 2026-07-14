"use client";

import { useEffect, useState } from "react";
import { api, healthColor } from "@/lib/api";

type Funnel = {
  found: number; passed_exclusions: number; matched: number;
  emailed: number; applied: number;
};
type CompanyStat = { name: string; health: string; jobs: number; matched: number };
type Day = { date: string; found: number; matched: number; emailed: number };

export default function StatsPage() {
  const [funnel, setFunnel] = useState<Funnel | null>(null);
  const [companies, setCompanies] = useState<CompanyStat[]>([]);
  const [days, setDays] = useState<Day[]>([]);

  useEffect(() => {
    api<Funnel>("/stats/funnel").then(setFunnel);
    api<CompanyStat[]>("/stats/companies").then(setCompanies);
    api<{ days: Day[] }>("/stats/timeseries?days=14").then((d) => setDays(d.days));
  }, []);

  const maxJobs = Math.max(1, ...companies.map((c) => c.jobs));
  const maxDay = Math.max(1, ...days.map((d) => d.found));
  const stages = funnel
    ? [
        ["Found", funnel.found],
        ["Passed exclusions", funnel.passed_exclusions],
        ["Matched", funnel.matched],
        ["Emailed", funnel.emailed],
        ["Applied", funnel.applied],
      ] as const
    : [];

  return (
    <div className="space-y-6">
      <h1 className="text-[22px] font-semibold tracking-tight">Statistics</h1>

      <div className="rounded-[10px] border border-border bg-card p-5">
        <div className="mb-4 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          Pipeline funnel (all time)
        </div>
        <div className="space-y-2">
          {stages.map(([label, value]) => (
            <div key={label} className="flex items-center gap-3 text-sm">
              <span className="w-36 text-muted-foreground">{label}</span>
              <div className="h-6 flex-1 overflow-hidden rounded bg-border/30">
                <div
                  className="h-full rounded bg-primary/70"
                  style={{ width: `${(value / Math.max(1, funnel!.found)) * 100}%` }}
                />
              </div>
              <span className="w-12 text-right font-semibold tabular-nums">{value}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-[10px] border border-border bg-card p-5">
          <div className="mb-4 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            Jobs per company
          </div>
          <div className="space-y-2">
            {companies.map((c) => (
              <div key={c.name} className="flex items-center gap-3 text-sm">
                <span className="w-24 truncate">{c.name}</span>
                <span className={`w-4 ${healthColor[c.health]}`}>●</span>
                <div className="h-5 flex-1 overflow-hidden rounded bg-border/30">
                  <div
                    className="h-full rounded bg-accent/60"
                    style={{ width: `${(c.jobs / maxJobs) * 100}%` }}
                  />
                </div>
                <span className="w-20 text-right tabular-nums text-muted-foreground">
                  {c.jobs} <span className="text-primary">({c.matched})</span>
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-[10px] border border-border bg-card p-5">
          <div className="mb-4 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            Last 14 days — found vs matched
          </div>
          {days.length === 0 ? (
            <div className="py-8 text-center text-sm text-muted-foreground">
              Data accumulates as scans run.
            </div>
          ) : (
            <div className="flex h-40 items-end gap-1.5">
              {days.map((d) => (
                <div key={d.date} className="group relative flex-1">
                  <div
                    className="w-full rounded-t bg-border/60"
                    style={{ height: `${(d.found / maxDay) * 140}px` }}
                  />
                  <div
                    className="absolute bottom-0 w-full rounded-t bg-primary/80"
                    style={{ height: `${(d.matched / maxDay) * 140}px` }}
                  />
                  <div className="absolute -top-6 left-1/2 hidden -translate-x-1/2 whitespace-nowrap rounded bg-background px-1.5 py-0.5 text-[10px] group-hover:block">
                    {d.date}: {d.found} / {d.matched}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
