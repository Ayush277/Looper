"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Run = {
  id: string; trigger: string; status: string; started_at: string;
  finished_at: string | null; companies_total: number; companies_ok: number;
  companies_failed: number; jobs_found: number; jobs_new: number; jobs_matched: number;
};
type RunDetail = {
  companies: {
    company: string; strategy: string; status: string; jobs_found: number;
    jobs_new: number; duration_ms: number | null; error: string | null;
  }[];
};

export default function HistoryPage() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [open, setOpen] = useState<string | null>(null);
  const [detail, setDetail] = useState<RunDetail | null>(null);

  useEffect(() => {
    api<{ items: Run[] }>("/scans").then((d) => setRuns(d.items));
  }, []);

  async function toggle(id: string) {
    if (open === id) return setOpen(null);
    setOpen(id);
    setDetail(null);
    setDetail(await api<RunDetail>(`/scans/${id}`));
  }

  return (
    <div className="space-y-4">
      <h1 className="text-[22px] font-semibold tracking-tight">History</h1>
      <div className="space-y-2">
        {runs.map((r) => (
          <div key={r.id} className="rounded-[10px] border border-border bg-card">
            <button
              onClick={() => toggle(r.id)}
              className="flex w-full flex-wrap items-center gap-x-6 gap-y-1 px-4 py-3 text-left text-sm"
            >
              <span className="font-medium">
                {new Date(r.started_at).toLocaleString("en-IN", {
                  day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
                })}
              </span>
              <span className="text-muted-foreground">{r.trigger}</span>
              <span className="text-muted-foreground">
                {r.companies_ok}✓ {r.companies_failed > 0 && `${r.companies_failed}✗`}
              </span>
              <span className="text-muted-foreground">{r.jobs_new} new</span>
              <span className="text-primary">{r.jobs_matched} matched</span>
              <span
                className={`ml-auto ${
                  r.status === "completed" ? "text-primary" : "text-warning"
                }`}
              >
                {r.status}
              </span>
            </button>
            {open === r.id && detail && (
              <div className="border-t border-border px-4 py-3">
                {detail.companies.map((c, i) => (
                  <div key={i} className="flex flex-wrap gap-x-4 py-1 text-[13px]">
                    <span className="w-24 font-medium">{c.company}</span>
                    <span
                      className={c.status === "success" ? "text-primary" : "text-destructive"}
                    >
                      {c.status}
                    </span>
                    <span className="text-muted-foreground">{c.strategy}</span>
                    <span className="text-muted-foreground">
                      {c.jobs_found} found / {c.jobs_new} new
                    </span>
                    {c.duration_ms != null && (
                      <span className="text-muted-foreground">
                        {(c.duration_ms / 1000).toFixed(1)}s
                      </span>
                    )}
                    {c.error && (
                      <span className="w-full truncate text-destructive/80">{c.error}</span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
        {runs.length === 0 && (
          <div className="rounded-[10px] border border-border bg-card p-8 text-center text-sm text-muted-foreground">
            No scan runs yet — hit “Scan now” on Home.
          </div>
        )}
      </div>
    </div>
  );
}
