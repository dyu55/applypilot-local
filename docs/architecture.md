# Architecture

ApplyPilot Local is one installable Python package. Its static HTML/CSS/JavaScript interface
is bundled in the wheel. FastAPI serves the UI and API on loopback; no Node.js runtime or
separate database service is required for users.

## Components

- `domain.py`: validated profiles, scoped facts, screening rules, jobs, and statuses.
- `storage.py`: profile namespaces, SQLite transactions, canonical identities, history, questions.
- `screening.py`: deterministic screening and qualitative fit with explicit reasons.
- `sources.py`: bounded public downloads, source adapters, CSV and structured URL imports.
- `materials.py`: text extraction, resume routing, source-preserving ordering, PDF validation.
- `model.py`: optional bounded ordering calls, complete-permutation validation, no generated facts.
- `service.py`: operations shared by the CLI and HTTP interface.
- `web.py` and `static/`: local HTTP interface, request controls, UI, downloads.
- `cli.py`: initialization, demo, diagnostics, collection, import, export, serving, material generation.

## Data layout

```text
application-data-root/
  profiles/
    profile-id/
      profile.json
      workspace.sqlite3
      materials/
        immutable-run-id/
          resume.pdf
          resume.md
          source-resume.txt
          preparation.md
          manifest.json
```

SQLite schema version 1 contains jobs, resume source texts, events, answers, questions, and
collection runs. Each operation opens and closes its own connection. Status and history
writes share a transaction. Profile files use an atomic rename. Materials are rendered in
staging, checked for missing substantive text, then renamed to an immutable run directory.
The job references a material only after publication. Incomplete stages are removed on failure.

Jobs use source-qualified identifiers and canonical URLs. Tracking parameters are removed,
but meaningful requisition query parameters are retained. Similar titles alone never cause
deduplication. Reimporting a known job does not erase user status or prior evidence.

## Three independent states

1. Posting availability: `open`, `expired`, or `unknown`, with source evidence.
2. Materials: absent or a verified, versioned manifest.
3. Application: `Pending`, `Needs user`, `Blocked`, `Skipped`, or `Submitted`.

Rule changes recalculate assessments. A status explicitly chosen by a user survives those
changes; the updated assessment is still visible. Preparing materials never creates an
application event. A manual submission confirmation is explicitly labelled `user_reported`.

## Trust boundaries

Public pages are data, not instructions. UI content is escaped. JSON APIs need a per-process
request token and matching origin. Host checks defend against unexpected hostnames. Public
source imports reject private-network destinations, validate each redirect, and bound downloads.
Model calls do not follow redirects carrying credentials and can return only source bullet indices.

This is a single-user desktop service. It is not designed to be exposed on a public interface,
used as a shared multi-user server, or protected by the request token against a compromised OS.
