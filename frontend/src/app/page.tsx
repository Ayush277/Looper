"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type Overview } from "@/lib/api";

function fmtTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-IN", {
    day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
  });
}

export default function HomePage() {
  const [data, setData] = useState<Overview | null>(null);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    api<Overview>("/stats/overview").then(setData).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 5000);
    return () => clearInterval(t);
  }, [refresh]);

  async function scanNow() {
    setScanning(true);
    setError(null);
    try {
      await api("/scans", { method: "POST" });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setTimeout(() => setScanning(false), 3000);
    }
  }

  const cards = [
    {
      label: "Companies monitored",
      value: data?.companies_active ?? "—",
      sub: data && data.companies_failing > 0
        ? `⚠ ${data.companies_failing} failing`
        : "all healthy",
      warn: !!data && data.companies_failing > 0,
    },
    {
      label: "Jobs found today",
      value: data?.jobs_found_today ?? "—",
      sub: `${data?.jobs_matched_today ?? 0} matched`,
    },
    {
      label: "Jobs emailed",
      value: data?.jobs_emailed_total ?? "—",
      sub: "total, deduplicated",
    },
    {
      label: "Last scan",
      value: data?.last_scan ? fmtTime(data.last_scan.at) : "never",
      sub: data?.last_scan?.status ?? "",
      small: true,
    },
    {
      label: "Next scan",
      value: fmtTime(data?.next_scan_at),
      sub: "scheduled",
      small: true,
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-[22px] font-semibold tracking-tight">Home</h1>
        <button
          onClick={scanNow}
          disabled={scanning}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:opacity-90 disabled:opacity-50"
        >
          {scanning ? "⟳ Scanning…" : "Scan now"}
        </button>
      </div>
      {error && (
        <div className="rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-2 text-sm text-destructive">
          {error}
        </div>
      )}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        {cards.map((c) => (
          <div key={c.label} className="rounded-[10px] border border-border bg-card p-5">
            <div className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              {c.label}
            </div>
            <div className={`mt-2 font-bold tabular-nums ${c.small ? "text-lg" : "text-3xl"}`}>
              {c.value}
            </div>
            <div
              className={`mt-1 text-[13px] ${c.warn ? "text-warning" : "text-muted-foreground"}`}
            >
              {c.sub}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
