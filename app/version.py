"""Application version: single source is the VERSION file at the project root."""
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_VERSION_FILE = _PROJECT_ROOT / "VERSION"

_FALLBACK_VERSION = "0.0.0"
APP_BUILD_DATE = "2026-09-11"
# Filled after the Windows EXE for this VERSION is built. Empty until then.
WINDOWS_SETUP_SHA256 = "30AF88B0EB5107C41F8DFCDD460D72A9B8D56FF3EA09AA96CAD8DDDD834B02AA"


def _read_version() -> str:
    try:
        text = _VERSION_FILE.read_text(encoding="utf-8")
    except OSError:
        return _FALLBACK_VERSION
    line = (text.splitlines() or [""])[0].strip()
    return line or _FALLBACK_VERSION


APP_VERSION = _read_version()
