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

Create `batch.json` in a private staging folder. This minimal fictional example demonstrates an incomplete offline batch:

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

`APPLY_ORDER.md` and `handoff.json` contain only ready jobs. `applications.csv` and the manifest include drafts, unresolved jobs, and exclusions. All handoffs start with `submission_authorized: false` and zero verified submissions. A Muse recipient can read the local files under separately supplied instructions; this version does not implement a Muse protocol or integration.

After publication, validate hashes and return the exact run path and latest pointer. Later application attempts go into private state, not edits to the immutable batch. If publication fails, keep staging for diagnosis and report the failure. A stale `.publish.lock` requires inspecting the active writer before removal; never delete another running publication's lock.
