"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Settings = {
  timezone: string;
  match_threshold: number;
  requirement_boost: number;
  scan_concurrency: number;
  openai_key_present: boolean;
  resend_key_present: boolean;
};

export default function SettingsPage() {
  const [s, setS] = useState<Settings | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api<Settings>("/settings").then(setS);
  }, []);

  async function save(patch: Record<string, unknown>) {
    const d = await api<Settings>("/settings", { method: "PATCH", body: JSON.stringify(patch) });
    setS(d);
    setSaved(true);
    setTimeout(() => setSaved(false), 1500);
  }

  if (!s) return null;
  return (
    <div className="max-w-xl space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-[22px] font-semibold tracking-tight">Settings</h1>
        {saved && <span className="text-sm text-primary">✓ saved</span>}
      </div>
      <div className="space-y-5 rounded-[10px] border border-border bg-card p-5">
        <div>
          <div className="mb-1 flex justify-between text-sm">
            <span>Match threshold</span>
            <span className="tabular-nums text-muted-foreground">{s.match_threshold}</span>
          </div>
          <input
            type="range" min={0.3} max={0.8} step={0.01}
            defaultValue={s.match_threshold}
            onMouseUp={(e) => save({ match_threshold: +(e.target as HTMLInputElement).value })}
            className="w-full accent-[var(--primary)]"
          />
          <div className="text-[12px] text-muted-foreground">
            Lower = more matches (more noise) · higher = fewer, stricter
          </div>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span>Requirement boost (per hit)</span>
          <input
            type="number" step={0.01} min={0} max={0.2}
            defaultValue={s.requirement_boost}
            onBlur={(e) => save({ requirement_boost: +e.target.value })}
            className="w-24 rounded-lg border border-border bg-background px-2 py-1.5 text-right tabular-nums"
          />
        </div>
        <div className="flex items-center justify-between text-sm">
          <span>Scan concurrency</span>
          <input
            type="number" min={1} max={16}
            defaultValue={s.scan_concurrency}
            onBlur={(e) => save({ scan_concurrency: +e.target.value })}
            className="w-24 rounded-lg border border-border bg-background px-2 py-1.5 text-right tabular-nums"
          />
        </div>
        <div className="flex items-center justify-between text-sm">
          <span>Timezone</span>
          <span className="text-muted-foreground">{s.timezone}</span>
        </div>
      </div>
      <div className="rounded-[10px] border border-border bg-card p-5 text-sm">
        <div className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          Environment keys
        </div>
        <div className="space-y-1 text-muted-foreground">
          <div>
            OpenAI embeddings:{" "}
            {s.openai_key_present ? (
              <span className="text-primary">✓ configured</span>
            ) : (
              <span>absent → local MiniLM model ($0, works offline)</span>
            )}
          </div>
          <div>
            Resend email:{" "}
            {s.resend_key_present ? (
              <span className="text-primary">✓ configured</span>
            ) : (
              <span>absent → console digests (dev)</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
