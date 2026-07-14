"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type JobItem } from "@/lib/api";

const TABS = [
  { key: "matched", label: "Matched" },
  { key: "all", label: "All" },
  { key: "bookmarked", label: "Bookmarked 🔖" },
  { key: "applied", label: "Applied ✓" },
  { key: "excluded", label: "Excluded" },
];

export default function JobsPage() {
  const [tab, setTab] = useState("matched");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<{ items: JobItem[]; total: number } | null>(null);

  const load = useCallback(() => {
    const params = new URLSearchParams({ page: String(page), page_size: "25" });
    if (tab === "bookmarked" || tab === "applied") {
      params.set("status", "all");
      params.set("user_state", tab);
    } else {
      params.set("status", tab);
    }
    if (search) params.set("search", search);
    api<{ items: JobItem[]; total: number }>(`/jobs?${params}`).then(setData);
  }, [tab, search, page]);

  useEffect(() => {
    const t = setTimeout(load, 250);
    return () => clearTimeout(t);
  }, [load]);

  async function setState(job: JobItem, state: string) {
    const next = job.user_state === state ? "none" : state;
    await api(`/jobs/${job.id}/state`, {
      method: "POST",
      body: JSON.stringify({ user_state: next }),
    });
    load();
  }

  return (
    <div className="space-y-4">
      <h1 className="text-[22px] font-semibold tracking-tight">Jobs Found</h1>
      <div className="flex flex-wrap items-center gap-2">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => { setTab(t.key); setPage(1); }}
            className={`rounded-full px-3 py-1.5 text-[13px] ${
              tab === t.key
                ? "bg-primary/15 text-primary"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {t.label}
          </button>
        ))}
        <input
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          placeholder="Search titles…"
          className="ml-auto w-56 rounded-lg border border-border bg-card px-3 py-1.5 text-sm outline-none focus:ring-2 focus:ring-ring"
        />
      </div>
      <div className="text-[13px] text-muted-foreground">{data?.total ?? "…"} jobs</div>
      <div className="space-y-3">
        {data?.items.map((job) => (
          <div
            key={job.id}
            className={`rounded-[10px] border border-border bg-card p-4 ${
              job.status === "matched" ? "border-l-2 border-l-primary" : ""
            }`}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <a
                  href={job.apply_url}
                  target="_blank"
                  rel="noreferrer"
                  className="font-semibold hover:text-primary"
                >
                  {job.company} — {job.title}
                </a>
                <div className="mt-1 text-[13px] text-muted-foreground">
                  {job.location ?? "location n/a"}
                  {job.posted_at && <> · posted {job.posted_at}</>}
                  {job.email_sent_at && <> · ✉ emailed</>}
                  <> · via {job.source_strategy}</>
                </div>
              </div>
              {job.match_score != null && (
                <span className="rounded-full bg-primary/10 px-2.5 py-1 text-[12px] font-semibold tabular-nums text-primary">
                  {job.match_score.toFixed(2)}
                </span>
              )}
            </div>
            {job.match_reasons.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {job.match_reasons.slice(0, 5).map((r, i) => (
                  <span
                    key={i}
                    className={`rounded-full border px-2 py-0.5 text-[11px] ${
                      r.kind === "exclude"
                        ? "border-destructive/40 text-destructive"
                        : "border-border text-muted-foreground"
                    }`}
                  >
                    {r.term}
                    {r.similarity != null && ` ${r.similarity}`}
                  </span>
                ))}
              </div>
            )}
            <div className="mt-3 flex gap-2">
              <a
                href={job.apply_url}
                target="_blank"
                rel="noreferrer"
                className="rounded-lg bg-primary px-3 py-1.5 text-[13px] font-semibold text-primary-foreground hover:opacity-90"
              >
                Apply ↗
              </a>
              <button
                onClick={() => setState(job, "applied")}
                className={`rounded-lg border border-border px-3 py-1.5 text-[13px] hover:bg-border/40 ${
                  job.user_state === "applied" ? "text-primary" : "text-muted-foreground"
                }`}
              >
                {job.user_state === "applied" ? "✓ Applied" : "Mark applied"}
              </button>
              <button
                onClick={() => setState(job, "bookmarked")}
                className={`rounded-lg border border-border px-3 py-1.5 text-[13px] hover:bg-border/40 ${
                  job.user_state === "bookmarked" ? "text-primary" : "text-muted-foreground"
                }`}
              >
                {job.user_state === "bookmarked" ? "🔖 Bookmarked" : "Bookmark"}
              </button>
            </div>
          </div>
        ))}
        {data && data.items.length === 0 && (
          <div className="rounded-[10px] border border-border bg-card p-8 text-center text-sm text-muted-foreground">
            No jobs here yet.
          </div>
        )}
      </div>
      {data && data.total > 25 && (
        <div className="flex items-center gap-3 text-sm">
          <button
            disabled={page <= 1}
            onClick={() => setPage(page - 1)}
            className="rounded-lg border border-border px-3 py-1.5 disabled:opacity-40"
          >
            ← Prev
          </button>
          <span className="text-muted-foreground">
            page {page} / {Math.ceil(data.total / 25)}
          </span>
          <button
            disabled={page >= Math.ceil(data.total / 25)}
            onClick={() => setPage(page + 1)}
            className="rounded-lg border border-border px-3 py-1.5 disabled:opacity-40"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
