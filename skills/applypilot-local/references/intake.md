# First-run conversation and persistent state

On first use, proactively lead the user through setup before researching jobs. Read supplied resumes and conversation details first, prefill supported answers, and ask the remaining questions in small conversational groups. The agent writes the files; the user should not have to edit JSON or operate commands.

Read [preferences.md](preferences.md) for the full questionnaire and strategy snapshot. Every listed topic must be offered during first-run setup, including additional constraints the list does not anticipate. An explicit "no preference," "unknown," or "skip this preference" is a recorded answer. Silence is not an answer. Do not silently select a daily quota, country, seniority, employer type, ranking order, or fallback strategy.

Use three manageable rounds, adapting to answers already supplied:

1. Resume, role families and level, location/work arrangement, and desired ready-job count.
2. Employer/industry and skill preferences, compensation, employment conditions, eligibility, and freshness.
3. Ranking precedence, optional direction quotas, sources and collection concurrency, optional fallback, materials/output preferences, local date/time zone, and other constraints.

Explain hard exclusions versus soft preferences. Ask the user to choose the order of competing preferences, such as role level, employer type, region, role family, skills, freshness, and application effort. These are examples, not fixed priorities. Do not universally prioritize banks, software companies, a country, or a technology stack.

Ask explicitly whether fallback is enabled. Until the user opts in, keep it disabled and do not broaden criteria to fill a quota. When enabled, record exactly what may change, the order and limits of changes, and what must remain fixed. Missing user replies do not enable fallback. Unknown compensation/eligibility facts remain unknown and must not be guessed.

Present a concise setup summary and obtain the user's confirmation of any new proposed settings. Reuse explicit answers already given; do not ask for a second approval of an already fully specified strategy. Save `setup_complete: true` with a timestamp only after the listed preference groups have recorded answers. On later runs, load the saved strategy and ask only about missing settings or requested changes.

Keep private state outside the source repository and installed skill folder:

```text
state/
  profile.json
  strategy.json
  resumes/
  answers.json
  questions.json
batches/
  YYYY-MM-DD/
    latest.json
    <run-id>/
```

`profile.json` contains candidate facts with source, scope, and confirmation time. `strategy.json` contains user-chosen search/preparation preferences; do not confuse preferences with legal or personal facts. Preserve original resumes privately with stable IDs. Optional preexisting application history can be read for duplicate avoidance, but this skill does not collect application outcomes or write back Muse results.

An answer record includes `question`, `answer`, `scope`, `source`, `source_reference`, and `confirmed_at`. Use `user_confirmed` only for explicit answers and `resume_based_draft` for agent narration supported by a resume. Keep `confirmed_at` null for drafts. Deduplicate by meaning while preserving country, employer, time period, and authorization scope. New explicit answers supersede equivalent older answers within the same scope.

Unresolved questions include `question`, `scope`, `job_ids`, `reason`, and `status` (`pending` or `resolved`). Link repeated questions to the existing record. A generated draft does not resolve a missing factual answer. Behavioral answers can directly adapt verified resume experience; ask only when an essential event, action, or result is absent.

Before selecting jobs, read prior batch manifests and any history the user has already supplied. Match requisition within employer/source, otherwise normalized URLs with company/title/location as supporting evidence. Preserve posting-identifying query parameters. Note when historical coverage is incomplete.

Keep resumes, contacts, answers, account details, cookies, credentials, and private history out of the skill, examples, release archives, and Git history. No passwords, OTPs, or API keys are required for preparation.
