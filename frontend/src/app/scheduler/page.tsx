"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type ScheduleSlot } from "@/lib/api";

export default function SchedulerPage() {
  const [data, setData] = useState<{ items: ScheduleSlot[]; next_run_at: string | null } | null>(
    null
  );
  const [hour, setHour] = useState(9);
  const [minute, setMinute] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api<{ items: ScheduleSlot[]; next_run_at: string | null }>("/schedules").then(setData);
  }, []);
  useEffect(load, [load]);

  async function add() {
    setError(null);
    try {
      await api("/schedules", { method: "POST", body: JSON.stringify({ hour, minute }) });
      load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function remove(id: string) {
    await api(`/schedules/${id}`, { method: "DELETE" });
    load();
  }

  return (
    <div className="max-w-xl space-y-4">
      <h1 className="text-[22px] font-semibold tracking-tight">Scheduler</h1>
      {error && <div className="text-sm text-destructive">{error}</div>}
      <div className="rounded-[10px] border border-border bg-card p-5">
        <div className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          Scan times (Asia/Kolkata)
        </div>
        <div className="mt-3 space-y-2">
          {data?.items.map((s) => (
            <div
              key={s.id}
              className="flex items-center justify-between rounded-lg border border-border px-4 py-2.5"
            >
              <span className="font-semibold tabular-nums">
                {String(s.hour).padStart(2, "0")}:{String(s.minute).padStart(2, "0")}
              </span>
              <button
                onClick={() => remove(s.id)}
                className="text-sm text-muted-foreground hover:text-destructive"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
        <div className="mt-4 flex items-center gap-2">
          <select
            value={hour}
            onChange={(e) => setHour(+e.target.value)}
            className="rounded-lg border border-border bg-background px-2 py-1.5 text-sm"
          >
            {Array.from({ length: 24 }, (_, h) => (
              <option key={h} value={h}>{String(h).padStart(2, "0")}</option>
            ))}
          </select>
          :
          <select
            value={minute}
            onChange={(e) => setMinute(+e.target.value)}
            className="rounded-lg border border-border bg-background px-2 py-1.5 text-sm"
          >
            {[0, 15, 30, 45].map((m) => (
              <option key={m} value={m}>{String(m).padStart(2, "0")}</option>
            ))}
          </select>
          <button
            onClick={add}
            className="rounded-lg bg-primary px-4 py-1.5 text-sm font-semibold text-primary-foreground"
          >
            + Add time
          </button>
        </div>
      </div>
      <div className="rounded-[10px] border border-border bg-card p-5 text-sm">
        <span className="text-muted-foreground">Next scheduled scan: </span>
        <span className="font-semibold">
          {data?.next_run_at
            ? new Date(data.next_run_at).toLocaleString("en-IN", {
                weekday: "short", hour: "2-digit", minute: "2-digit",
              })
            : "—"}
        </span>
        <span className="ml-2 text-primary">● scheduler running</span>
      </div>
    </div>
  );
}
