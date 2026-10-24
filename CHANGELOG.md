# Changelog

## 0.2.0

First-run setup now proactively records customizable search, ranking, material, and delivery preferences, including explicit no-preference choices and optional fallback. Parallel source collection uses host tools with a central merge and frozen ranks. Helpers validate setup and fallback permission, preserve the selected rank order, and publish a daily preparation report with counts, section issues, and PASS/WARN/BLOCKED.

The workflow ends after preparation and optional file handoff. Muse result writeback, receipt collection, and application monitoring are outside scope. Schema version 1 remains readable with legacy warnings; new runs use schema version 2. Bounded Codex host acceptance exercised live supplied-link collection and material preparation; Claude Code acceptance remains blocked by account availability.

Host acceptance found and clarified the distinction between structured private question records and text summaries in a published batch. Observed host results and remaining limits are recorded in `evals/host-acceptance.md`.

## 0.1.0

Portable conversational skill, factual material preparation instructions, PDF and immutable dated-batch helpers, local handoff files, and cross-platform CI with a verified skill ZIP.
