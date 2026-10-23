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

Rank selected jobs by evidence of fit, preference match, freshness when known, and application feasibility. Explain the basis in plain English. Keyword overlap alone is not evidence of experience or eligibility. Never pad a requested quota with expired jobs, duplicates, incomplete descriptions, or fabricated listings.

Bound research to the user's scope. Retry transient source failures at most twice, then report them and continue with independent sources. Respect site controls; do not bypass CAPTCHA or anti-bot challenges. If the target cannot be met within the available scope/tools, publish the useful partial batch with the shortfall and source outcomes.

Source reports use `ok`, `partial`, `blocked`, or `not_checked`. Record the actual query/source, timestamp, and a concise limitation. Material readiness and source health remain separate: enough verified materials can exist even when another source was blocked.
