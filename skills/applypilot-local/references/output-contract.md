# Batch files and helper contract

The agent owns file creation and helper execution. Resolve `<skill>` to the folder containing SKILL.md. All paths below are examples, not literal machine paths. Use the user's local date, time zone, and private workspace.

```text
batches/
  2026-10-23/
    latest.json
    20261023T090000-demo/
      batch.json
      manifest.json
      APPLY_ORDER.md
      DAILY_REPORT.md
      daily_report.json
      applications.csv
      HANDOFF.md
      handoff.json
      jobs/
        design-01/
          resume.md
          resume.pdf
          job_description.md
          notes.md
          fact_map.json
```

The run ID is unique, with letters, digits, hyphens, or underscores. Keep all files for a job together. An additional run on the same date gets a new run ID. Published runs are never overwritten; `latest.json` identifies the newest completed run. Do not replace a run while the user is applying from it.

## Agent-generated input

New runs use `schema_version: 2`. Create `batch.json` in private staging and include the confirmed `strategy` object from `state/strategy.json`; its shape is documented in [preferences.md](preferences.md). `requested_count` must match the user's `target_count`. First-run setup must be complete before a new run can publish.

Include `workflow_checks` for `intake`, `deduplication`, `screening`, `ranking`, and `resume_routing`. Each has `status` (`pass`, `warning`, `failed`, or `not_run`) and a concrete `detail`. These are agent attestations, not independently measured by the helper. Do not mark missing historical coverage or an unperformed check as passed.

Include `collection_execution` with actual `mode` (`parallel` or `sequential`), `max_in_flight`, and `detail`. Use the strategy's source IDs in `source_reports`, including blocked/not-checked sources, so missing coverage is visible. For each selected job, include consecutive `rank`, `role_family`, nonempty `ranking_reasons`, `selection_tier` (`primary` or `fallback`), and `fallback_rules_used` (empty for primary jobs). Fallback requires explicit opt-in and matching allowed rules. Selection ranks remain stable even when concurrent collectors finish in a different order.

`batch.json.pending_questions` is a list of nonempty text summaries, such as `["Confirm Canadian sponsorship needs; scope: Canada roles."]`. Keep full question objects with IDs, scope, provenance, and status in `state/questions.json`; do not copy those objects into this batch field. Use an empty list when no questions remain.

The following older `schema_version: 1` example is retained only for reading/migrating legacy drafts. Legacy inputs are accepted with a warning and cannot get a clean v0.2 PASS. Do not use legacy mode to bypass first-run setup for a new user:

```json
{
  "schema_version": 1,
  "date": "2026-10-23",
  "run_id": "20261023T090000-demo",
  "created_at": "2026-10-23T09:00:00+00:00",
  "time_zone": "UTC",
  "requested_count": 1,
  "source_reports": [
    {
      "source": "User-supplied description",
      "outcome": "not_checked",
      "checked_at": "2026-10-23T09:00:00+00:00",
      "detail": "Offline preparation; no live availability check."
    }
  ],
  "pending_questions": [],
  "jobs": [
    {
      "id": "design-01",
      "company": "Example Studio",
      "title": "Product Designer",
      "location": "Remote",
      "url": "https://example.com/jobs/design-01",
      "availability": {
        "status": "unknown",
        "checked_at": "2026-10-23T09:00:00+00:00",
        "evidence": "Supplied offline; not checked online."
      },
      "decision": "selected",
      "reasons": ["The supplied description matches the user's design focus."],
      "application_status": "Pending",
      "materials": {
        "status": "draft",
        "reason": "Live availability and PDF review are incomplete.",
        "files": {}
      }
    }
  ]
}
```

Record `requisition_id` when supplied by the source. Other evidence, fit notes, and salary details can be retained in the job record and notes; never invent absent values. The helper checks in-batch URL/requisition duplicates. The agent checks prior batches and application history before selecting jobs.

For a ready job, replace `materials` with:

