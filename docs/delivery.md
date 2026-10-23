# Continuous integration and delivery

## CI

On pushes to `main`, pull requests, and manual dispatches:

1. Ruff lint and format checks.
2. English-only / private-content repository checks.
3. Tests on Linux, macOS, and Windows with Python 3.11 and 3.13.
4. A browser smoke test of the actual local web application.
5. Wheel and source distribution build, metadata validation, and clean installed-package smoke.
6. Distribution artifact upload after required checks pass.

Actions are pinned to commit hashes. Dependabot proposes action and dependency updates.
CI uses fictional fixtures and no recruiting credentials or paid model calls.
Live job-source checks are performed separately and are not represented by offline test results.

## Release

The manually dispatched Release workflow takes a tag such as `v0.1.0`. It requires the tag
to match the package version, reruns quality and test checks, builds packages, and publishes
the resulting assets to GitHub Releases. Its write permission is restricted to the publish job.
Publishing to PyPI is not configured and requires a separate, intentional distribution decision.

Before dispatching:

- Verify the intended commit's full CI is green.
- Verify the clean wheel works without a source checkout.
- Inspect English-only content and distribution file lists.
- Update the version and release notes for the actual implemented behavior.
- Inspect generated demo screenshots and PDF pages using only fictional data.

Repository credentials are supplied by GitHub Actions for release publication. No personal
token or candidate data is stored as a project secret or included in release artifacts.
