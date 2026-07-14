const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "content-type": "application/json", ...init?.headers },
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {}
    throw new Error(detail);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export type Company = {
  id: string; name: string; careers_url: string | null; status: string;
  health: string; preferred_strategy: string | null;
  last_success_at: string | null; jobs_total: number; jobs_matched: number;
};
export type JobItem = {
  id: string; company: string; title: string; location: string | null;
  apply_url: string; posted_at: string | null; first_seen_at: string;
  status: string; match_score: number | null;
  match_reasons: { term: string; kind: string; similarity?: number }[];
  email_sent_at: string | null; user_state: string; source_strategy: string;
};
export type Keyword = { id: string; term: string; kind: string; enabled: boolean };
export type ScheduleSlot = { id: string; hour: number; minute: number; enabled: boolean };
export type Overview = {
  companies_active: number; companies_failing: number; jobs_found_today: number;
  jobs_matched_today: number; jobs_emailed_total: number;
  last_scan: { at: string; status: string } | null; next_scan_at: string | null;
};

export const healthColor: Record<string, string> = {
  healthy: "text-primary", degraded: "text-warning",
  failing: "text-destructive", unknown: "text-muted-foreground",
};
