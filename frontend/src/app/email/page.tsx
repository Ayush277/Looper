"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Settings = {
  notification_email: string | null;
  email_enabled: boolean;
  resend_key_present: boolean;
};

export default function EmailPage() {
  const [s, setS] = useState<Settings | null>(null);
  const [email, setEmail] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api<Settings>("/settings").then((d) => {
      setS(d);
      setEmail(d.notification_email ?? "");
    });
  }, []);

  async function save(patch: Partial<Settings>) {
    const d = await api<Settings>("/settings", { method: "PATCH", body: JSON.stringify(patch) });
    setS(d);
    setSaved(true);
    setTimeout(() => setSaved(false), 1500);
  }

  if (!s) return null;
  return (
    <div className="max-w-xl space-y-4">
      <h1 className="text-[22px] font-semibold tracking-tight">Email Settings</h1>
      <div className="space-y-4 rounded-[10px] border border-border bg-card p-5">
        <label className="flex items-center justify-between text-sm">
          <span>Email digest</span>
          <button
            onClick={() => save({ email_enabled: !s.email_enabled })}
            className={`h-6 w-11 rounded-full transition-colors ${
              s.email_enabled ? "bg-primary" : "bg-border"
            }`}
          >
            <span
              className={`block h-5 w-5 rounded-full bg-background transition-transform ${
                s.email_enabled ? "translate-x-5" : "translate-x-0.5"
              }`}
            />
          </button>
        </label>
        <div>
          <div className="mb-1 text-sm text-muted-foreground">Recipient</div>
          <div className="flex gap-2">
            <input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
            />
            <button
              onClick={() => save({ notification_email: email })}
              className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground"
            >
              {saved ? "✓ Saved" : "Save"}
            </button>
          </div>
        </div>
        <div className="rounded-lg border border-border bg-background px-4 py-3 text-[13px] text-muted-foreground">
          Provider: Resend —{" "}
          {s.resend_key_present ? (
            <span className="text-primary">✓ key configured</span>
          ) : (
            <span className="text-warning">
              no RESEND_API_KEY in .env → digests print to the API console (dev mode)
            </span>
          )}
        </div>
        <div className="text-[13px] text-muted-foreground">
          Future channels: Telegram · Discord · Slack · Push (post-v1 roadmap)
        </div>
      </div>
    </div>
  );
}
