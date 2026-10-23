# Contributing

This is a portable agent skill. Keep instructions useful to both Codex and Claude Code, and keep the user experience conversational. Add scripts only for deterministic work that is worth reusing.

Use fictional examples and reserved domains. Never commit candidate data, private workspace files, credentials, browser sessions, generated PDFs, or application histories. All maintained content must be English.

For development, create a Python 3.11+ virtual environment outside the installed skill. Install the hash-locked requirements, then run:

```sh
python -m pip install --require-hashes -r requirements-dev.lock
ruff check .
ruff format --check .
python scripts/check_repository.py
python scripts/validate_skill.py
python -m pytest
python scripts/build_skill.py
python scripts/smoke_skill.py
```

The project is not a Python application package; do not add an executable entry point or a web server. The ZIP contains the skill folder and its required resources. Update VERSION for a new release. Dispatch the Release workflow with a matching tag after CI succeeds for that exact commit.

Dependency updates use `uv pip compile requirements-dev.in --generate-hashes --output-file requirements-dev.lock`. Keep runtime PDF requirements in the skill folder so a copied skill is self-contained. Re-run fixture tests after dependency changes.

Use evals/scenarios.json to assess agent behavior in the target host before claiming a host-level integration passed. Record tools available, prompts, generated artifacts, and observed limitations. A schema check is not evidence that an agent followed every instruction.
