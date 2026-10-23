# ApplyPilot Local

[![CI](https://github.com/dyu55/applypilot-local/actions/workflows/ci.yml/badge.svg)](https://github.com/dyu55/applypilot-local/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-193d35.svg)](LICENSE)

**Your career. Your own direction.**

A private, local-first job search workspace. Bring your resume, define your preferences,
collect opportunities, prepare truthful materials, and keep your next steps in one place.
No cloud account, AI subscription, messaging platform, or Node.js installation is required.
The interface, examples, documentation, and source comments are in English.

## What v0.1 does

- A local web dashboard plus a command-line interface.
- Separate profiles for different people or searches, with configurable roles, skills,
  regions, exclusions, salary units, freshness, and country-scoped sponsorship facts.
- Manual job entry, CSV import, structured job-page URL import, and read-only adapters
  for Greenhouse, Lever, Remote OK, and Adzuna search.
- Persistent deduplication, reasoned screening, honest unknown states, and a status history.
- PDF, DOCX, Markdown, and text resume import; role-specific resume routing.
- Resume PDF generation that reorders existing bullet groups and preserves all source lines.
- Optional model-assisted bullet ordering with a call budget and validated permutations.
- Scoped questions, confirmed reusable answers, CSV / JSON exports, and versioned materials.
- A fictional, completely offline demo with no real applications or external requests.

**This version prepares and tracks applications.** Browser autofill and automated submission
are planned for v0.2. It does not bypass site controls, access your email, or log into job boards.

## Get started

Requires **Python 3.11 or later**. Use a virtual environment to keep dependencies isolated.
Git is needed only for cloning; release archives can be downloaded instead.

```sh
git clone https://github.com/dyu55/applypilot-local.git
cd applypilot-local
python -m venv .venv
```

Activate it on macOS / Linux:

```sh
source .venv/bin/activate
```

Or on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Then install and launch:

```sh
python -m pip install .
applypilot doctor
applypilot serve
```

Open **http://127.0.0.1:8765** if the browser does not open automatically. The service binds
only to your computer's loopback interface. `Ctrl+C` stops it.

Start with **Settings** and **Resumes**, or select **Explore the demo** in an empty workspace.
For a separate demo profile that cannot overwrite your own profile:

```sh
applypilot --profile demo demo
applypilot --profile demo serve
```

The demo is loaded once per empty profile. Every candidate, employer, and vacancy in it
is fictional. Loading it creates no application attempts or submission confirmations.

### Install a release

Download the wheel from [Releases](https://github.com/dyu55/applypilot-local/releases), activate
a virtual environment, and run `python -m pip install /path/to/downloaded.whl` using its
actual filename. Package dependencies are downloaded by pip; no PyPI release of this project
is required. After installation, `applypilot serve` works without this source checkout.

## A typical search

1. Set your target titles, skills, regions, and explicit screening rules.
2. Upload a resume and review the extracted source text. Add separate versions for different roles.
3. Add job details, import a CSV, read a structured job URL, or configure a public source.
4. Review each match and its reasons. Unknown information is displayed for review.
5. Prepare materials and inspect the generated PDF. Original wording and source versions remain available.
6. Apply on the employer's site yourself. Record the outcome and its confirmation reference.
7. Keep unanswered form questions in the answer bank; confirm an answer once within its proper scope.

## Configure sources and models

Sources are disabled until you configure and enable them in **Settings**. Job collection
does not guarantee worldwide coverage. Public feeds can be incomplete or unavailable.

| Source | Setup | Key required | Availability meaning |
| --- | --- | --- | --- |
| Greenhouse | Employer board token | No | Listed on the public board when fetched |
| Lever | Employer board name; `eu` for EU API | No | Listed on the public board when fetched |
| Remote OK | Optional title / tag query | No | Listed on Remote OK; employer restrictions still apply |
| Adzuna | Supported country code and search query | Yes | Search result, employer availability unverified |
| Job URL | Public page with structured `JobPosting` data | No | Unverified unless structured expiry is explicit |
| CSV / manual | Your own posting details | No | Unverified |

Remote OK listings link to the original Remote OK URL and identify Remote OK as the source.
Respect each source's terms, request limits, and attribution requirements. Adzuna may have
account-specific quotas. This application does not represent access as free or unlimited.
See [source configuration](docs/sources.md).

AI is **off by default**. Without it, keyword-based ordering, resume routing, screening,
tracking, and all demo features work normally. For model assistance, configure a
Chat Completions-compatible endpoint and a model name in Settings, then opt in.
Hosted endpoints require HTTPS and an API key in the configured environment variable;
a loopback HTTP endpoint can connect to a separately installed local model server.

Only existing resume bullet groups and a bounded job excerpt are sent to that endpoint.
Provider charges may apply. A remote provider receives that content even though your
workspace is stored locally. Profile facts and the answer bank are not sent by this integration.
The model returns ordering indices, and cannot inject new wording into the resume.
Actual model/provider compatibility must be checked with your endpoint; protocol fixtures
are tested without using anyone's API key. See [privacy and model behavior](docs/privacy.md).

## Your data

The default data directory follows your operating system's application-data convention.
`applypilot init` prints the exact private profile directory. Override it when needed:

```sh
applypilot --data-dir ./private-workspace --profile my-search init
applypilot --data-dir ./private-workspace --profile my-search serve --port 8877
```

Use the same options for every command that should access that workspace. Keep private
directories outside source repositories. `APPLYPILOT_DATA_DIR` can set the root as an alternative.
Profiles use separate SQLite databases, configuration, resume texts, and material directories.
Local data is not encrypted by this application; use your OS's disk encryption and account controls.
There is no telemetry or application-operated cloud sync.

```sh
applypilot --profile my-search import jobs.csv
applypilot --profile my-search collect
applypilot --profile my-search export --format csv
applypilot --profile my-search export --format json
applypilot --profile my-search materials JOB_ID
```

CSV imports require `title`, `company`, and `url`. Optional columns include `description`,
`location`, `source_id`, `salary_min`, `salary_max`, `currency`, `period`, `posted_at`,
`country`, `sponsorship`, and `remote`. Salary periods are `year`, `month`, or `hour`.
Dates use ISO 8601. Exported CSV is intended for review, and is not a full database backup.

## Important boundaries

- `Submitted` requires a confirmation reference. Manual reports are labelled `user_reported`;
  they are not presented as programmatically verified receipts.
- Posting availability, material readiness, and application status are independent.
- Salary currency and period are never silently converted. Unknown facts are not false.
- Target-title matching is phrase-based; it is not a professional qualification assessment.
- Only existing contiguous bullet groups are reordered. Paragraph resumes are preserved;
  v0.1 does not promise generated narratives or invented achievements.
- Imported files are converted to editable text. Original source formatting is not reproduced.
- The bundled PDF font supports Latin scripts. Unsupported characters cause an explicit error,
  rather than an unreadable PDF. Broader font support is planned.
- Question deduplication normalizes case, whitespace, and punctuation within the same scope.
  Semantically different or differently phrased questions require human review.
- Live websites and local model servers change. Adapter fixture tests do not prove every
  employer page or model endpoint works.

## Development and delivery

```sh
python -m pip install --require-hashes -r requirements-dev.lock
python -m pip install --no-deps -e .
ruff check .
ruff format --check .
python scripts/check_repository.py
python -m pytest --cov=applypilot
python -m build
```

The hash-locked development requirements and `uv.lock` are committed. Use `uv lock` and
`uv export --extra dev --extra browser --no-emit-project --format requirements-txt --output-file requirements-dev.lock`
when intentionally updating dependencies.

CI tests Python 3.11 and 3.13 on Linux, macOS, and Windows, checks English-only public
content, and builds / validates wheel and source distributions. A browser smoke test exercises
the local UI. Passing builds upload installable artifacts. The release workflow validates the
version, reruns checks, and publishes versioned assets to GitHub Releases.
See [delivery](docs/delivery.md), [architecture](docs/architecture.md), and [roadmap](docs/roadmap.md).

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md). Use fictional data in tests, demos, issues, and
screenshots. Never commit real resumes, application histories, credentials, or browser sessions.

## License

MIT. See [LICENSE](LICENSE). Dependency licenses remain with their respective authors.
This is an independent project and is not affiliated with the job boards or model providers.

