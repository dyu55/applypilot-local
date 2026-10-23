"""Check the installed command rather than the source file layout."""

import subprocess

from applypilot import __version__


def test_installed_command() -> None:
    result = subprocess.run(["applypilot", "--version"], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == __version__
