#!/usr/bin/env python3
"""Check that last night's CRM data backup exists and is fresh.

Looks at backup_email.log (DONE backup job) and archive files in
data/database/backups/auto/. Understands current .7z names and legacy
.tar.xz / .tar.xz.enc.

Cron example (retry full backup only if this check fails):

  15 4 * * * cd /path/to/crm && python3 scripts/backup_healthcheck.py --max-age-hours 30 \\
      >> data/logs/backup_health_cron.log 2>&1 \\
      || bash scripts/backup_and_email.sh >> data/logs/backup_health_cron.log 2>&1
"""

from __future__ import annotations

import argparse
import glob
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

DONE_PATTERN = re.compile(
    r"^\[(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]\s+DONE backup job\s*$"
)

ARCHIVE_GLOBS = (
    "crm_data_backup_*.7z",
    "crm_files_backup_*.7z",
    "crm_data_backup_*_mail.7z.*",
    "crm_files_backup_*_mail.7z.*",
    "crm_data_backup_*.tar.xz",
    "crm_data_backup_*.tar.xz.enc",
    "crm_full_backup_*.7z",
    "crm_full_backup_*.tar.xz",
    "crm_full_backup_*.tar.xz.enc",
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Healthcheck for CRM backup pipeline")
    parser.add_argument(
        "--root",
        default="",
        help="CRM root (default: parent of scripts/)",
    )
    parser.add_argument(
        "--max-age-hours",
        type=int,
        default=30,
        dest="max_age_hours",
        help="Maximum allowed age for successful backup",
    )
    return parser.parse_args()


def _latest_done_timestamp(log_path: Path) -> datetime | None:
    if not log_path.exists():
        return None
    latest: datetime | None = None
    for line in log_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = DONE_PATTERN.match(line.strip())
        if not match:
            continue
        ts = datetime.strptime(match.group("ts"), "%Y-%m-%d %H:%M:%S")
        if latest is None or ts > latest:
            latest = ts
    return latest


def _latest_archive(backup_dir: Path) -> Path | None:
    names: list[str] = []
    for pat in ARCHIVE_GLOBS:
        names.extend(glob.glob(str(backup_dir / pat)))
    files = sorted(
        (Path(p) for p in names),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return files[0] if files else None


def main() -> int:
    args = _parse_args()
    now = datetime.now()
    threshold = now - timedelta(hours=args.max_age_hours)
    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[1]
    backup_log = root / "data" / "logs" / "backup_email.log"
    health_log = root / "data" / "logs" / "backup_health.log"
    backup_dir = root / "data" / "database" / "backups" / "auto"
    health_log.parent.mkdir(parents=True, exist_ok=True)

    problems: list[str] = []

    latest_done = _latest_done_timestamp(backup_log)
    if latest_done is None:
        problems.append("no DONE backup marker in backup_email.log")
    elif latest_done < threshold:
        problems.append(
            f"latest DONE too old: {latest_done.strftime('%Y-%m-%d %H:%M:%S')} "
            f"(threshold: {threshold.strftime('%Y-%m-%d %H:%M:%S')})"
        )

    latest_arc = _latest_archive(backup_dir)
    if latest_arc is None:
        problems.append("no backup archives found in auto backup directory")
    else:
        arc_mtime = datetime.fromtimestamp(latest_arc.stat().st_mtime)
        if arc_mtime < threshold:
            problems.append(
                f"latest archive too old: {latest_arc.name} "
                f"({arc_mtime.strftime('%Y-%m-%d %H:%M:%S')})"
            )

    stamp = now.strftime("%Y-%m-%d %H:%M:%S")
    if problems:
        msg = f"[{stamp}] BACKUP_HEALTH_FAIL :: " + " | ".join(problems)
        print(msg)
        with health_log.open("a", encoding="utf-8") as handle:
            handle.write(msg + "\n")
        return 1

    ok_msg = (
        f"[{stamp}] BACKUP_HEALTH_OK :: "
        f"latest_done={latest_done.strftime('%Y-%m-%d %H:%M:%S') if latest_done else 'n/a'} "
        f"latest_archive={latest_arc.name if latest_arc else 'n/a'}"
    )
    print(ok_msg)
    with health_log.open("a", encoding="utf-8") as handle:
        handle.write(ok_msg + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
