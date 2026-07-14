"use client";

import { useCallback, useEffect, useState } from "react";
import { api, healthColor, type Company } from "@/lib/api";

export default function CompaniesPage() {
  const [companies, setCompanies] = useState<Company[] | null>(null);
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api<Company[]>("/companies").then(setCompanies).catch((e) => setError(e.message));
  }, []);
  useEffect(load, [load]);

  async function act(id: string, action: string, method = "POST") {
    setError(null);
    try {
      await api(`/companies/${id}${action}`, { method });
      load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function add() {
    setError(null);
    try {
      await api("/companies", {
        method: "POST",
        body: JSON.stringify({ name, careers_url: url || null }),
      });
      setName(""); setUrl(""); setAdding(false);
      load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-[22px] font-semibold tracking-tight">Companies</h1>
        <button
          onClick={() => setAdding(!adding)}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:opacity-90"
        >
          + Add company
        </button>
      </div>
      {error && (
        <div className="rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-2 text-sm text-destructive">
          {error}
        </div>
      )}
      {adding && (
        <div className="flex flex-wrap gap-2 rounded-[10px] border border-border bg-card p-4">
          <input
            value={name} onChange={(e) => setName(e.target.value)} placeholder="Company name*"
            className="w-48 rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
          />
          <input
            value={url} onChange={(e) => setUrl(e.target.value)}
            placeholder="Careers URL (optional — auto-probed)"
            className="flex-1 min-w-64 rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
          />
          <button
            onClick={add} disabled={!name}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground disabled:opacity-50"
          >
            Add
          </button>
        </div>
      )}
      <div className="overflow-x-auto rounded-[10px] border border-border">
        <table className="w-full bg-card text-sm">
          <thead>
            <tr className="border-b border-border text-left text-[11px] uppercase tracking-wide text-muted-foreground">
              <th className="px-4 py-3">Company</th>
              <th className="px-4 py-3">Health</th>
              <th className="px-4 py-3">Last success</th>
              <th className="px-4 py-3">Strategy</th>
              <th className="px-4 py-3">Jobs (matched)</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {companies?.map((c) => (
              <tr key={c.id} className="border-b border-border/60 last:border-0">
                <td className="px-4 py-3 font-medium">{c.name}</td>
                <td className={`px-4 py-3 ${healthColor[c.health]}`}>● {c.health}</td>
                <td className="px-4 py-3 text-muted-foreground">
                  {c.last_success_at
                    ? new Date(c.last_success_at).toLocaleString("en-IN", {
                        day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
                      })
                    : "never"}
                </td>
                <td className="px-4 py-3 text-muted-foreground">
                  {c.preferred_strategy ?? "—"}
                </td>
                <td className="px-4 py-3 tabular-nums">
                  {c.jobs_total} ({c.jobs_matched})
                </td>
                <td className="px-4 py-3">
                  <span
                    className={c.status === "paused" ? "text-warning" : "text-muted-foreground"}
                  >
                    {c.status}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex justify-end gap-1.5">
                    <button
                      onClick={() => act(c.id, "/scan")}
                      className="rounded-md border border-border px-2.5 py-1 text-[12px] text-muted-foreground hover:text-foreground"
                    >
                      Scan
                    </button>
                    <button
                      onClick={() => act(c.id, c.status === "paused" ? "/resume" : "/pause")}
                      className="rounded-md border border-border px-2.5 py-1 text-[12px] text-muted-foreground hover:text-foreground"
                    >
                      {c.status === "paused" ? "Resume" : "Pause"}
                    </button>
                    <button
                      onClick={() => {
                        if (confirm(`Delete ${c.name}? Its job history is kept.`))
                          act(c.id, "", "DELETE");
                      }}
                      className="rounded-md border border-border px-2.5 py-1 text-[12px] text-destructive/80 hover:text-destructive"
                    >
                      ✕
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
