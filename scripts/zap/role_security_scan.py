#!/usr/bin/env python3
"""
Прогон сценариев по ролям без ZAP: логин (с CSRF) + GET по списку URL, сводка кодов ответа.
Дополняет OWASP ZAP там, где нужна сессия; не заменяет активное сканирование ZAP.

  copy scripts\\zap\\scan_users.example.json scripts\\zap\\scan_users.json
  редактируй пароли
  .venv-win\\Scripts\\python.exe scripts\\zap\\role_security_scan.py --base-url http://127.0.0.1:5000

Требуется запущенный CRM. Учти лимиты brute-force на /login (не гоняй десятки раз подряд).
"""
from __future__ import annotations

import argparse
import http.cookiejar
import json
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional, Tuple


DEFAULT_PATHS = [
    "/",
    "/all_orders",
    "/salary",
    "/reports",
    "/shop",
    "/finance",
    "/customers",
    "/api/device-types",
]


class _CsrfParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.token: Optional[str] = None

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        if self.token is not None:
            return
        ad = dict(attrs)
        if tag == "input" and ad.get("name") == "csrf_token" and ad.get("value"):
            self.token = ad.get("value")


def _build_opener(ctx: Optional[ssl.SSLContext], cookie_jar: Optional[http.cookiejar.CookieJar] = None):
    cj = cookie_jar or http.cookiejar.CookieJar()
    handlers: List = [urllib.request.HTTPCookieProcessor(cj)]
    if ctx is not None:
        handlers.append(urllib.request.HTTPSHandler(context=ctx))
    return urllib.request.build_opener(*handlers), cj


def _fetch(
    opener: urllib.request.OpenerDirector,
    url: str,
    method: str = "GET",
    data: Optional[bytes] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Tuple[int, Dict[str, str], bytes]:
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("User-Agent", "NikaCRM-role-security-scan/1.0")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with opener.open(req, timeout=60) as resp:
            body = resp.read()
            hdrs = {k.lower(): v for k, v in resp.headers.items()}
            return resp.getcode() or 200, hdrs, body
    except urllib.error.HTTPError as e:
        body = e.read()
        hdrs = {k.lower(): v for k, v in e.headers.items()} if e.headers else {}
        return e.code, hdrs, body


def _parse_csrf(html: bytes) -> Optional[str]:
    p = _CsrfParser()
    try:
        p.feed(html.decode("utf-8", errors="replace"))
    except Exception:
        return None
    return p.token


def _login_ok(opener: urllib.request.OpenerDirector, base: str, username: str, password: str) -> bool:
    login_url = base.rstrip("/") + "/login"
    code, _, body = _fetch(opener, login_url)
    if code != 200:
        print(f"  GET /login -> {code}", file=sys.stderr)
        return False
    token = _parse_csrf(body)
    if not token:
        print("  Не найден csrf_token на странице логина", file=sys.stderr)
        return False
    form = urllib.parse.urlencode(
        {
            "csrf_token": token,
            "username": username,
            "password": password,
        }
    ).encode("utf-8")
    code, _, _ = _fetch(
        opener,
        login_url,
        method="POST",
        data=form,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": login_url,
            "Origin": urllib.parse.urlparse(login_url).scheme
            + "://"
            + urllib.parse.urlparse(login_url).netloc,
        },
    )
    if code not in (200, 302, 303):
        print(f"  POST /login -> {code}", file=sys.stderr)
        return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Скан по ролям: логин + GET URL")
    ap.add_argument("--base-url", default="http://127.0.0.1:5000", help="Базовый URL CRM")
    ap.add_argument(
        "--users-file",
        type=Path,
        default=Path(__file__).resolve().parent / "scan_users.json",
        help="JSON со списком {role, username, password} (см. scan_users.example.json)",
    )
    ap.add_argument(
        "--paths-file",
        type=Path,
        default=None,
        help="Необязательный JSON-массив путей [\"/a\", ...]",
    )
    args = ap.parse_args()

    base = args.base_url.rstrip("/")
    ctx = None
    if base.startswith("https://"):
        ctx = ssl.create_default_context()

    paths = list(DEFAULT_PATHS)
    if args.paths_file and args.paths_file.is_file():
        paths = json.loads(args.paths_file.read_text(encoding="utf-8"))

    if not args.users_file.is_file():
        print(f"Нет файла {args.users_file} — скопируйте scan_users.example.json и заполните пароли.", file=sys.stderr)
        return 2

    users = json.loads(args.users_file.read_text(encoding="utf-8"))
    if not isinstance(users, list) or not users:
        print("users-file должен содержать непустой JSON-массив", file=sys.stderr)
        return 2

    opener_pub, _ = _build_opener(ctx)

    print("=== Заголовки публичной /login (без сессии) ===")
    code, hdrs, _ = _fetch(opener_pub, base + "/login")
    print(f"HTTP {code}")
    for h in ("x-frame-options", "content-security-policy", "content-security-policy-report-only", "set-cookie"):
        v = hdrs.get(h)
        if v:
            print(f"  {h}: {v[:120]}{'...' if len(v) > 120 else ''}")

    print("\n=== Прогон по ролям ===")
    for u in users:
        role = u.get("role", "?")
        user = u.get("username", "")
        pw = u.get("password", "")
        print(f"\n-- {role} ({user}) --")
        opener, _cj = _build_opener(ctx)
        if not _login_ok(opener, base, user, pw):
            print("  LOGIN FAILED")
            continue
        for path in paths:
            url = base + (path if path.startswith("/") else "/" + path)
            c, _, b = _fetch(opener, url)
            snippet = (b[:80].decode("utf-8", errors="replace").replace("\n", " ") if b else "")
            print(f"  {path:32} -> {c:3}  ({len(b)} B) {snippet}")

    print("\nГотово. Для OWASP ZAP baseline/full см. scripts/zap/Run-ZapBaseline.ps1 (нужен Docker).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
