"""Run tests without reading any .env file or displaying configuration secrets."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Settings

Settings.model_config["env_file"] = None

import pytest

if __name__ == "__main__":
    raise SystemExit(pytest.main(sys.argv[1:]))
