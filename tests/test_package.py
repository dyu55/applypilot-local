"""Check the installed command rather than the source file layout."""

import os
import subprocess
import sys
from pathlib import Path

from applypilot import __version__


def test_installed_command() -> None:
    command = Path(sys.executable).with_name("applypilot.exe" if os.name == "nt" else "applypilot")
    result = subprocess.run([str(command), "--version"], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == __version__
