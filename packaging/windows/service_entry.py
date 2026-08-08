"""Windows service entry point for the offline Nika CRM installation."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values


APP_ROOT = Path(__file__).resolve().parent
DATA_ROOT = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "NikaCRM"
ENV_FILE = DATA_ROOT / ".env"


def load_service_environment() -> None:
    if not ENV_FILE.is_file():
        raise RuntimeError(f"Nika CRM environment file not found: {ENV_FILE}")

    for name, value in dotenv_values(ENV_FILE).items():
        if not name or value is None:
            continue
        # PowerShell Set-Content -Encoding UTF8 may prefix the first key with BOM.
        key = name.lstrip("\ufeff").strip()
        if key:
            os.environ[key] = value

    os.environ.setdefault("FLASK_ENV", "production")


def main() -> None:
    load_service_environment()
    os.chdir(APP_ROOT)

    from waitress import serve
    from wsgi import app

    serve(
        app,
        host=os.environ.get("APP_HOST", "0.0.0.0"),
        port=int(os.environ.get("APP_PORT", "5000")),
        threads=8,
        channel_timeout=120,
    )


if __name__ == "__main__":
    main()
