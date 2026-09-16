"""Set up and start the AI service with one Python command."""

from __future__ import annotations

import hashlib
import subprocess
import sys
import venv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".venv"
REQUIREMENTS = ROOT / "requirements.txt"
REQUIREMENTS_STAMP = VENV_DIR / ".requirements.sha256"


def venv_python() -> Path:
    """Return the virtual environment's Python executable for this platform."""
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def requirements_digest() -> str:
    return hashlib.sha256(REQUIREMENTS.read_bytes()).hexdigest()


def ensure_environment() -> Path:
    """Create the virtual environment and install changed dependencies."""
    python = venv_python()
    if not python.exists():
        print(f"Creating virtual environment at {VENV_DIR} ...", flush=True)
        venv.EnvBuilder(with_pip=True).create(VENV_DIR)

    digest = requirements_digest()
    installed_digest = (
        REQUIREMENTS_STAMP.read_text(encoding="utf-8").strip()
        if REQUIREMENTS_STAMP.exists()
        else None
    )
    if installed_digest != digest:
        print("Installing AI service dependencies ...", flush=True)
        subprocess.run(
            [str(python), "-m", "pip", "install", "-r", str(REQUIREMENTS)],
            cwd=ROOT,
            check=True,
        )
        REQUIREMENTS_STAMP.write_text(digest, encoding="utf-8")

    return python


def main() -> int:
    python = ensure_environment()
    print("Starting Banteay Digital AI service ...", flush=True)
    completed = subprocess.run([str(python), str(ROOT / "run.py")], cwd=ROOT)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
