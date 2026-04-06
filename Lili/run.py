from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _bootstrap_local_venv() -> None:
    project_root = Path(__file__).resolve().parent
    venv_root = project_root / ".venv"
    venv_python = venv_root / "Scripts" / "python.exe"

    if Path(sys.executable).resolve() == venv_python.resolve():
        return

    if not venv_python.exists():
        return

    relaunched_flag = "LILI_RELAUNCHED_FROM_VENV"
    if os.environ.get(relaunched_flag) == "1":
        return

    env = os.environ.copy()
    env[relaunched_flag] = "1"
    raise SystemExit(
        subprocess.call(
            [str(venv_python), str(Path(__file__).resolve()), *sys.argv[1:]],
            cwd=str(project_root),
            env=env,
        )
    )


_bootstrap_local_venv()

from app.main import main


if __name__ == "__main__":
    raise SystemExit(main())
