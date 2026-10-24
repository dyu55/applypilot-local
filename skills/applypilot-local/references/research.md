# Research and screening

Use the host's search/browser/connectors with the user's selected sources. Prefer an employer's official career page or ATS posting when it matches the employer, title, requisition, and location. Do not assume every user is seeking software roles or jobs in a particular country.

For each candidate posting, record:

- Stable job ID, company, title, location, original URL, and requisition ID when present.
- The substantive description, including responsibilities and requirements, with its source URL and retrieval time.
- Posted date, salary range/currency/period, work arrangement, authorization requirements, and required qualifications only when stated.
- Availability (`open`, `unknown`, or `expired`), timestamp, and concrete evidence.
- Screening decision (`selected`, `needs_user`, or `skipped`), reasons, match evidence, and missing qualifications.

`open` requires a matching posting with a usable application entry. Explicit closure wording supports `expired`. Access restrictions, CAPTCHA, timeouts, redirects, a generic HTTP 200, and a cached local description do not prove availability. Treat ambiguous failures as `unknown`. A supplied offline description is sufficient for a draft, with unknown availability.

Apply the user's exclusions, role level, location, compensation, freshness, and authorization constraints. Do not infer salary from benefit amounts or hours, substitute a predicted salary for an advertised salary, or silently convert currencies/pay periods. Unknown required facts route the job to `needs_user`. Hard exclusions route it to `skipped` with a reason. A missing optional preference can remain a documented limitation.

Rank eligible jobs using the user's recorded precedence and preference values. Fit, freshness, and application feasibility are possible criteria, not a fixed ranking order. Explain the basis in plain English. Keyword overlap alone is not evidence of experience or eligibility. Never pad a requested quota with expired jobs, duplicates, incomplete descriptions, or fabricated listings.

Bound research to the user's scope and recorded timeout/retry budget. Report exhausted source failures and continue with independent sources. Respect site controls; do not bypass CAPTCHA or anti-bot challenges. If the target cannot be met within the available scope/tools, publish the useful partial batch with the shortfall and source outcomes.

Source reports use `ok`, `partial`, `blocked`, or `not_checked`. Record the actual query/source, timestamp, and a concise limitation. Material readiness and source health remain separate: enough verified materials can exist even when another source was blocked.

## Parallel collection and deterministic merge

Read the confirmed strategy before collection. Use its chosen source/query groups, mode, concurrency limit, timeout, and retry budget. Sources can be employer boards, search queries, user links, or available connectors; do not hardcode an author's sources. Source priority is configurable and independent of which request finishes first.

In parallel mode, issue independent reads concurrently using available host tools or independent browser tabs. Keep writes to one shared browser tab/session sequential. Parallel mode does not itself request subagents, new accounts, connectors, or paid services. If the host cannot run reads concurrently, continue sequentially within scope and report the limitation; do not claim parallel execution occurred. With only one source, sequential execution is expected.

Keep each source's candidates, timestamps, and errors in separate private staging data. When all sources finish or reach their budgets, merge centrally, normalize IDs/URLs, deduplicate against prior batches, and apply the same hard rules and confirmed ranking strategy to the combined pool. Do not let concurrent collectors overwrite profile/state files or publish competing batches.

Apply configured role quotas, then any explicitly allowed capacity transfers. If there is a shortfall, run a bounded additional collection pass only within the original criteria. Broader fallback runs only when enabled, following the recorded changes and limits. A fallback strategy must not silently become the next run's primary strategy.

Freeze consecutive ranks after merging and screening. Each selected job records `rank`, `role_family`, `ranking_reasons`, `selection_tier` (`primary` or `fallback`), and `fallback_rules_used`. Record these even for selected jobs whose materials remain drafts. Helpers publish ready jobs by frozen rank, not input array order or collection completion time. Subsequent reruns publish a new batch instead of changing the current order.

Include `collection_execution` with actual `mode`, `max_in_flight`, and `detail`. This is an agent observation, not concurrency measured by the publication helper. Each source report must describe what actually ran; preserve failed/partial/not-checked outcomes for the daily report.
