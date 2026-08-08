"""
Чтение/запись ключей в файл .env без затирания остальных переменных.
Используется для синхронизации SMTP из Настроек CRM.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, Mapping, Optional

logger = logging.getLogger(__name__)

MAIL_ENV_KEYS = (
    "MAIL_SERVER",
    "MAIL_PORT",
    "MAIL_USE_TLS",
    "MAIL_USE_SSL",
    "MAIL_USERNAME",
    "MAIL_PASSWORD",
    "MAIL_DEFAULT_SENDER",
    "MAIL_TIMEOUT",
)


def resolve_dotenv_path() -> Optional[Path]:
    """Путь к .env: DOTENV_PATH → Windows ProgramData\\NikaCRM\\.env → корень репо."""
    override = (os.environ.get("DOTENV_PATH") or "").strip()
    if override:
        return Path(override)

    program_data = (os.environ.get("PROGRAMDATA") or "").strip()
    if program_data:
        win_path = Path(program_data) / "NikaCRM" / ".env"
        if win_path.is_file():
            return win_path

    # app/utils/dotenv_file.py → корень репозитория
    repo_root = Path(__file__).resolve().parents[2]
    repo_env = repo_root / ".env"
    if repo_env.is_file():
        return repo_env

    # Каталог запуска (systemd/WorkingDirectory или Windows service cwd)
    cwd_env = Path.cwd() / ".env"
    if cwd_env.is_file():
        return cwd_env

    return None


def _escape_env_value(value: str) -> str:
    text = (value or "").replace("\r", "").replace("\n", " ").strip()
    if not text:
        return ""
    if any(ch in text for ch in (' ', '#', '=', '"', "'")):
        return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return text


def upsert_dotenv_keys(path: Path, updates: Mapping[str, str]) -> bool:
    """
    Обновляет/добавляет ключи в .env, сохраняя остальные строки и комментарии.
    Возвращает True, если файл изменился.
    """
    if not path.is_file():
        return False

    raw = path.read_text(encoding="utf-8-sig")
    lines = raw.splitlines()
    remaining = dict(updates)
    out = []
    changed = False

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            out.append(line)
            continue
        key, _, _old_val = stripped.partition("=")
        key = key.strip().lstrip("\ufeff")
        if key in remaining:
            new_val = remaining.pop(key)
            new_line = f"{key}={_escape_env_value(new_val)}"
            if new_line != line.strip():
                changed = True
            out.append(new_line)
        else:
            out.append(line)

    for key, value in remaining.items():
        out.append(f"{key}={_escape_env_value(value)}")
        changed = True

    if not changed:
        return False

    text = "\n".join(out)
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return True


def sync_mail_settings_to_dotenv(payload: Mapping) -> None:
    """
    Пишет SMTP из формы/БД в .env и в os.environ текущего процесса.
    Пустой mail_password в payload не затирает уже сохранённый MAIL_PASSWORD.
    """
    path = resolve_dotenv_path()
    if path is None:
        return

    def _as_bool(value, default: bool) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        return str(value).strip().lower() in ("1", "true", "on", "yes", "t")

    updates: Dict[str, str] = {
        "MAIL_SERVER": str(payload.get("mail_server") or "").strip(),
        "MAIL_PORT": str(payload.get("mail_port") if payload.get("mail_port") not in (None, "") else 587),
        "MAIL_USE_TLS": "True" if _as_bool(payload.get("mail_use_tls"), True) else "False",
        "MAIL_USE_SSL": "True" if _as_bool(payload.get("mail_use_ssl"), False) else "False",
        "MAIL_USERNAME": str(payload.get("mail_username") or "").strip(),
        "MAIL_DEFAULT_SENDER": str(payload.get("mail_default_sender") or "").strip(),
    }
    timeout = payload.get("mail_timeout")
    if timeout not in (None, ""):
        updates["MAIL_TIMEOUT"] = str(timeout)

    password = str(payload.get("mail_password") or "").strip()
    if password:
        updates["MAIL_PASSWORD"] = password

    try:
        if upsert_dotenv_keys(path, updates):
            logger.info("SMTP-настройки синхронизированы в %s", path)
        for key, value in updates.items():
            os.environ[key] = value
    except Exception as exc:
        logger.warning("Не удалось обновить MAIL_* в .env (%s): %s", path, exc)
