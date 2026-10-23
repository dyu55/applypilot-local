# Roadmap

## v0.1 - Independent local workflow

- Local dashboard, CLI, separate profiles, and explicit configuration.
- Fictional offline demo and environment diagnostics.
- Public source adapters, search-provider integration, CSV / URL / manual imports.
- Persistent identities, screening reasons, and explicit unknown states.
- Resume import and routing, source-preserving ordering, verified PDF output.
- Scoped answers, unresolved questions, evidence-backed manual status, exports.
- Cross-platform CI, package smoke tests, GitHub release assets, English documentation.

The release does not require a particular AI agent or messaging platform. It is implemented
as a clean standalone package; no private applicant workspace or its Git history is imported.

## v0.2 - Browser-assisted applications

- A visible browser session intentionally started by the user.
- One ATS integration first, tested against a local simulated employer flow.
- Known-field filling, upload validation, progress checkpoints, and human handoff.
- Review of materials and sensitive answers before final submission.
- Explicit confirmation evidence and a pending-confirmation state when results are unclear.
- No automatic resubmission after an ambiguous outcome.

## v0.3 - Broader coverage and durable runs

- Opt-in local scheduling with timezone, next-run visibility, and stop controls.
- More source adapters, source refresh policies, caching, and optional notifications.
- Broader script/font support, richer resume templates, and configurable document formatting.
- Carefully scoped semantic question matching with human review.
- Legacy-data import preview, migration reports, and guided backup/restore.

Support is declared per tested platform and integration. General configuration does not
imply that every occupation, legal jurisdiction, job board, or model endpoint is supported.
