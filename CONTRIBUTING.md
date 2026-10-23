# Contributing

Use Python 3.11 or newer, create a virtual environment, and follow the development
commands in the README. Repository content is English-only. No frontend build is required.

Open an issue with a concrete problem, expected behavior, and a minimal fictional example.
Do not attach real resumes, private employer correspondence, application records, secrets,
or browser sessions. Redact screenshots before sharing them.

Pull requests should describe the behavior changed and how it was validated. Add tests for
data integrity, factual boundaries, parsing behavior, and user-visible bugs. Tests must run
offline unless explicitly designated as manual live-source checks.

Job-source adapters must be read-only, bounded, respect attribution, and report partial
failures. They must not bypass anti-bot protections or invoke application submission endpoints.
Do not silently infer salary currency, work authorization, sponsorship, or personal identity.

Before requesting review, run lint, format checks, the repository content check, tests, and
package validation. Use separate profiles and temporary directories for test data.
