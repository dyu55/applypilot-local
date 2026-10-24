# Customizable first-run preferences

Offer every topic below through conversation. Reuse existing explicit answers and allow "no preference" or "unknown" where appropriate. Invite additional constraints; this checklist is not an exhaustive limit on customization.

| Group | Ask about |
| --- | --- |
| roles | Role families, titles, responsibilities, industries, exclusions, desired direction mix |
| levels | Seniority, years-of-experience range, over-level roles, management versus individual contributor |
| employers | Preferred/excluded companies, employer types, industries, company size, agencies/consultancies |
| locations | Countries, regions/cities, commute radius, local priority, relocation and remote-location restrictions |
| work_arrangement | Remote, hybrid/on-site, office days, time-zone overlap, work hours |
| skills | Preferred/required technologies, transferable skills, languages, skills to avoid |
| compensation | Threshold/range, currency and pay period, unknown salary handling, level-specific salary rules |
| employment | Permanent/contract/part-time, duration, shifts, travel, other working conditions |
| eligibility | Known work eligibility and sponsorship scope; keep unknown facts unknown |
| freshness | Posting age and unknown-date handling; how recently availability must be checked |
| materials | Source resume routing, tailoring depth, output language/formats, PDF length/layout preferences, file naming |
| delivery | Private output folder, time zone, reporting preferences, run-day preferences |
| other | Anything else that affects selection, ordering, materials, or output |

Also ask for ready-job target count, optional role-family minimums, ranking precedence, source/query groups, concurrency/retry/time limits, and whether fallback is enabled. A run-day preference is not a scheduled task: create no scheduler or notifications without a separate request to enable them.

Use this private strategy shape. The values below are fictional demonstration choices, never defaults to impose on users. The user's answers can be text, lists, or structured objects. The helper validates recorded setup, not whether an agent truthfully represented the conversation.

```json
{
  "setup_complete": true,
  "confirmed_at": "2026-10-23T09:00:00+00:00",
  "target_count": 5,
  "preferences": {
    "roles": {"status": "answered", "value": ["Product Designer"]},
    "levels": {"status": "answered", "value": ["Intermediate"]},
    "employers": {"status": "no_preference"},
    "locations": {"status": "no_preference"},
    "work_arrangement": {"status": "answered", "value": ["Remote"]},
    "skills": {"status": "no_preference"},
    "compensation": {"status": "unknown"},
    "employment": {"status": "no_preference"},
    "eligibility": {"status": "unknown"},
    "freshness": {"status": "no_preference"},
    "materials": {"status": "answered", "value": "Use my design resume; prepare Markdown and PDF."},
    "delivery": {"status": "answered", "value": "Private workspace; UTC; report every run."},
    "other": {"status": "no_preference"}
  },
  "role_quotas": {},
  "ranking": {"criteria": ["levels", "roles", "freshness"]},
  "collection": {
    "sources": ["employer_boards", "host_job_search"],
    "mode": "parallel",
    "max_parallel": 3,
    "timeout_seconds": 120,
    "retry_limit": 2
  },
  "fallback": {"enabled": false, "allowed_relaxations": []}
}
```

Response states are `answered`, `no_preference`, or `unknown`. Missing a preference group means setup is incomplete. An answered group needs a value. The agent can maintain additional preference groups without changing the skill. Store personal eligibility facts separately with provenance; a preference response saying eligibility is unknown is not a confirmed eligibility answer.

`role_quotas` maps role-family names to minimum counts; their total cannot exceed the target. Ask whether unused capacity can transfer between directions and save the answer in the roles preference. Hard minimum shortfalls remain visible in the daily report. Use an empty object only after the user chooses no direction quotas.

`ranking.criteria` is ordered by importance. Apply hard constraints and duplicate checks first, then compare eligible jobs using these priorities and their recorded preference values. Document tradeoffs. Use a stable job ID to break remaining ties, never source completion time. If the user explicitly wants discovery order, record `["discovery_order"]` and freeze that order.

Fallback is optional. If enabled, `allowed_relaxations` lists specific user-approved changes, such as a wider posting-age window or an additional role family. Mark affected jobs `selection_tier: "fallback"` and record matching `fallback_rules_used`. Never relax factual truth, required eligibility, explicit hard exclusions, or quality checks. If disabled or exhausted, report the shortfall instead of broadening criteria.

The skill does not contain a universal ranking formula. The host agent applies the confirmed strategy and records ranking reasons; helpers enforce the frozen ranks, fallback opt-in, report counts, and publication checks.
