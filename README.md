# ApplyPilot Local

An agent skill that turns a conversation, a resume, and job preferences into a dated folder of application materials. Use the same skill with Codex or Claude Code.

Tell your agent:

> Use ApplyPilot Local. Here is my resume. I am looking for product design roles in my region, including remote work. Find five suitable openings, prepare the materials, and save today's batch. I will apply myself or hand the folder to Muse.

The agent collects missing details, searches with its own tools, screens postings, prepares supported resume variants, and saves the results locally. The skill supplies instructions and small file/PDF helpers. There is no web application, application command to install, separate model service, or mandatory API key.

## Install once

Download the release ZIP or clone this repository. Copy the complete `skills/applypilot-local` folder into your agent's skill directory, preserving its scripts and references. If downloading the release ZIP, it already contains that folder. Do not overwrite an existing installation without reviewing your changes.

| Agent | Personal skill directory | Project skill directory | Explicit invocation |
| --- | --- | --- | --- |
| Codex | `~/.agents/skills/applypilot-local/` | `.agents/skills/applypilot-local/` | `$applypilot-local` |
| Claude Code | `~/.claude/skills/applypilot-local/` | `.claude/skills/applypilot-local/` | `/applypilot-local` |

These paths and invocation forms follow the [Codex skill documentation](https://developers.openai.com/codex/skills/) and [Claude Code skill documentation](https://code.claude.com/docs/en/skills). On Windows, `~` means your user home folder. If a host does not discover the skill, restart or use its skill selector; you can also ask the agent to read the installed SKILL.md directly. Follow managed host settings where applicable.

You can ask your agent to install the folder for you:

> Install the applypilot-local skill from https://github.com/dyu55/applypilot-local, using the skills/applypilot-local folder. Check for an existing installation first. Keep my personal data outside the repository and skill folder.

## Use through conversation

Provide a resume and target roles, locations, level, and preferences. The agent asks only for missing information that affects the current task, then maintains a private profile, scoped answer bank, pending questions, and application history. It can also prepare drafts from supplied job descriptions when live browsing is unavailable.

The agent uses the host's search/browser/document tools. Python 3.11+ is needed only for bundled helpers; PDF verification/rendering uses pypdf and ReportLab. The agent can install those dependencies in an isolated environment or use equivalent available document tools. If a check is unavailable, the result stays a draft with a reason.

```text
applypilot-workspace/
  state/
  batches/
    YYYY-MM-DD/
      latest.json
      <run-id>/
        APPLY_ORDER.md
        applications.csv
        manifest.json
        HANDOFF.md
        handoff.json
        jobs/<job-id>/
          resume.md
          resume.pdf
          job_description.md
          notes.md
          fact_map.json
```

Same-day reruns preserve earlier runs. The date folder's `latest.json` points to the newest complete batch. All candidate files stay in the private workspace you choose.

## What v0.1 delivers

- Conversation-led intake and persistent candidate state.
- Host-tool job research, evidence-based screening, and duplicate checks.
- Truthful resume tailoring, source references, and explicit PDF review checks.
- Immutable dated batches with application order, hashes, source outcomes, and shortfalls.
- Local handoff files for manual application or another agent such as Muse.

Preparation never counts as submission. The handoff does not send files, invoke Muse, or authorize applications. This release has no Muse API integration. It does not guarantee access to protected job sites or control how a host agent reasons. Review factual content before applying.

All maintained instructions, templates, examples, and code are English. Actual user names and source facts are preserved faithfully in private outputs.

## Validation and releases

GitHub Actions checks skill structure/references, English-only repository content, lint/formatting, and helper behavior on Linux, macOS, and Windows with Python 3.11 and 3.13. It builds a skill ZIP and tests an extracted copy outside the checkout. Release publication requires successful CI for the exact commit.

Tests validate deterministic helpers and fictional fixtures. They do not prove end-to-end execution in every Codex/Claude Code version, live job-site access, truthful agent judgment, or Muse compatibility. See [behavioral scenarios](evals/scenarios.json) for host-level acceptance checks and [CONTRIBUTING.md](CONTRIBUTING.md) for development.

[Skill entry point](skills/applypilot-local/SKILL.md) · [MIT license](LICENSE)
