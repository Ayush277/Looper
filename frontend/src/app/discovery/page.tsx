export default function DiscoveryPage() {
  return (
    <div className="max-w-2xl space-y-4">
      <h1 className="text-[22px] font-semibold tracking-tight">Discovery</h1>
      <div className="rounded-[10px] border border-border bg-card p-6">
        <div className="text-sm leading-6 text-muted-foreground">
          <p className="mb-3 text-foreground">
            Global discovery finds matching jobs <em>beyond</em> your tracked companies — by
            keyword + country, across the whole indexed job market.
          </p>
          <p className="mb-3">
            It runs on job-aggregator APIs and ATS board sweeps, and needs one free API key to
            activate:
          </p>
          <ul className="mb-3 list-inside list-disc space-y-1">
            <li>
              <span className="text-foreground">JSearch</span> (RapidAPI) — recommended, also
              powers the search-engine scraping strategy
            </li>
            <li><span className="text-foreground">Adzuna</span> — official API, good India coverage</li>
          </ul>
          <p>
            Add <code className="rounded bg-border/40 px-1.5 py-0.5 text-[12px]">JSEARCH_API_KEY=…</code>{" "}
            to <code className="rounded bg-border/40 px-1.5 py-0.5 text-[12px]">.env</code> and
            restart — the saved-query board unlocks here. Design:{" "}
            <span className="text-foreground">docs/15-global-discovery.md</span>
          </p>
        </div>
      </div>
      <div className="rounded-[10px] border border-dashed border-border p-6 text-sm text-muted-foreground">
        Seeded and waiting: <span className="text-foreground">“Software Engineer Intern · India”</span>{" "}
        (Bangalore, Hyderabad, Pune, Remote)
      </div>
    </div>
  );
}
