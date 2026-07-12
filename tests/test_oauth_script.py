from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def test_oauth_script_starts_from_documented_command() -> None:
    project_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PINTEREST_APP_ID"] = ""
    env["PINTEREST_APP_SECRET"] = ""

    result = subprocess.run(
        [sys.executable, "scripts/pinterest_oauth.py"],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "Add PINTEREST_APP_ID and PINTEREST_APP_SECRET" in output
    assert "ModuleNotFoundError" not in output
