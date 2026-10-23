# Candidate intake and persistent state

The agent creates and maintains these local files. Start with the resume and preferences already supplied in the conversation or identified workspace; do not ask the user to repeat them.

Before the first search, establish:

- A source resume or enough verified experience to prepare one.
- Target role families and level, preferred locations, remote/hybrid/on-site constraints.
- The desired batch size and search scope. If unspecified, start with five leads and explain that assumption.
- A private output location. Suggest `applypilot-workspace` in a user-writable documents directory outside Git repositories; use the host's actual paths.

Ask about compensation, currency and pay period, authorization, sponsorship, relocation, or availability only when needed for screening or answers. Unknown is a valid value. Do not infer these facts from name, location, nationality, or resume history. A salary threshold without currency and period is incomplete. Do not turn a preference into a legal eligibility statement.

Use a private state layout such as:

```text
state/
  profile.json
  rules.md
  resumes/
  answers.json
  questions.json
  application_attempts.jsonl
batches/
  YYYY-MM-DD/
    latest.json
    <run-id>/
```

Store profile values with provenance, for example:

```json
{
  "schema_version": 1,
  "target_roles": ["Product Designer"],
  "locations": ["Remote"],
  "time_zone": "UTC",
  "facts": {
    "requires_sponsorship": {
      "value": null,
      "source": null,
      "scope": null,
      "confirmed_at": null
    }
  }
}
```

An answer record includes `question`, `answer`, `scope`, `source`, `source_reference`, and `confirmed_at`. Use `user_confirmed` only for explicit user answers; use `resume_based_draft` for agent narration supported by a resume. Keep `confirmed_at` null for drafts. Normalize question wording for deduplication, but retain distinctions such as country, employer, time period, and authorization type. A newer explicit answer supersedes an older equivalent answer in the same scope.

Question records include `question`, `scope`, `job_ids`, `reason`, and `status` (`pending` or `resolved`). Link repeated questions to the existing record. A generated draft does not resolve a question requiring a confirmed fact.

Read prior application attempts and published batch manifests before selecting jobs. Match requisition ID within employer/source when available, otherwise compare normalized URLs and company/title/location. Strip tracking parameters only; preserve parameters that identify the posting. Avoid duplicate applications across different aggregators.

Keep resumes, contacts, answer banks, account details, cookies, credentials, and application history out of the skill directory, examples, release archives, and Git history. Do not require passwords, OTPs, or API keys to prepare a batch.
