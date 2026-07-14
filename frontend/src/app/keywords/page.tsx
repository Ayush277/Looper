"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type Keyword } from "@/lib/api";

const COLS = [
  { kind: "include", title: "Include (match)", icon: "⦿", hint: "Semantic — variants match" },
  { kind: "requirement", title: "Requirements (boost)", icon: "◆", hint: "Eligibility & location" },
  { kind: "exclude", title: "Exclude (block)", icon: "⊘", hint: "Hard blocks, never emailed" },
];

export default function KeywordsPage() {
  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [drafts, setDrafts] = useState<Record<string, string>>({});

  const load = useCallback(() => {
    api<Keyword[]>("/keywords").then(setKeywords);
  }, []);
  useEffect(load, [load]);

  async function add(kind: string) {
    const term = drafts[kind]?.trim();
    if (!term) return;
    await api("/keywords", { method: "POST", body: JSON.stringify({ term, kind }) });
    setDrafts({ ...drafts, [kind]: "" });
    load();
  }

  async function remove(id: string) {
    await api(`/keywords/${id}`, { method: "DELETE" });
    load();
  }

  return (
    <div className="space-y-4">
      <h1 className="text-[22px] font-semibold tracking-tight">Keywords</h1>
      <p className="text-sm text-muted-foreground">
        Matching is semantic: “SDE Intern” matches “Software Engineer Internship”. Changes apply
        from the next scan.
      </p>
      <div className="grid gap-4 lg:grid-cols-3">
        {COLS.map((col) => (
          <div key={col.kind} className="rounded-[10px] border border-border bg-card p-4">
            <div className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              {col.title}
            </div>
            <div className="mb-3 mt-0.5 text-[12px] text-muted-foreground/70">{col.hint}</div>
            <div className="mb-3 flex gap-2">
              <input
                value={drafts[col.kind] ?? ""}
                onChange={(e) => setDrafts({ ...drafts, [col.kind]: e.target.value })}
                onKeyDown={(e) => e.key === "Enter" && add(col.kind)}
                placeholder="Add keyword…"
                className="flex-1 rounded-lg border border-border bg-background px-3 py-1.5 text-sm outline-none focus:ring-2 focus:ring-ring"
              />
              <button
                onClick={() => add(col.kind)}
                className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-primary-foreground"
              >
                +
              </button>
            </div>
            <div className="space-y-1.5">
              {keywords
                .filter((k) => k.kind === col.kind)
                .map((k) => (
                  <div
                    key={k.id}
                    className="group flex items-center justify-between rounded-lg px-2 py-1.5 text-sm hover:bg-border/30"
                  >
                    <span>
                      <span
                        className={
                          col.kind === "exclude" ? "text-destructive/70" : "text-primary/80"
                        }
                      >
                        {col.icon}
                      </span>{" "}
                      {k.term}
                    </span>
                    <button
                      onClick={() => remove(k.id)}
                      className="text-muted-foreground opacity-0 hover:text-destructive group-hover:opacity-100"
                    >
                      ✕
                    </button>
                  </div>
                ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
