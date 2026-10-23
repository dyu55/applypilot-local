# ApplyPilot Local

A private, local-first job search workspace for every career.

This project is under active development toward v0.1. It runs independently of
any AI agent, messaging platform, or cloud account. All examples use fictional people.

## Development

Requires Python 3.11 or later.

```sh
python -m venv .venv
python -m pip install -e ".[dev]"
python -m pytest
```

Activate the virtual environment before installing; see the installation guide as it is added.

## Delivery

GitHub Actions checks formatting, lint, English-only repository content, tests,
and package installation on Linux, macOS, and Windows. Passing main-branch builds
produce wheel and source archives. The release workflow validates a version tag
and publishes the tested archives to GitHub Releases.

## Privacy

Candidate profiles, original resumes, answer banks, application history, API keys,
and browser sessions belong in the user's local data directory, outside this repository.
The application will never treat generated materials as proof of an application submission.

## License

MIT. See [LICENSE](LICENSE).

