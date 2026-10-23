# Privacy and model behavior

Your profile, extracted resume text, scoped answers, questions, job pool, history, and
generated materials are stored in your selected local data directory. They are not encrypted
by this application. Use the operating system's disk encryption and access controls.

There is no telemetry, application-operated cloud account, automatic upload, or background
email access. An empty offline demo contacts no external service.

## Network activity

- Collecting enabled sources downloads public postings from the configured services.
- Reading a job URL fetches that page and its validated redirects.
- Opening an original posting navigates your browser to an external site.
- Model-assisted generation sends the existing bullet group and a bounded job excerpt to
  the configured endpoint. A local endpoint can still be backed by another service; inspect it.
- Installing dependencies downloads packages. The UI itself has no external fonts, scripts,
  analytics, image requests, or CDN dependencies.

API keys belong in shell environment variables, not the profile or answer bank.
The model interface reads `APPLYPILOT_MODEL_API_KEY` by default; the variable name can be
changed in Settings. Adzuna uses `ADZUNA_APP_ID` and `ADZUNA_APP_KEY`.
No password manager, browser profile, cookies, or OTPs are accessed in v0.1.

## Optional AI

The default endpoint points to a loopback address, but no model is installed or started for
you. Model assistance remains disabled until you enable it and configure a model name.
The protocol is Chat Completions-compatible with a JSON permutation response. A provider
may charge for calls, retain inputs, or have additional terms; choose it intentionally.

Only bullet ordering is accepted. The application validates that every source bullet index
appears exactly once and contains no replacement text. On an invalid response, timeout,
or exhausted call limit, keyword ordering preserves the source and a warning is recorded.
Endpoint configuration errors are shown before a material run starts.

No live hosted model has to be called for CI. Compatibility fixture tests do not constitute
verification of a particular hosted or local model. Test your chosen endpoint with fictional
data before sending your own resume.

## Backups and deletion

Stop the server before copying the complete application data directory for backup. CSV and
JSON job exports do not contain all profile, resume, question, or history information.
To delete a profile, stop the server and remove only its directory under `profiles/`.
Uninstalling the Python package leaves private data intact so upgrades do not delete it.

Use only fictional data in public issues and screenshots. The repository content scanner
is an additional guard, not a guarantee that an arbitrary file contains no personal data.