```json
{
  "status": "ready",
  "source_resume_id": "design-resume-v1",
  "review": {
    "facts_checked": true,
    "pdf_visual_checked": true
  },
  "files": {
    "resume_md": "jobs/design-01/resume.md",
    "resume_pdf": "jobs/design-01/resume.pdf",
    "job_description": "jobs/design-01/job_description.md",
    "notes": "jobs/design-01/notes.md",
    "fact_map": "jobs/design-01/fact_map.json"
  }
}
```

Only set review flags after performing the reviews in materials.md. Ready jobs must be selected and have evidence of open availability. `draft` and `missing` require a reason. A `needs_user` decision maps to `Needs user`; a `skipped` decision maps to `Skipped`. Selected preparation stays `Pending`. This helper never creates a submission record.

## Helper calls made by the agent

Use an available Python 3.11+ interpreter. Quote paths with spaces using the host's native argument handling. If PDF dependencies are missing, create a virtual environment outside the skill folder and install `scripts/requirements-pdf.txt`; dependency installation follows host permission settings. Core staging checks and publishing draft-only batches use the Python standard library.

```text
python <skill>/scripts/render_resume.py <staging>/jobs/design-01/resume.md <staging>/jobs/design-01/resume.pdf
python <skill>/scripts/validate_batch.py <staging>
python <skill>/scripts/publish_batch.py <staging> <private-workspace>/batches
python <skill>/scripts/validate_batch.py <published-run>
```

These are implementation helpers for the agent, not a user-facing workflow interface. No installed application or executable entry point is needed. The helpers make no network calls. Publishing copies only files declared in batch.json and generates the indexes. Unexpected private files in staging are excluded. Relative paths must stay inside staging; symlinked files are rejected.

`manifest.json` records counts, shortfall, job decisions, source health, PDF text checks, review attestations, and SHA-256 hashes. It labels readiness `ready`, `partial`, or `blocked`. Source failures remain separate. A zero-ready run is blocked, even when the helper exits successfully after preserving useful drafts. Read the returned status; process exit alone is not a readiness claim.

`APPLY_ORDER.md` and `handoff.json` contain only ready jobs; a BLOCKED report leaves their application queues empty until a corrected new run passes review. `applications.csv` and the manifest include drafts, unresolved jobs, and exclusions. All handoffs start with `submission_authorized: false`. A Muse recipient can read the local files under separately supplied instructions; this version does not implement a Muse protocol or integration.

After publication, validate hashes and return the exact run path and latest pointer. This preparation workflow ends at the daily report and optional file handoff; it does not request or write back application outcomes. If publication fails, keep staging for diagnosis and report the failure. A stale `.publish.lock` requires inspecting the active writer before removal; never delete another running publication's lock.

## Required daily preparation report

Publishing always creates `DAILY_REPORT.md` and `daily_report.json`, hashes them with the other files, and returns `report_result` alongside material readiness. Return the report path and summarize it in conversation after every run.

The report separates jobs recorded/selected/ready, resume PDF files prepared, PDF text checks passed, editable resumes, target, and shortfall. It lists each workflow section, its evidence basis, problems, source coverage and actual collection mode, quotas, fallback usage, and pending questions. A PDF file prepared as a draft is counted as a prepared file, not as a validated ready application.

- `PASS`: target and role quotas met; all recorded preparation checks passed; no unresolved issues.
- `WARN`: useful ready materials exist, but there are source limitations, omitted/unperformed checks, incomplete selected materials, quota shortfalls, or pending user input.
- `BLOCKED`: zero jobs are ready or a workflow check explicitly failed.

`manifest.status` still describes material availability (`ready`, `partial`, `blocked`). `report_result` describes the whole recorded preparation review; it can be WARN/BLOCKED even when some materials are ready. Do not hide that result behind a successful process exit or a ready PDF count.

Fact review, live source observations, concurrency observations, and page inspection are agent attestations; file checks, counts, and PDF extraction are helper checks. PASS applies to this recorded preparation scope, not submission or a guarantee that the agent's factual judgment is correct. There is no Muse result writeback, receipt collection, or application monitoring stage.
