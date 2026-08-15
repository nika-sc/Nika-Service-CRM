#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "templates" / "base.html"
lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
out = []
i = 0
skip_style = False
while i < len(lines):
    line = lines[i]
    if not skip_style and line.strip() == "<style>":
        window = "".join(lines[i : min(i + 6, len(lines))])
        if "overflow-x: hidden" in window:
            skip_style = True
            out.append(
                '    <link rel="stylesheet" href="{{ url_for(\'static\', filename=\'css/app-chrome.css\') }}">\n'
            )
            i += 1
            continue
    if skip_style:
        if line.strip() == "</style>":
            skip_style = False
        i += 1
        continue
    if line.strip() == "<style>" and i + 1 < len(lines) and "Pre-hint" in lines[i + 1]:
        out.append('    <style nonce="{{ csp_nonce() }}">\n')
        i += 1
        continue
    if line.strip() == "<script>" and i + 1 < len(lines):
        nxt = lines[i + 1]
        if "Применяем тему максимально рано" in nxt:
            out.append(
                '    <script src="{{ url_for(\'static\', filename=\'js/app_theme_early.js\') }}"></script>\n'
            )
            i += 2
            while i < len(lines) and "</script>" not in lines[i]:
                i += 1
            i += 1
            continue
        if "Дублируем класс темы" in nxt:
            out.append(
                '    <script src="{{ url_for(\'static\', filename=\'js/app_theme_body.js\') }}"></script>\n'
            )
            i += 2
            while i < len(lines) and "</script>" not in lines[i]:
                i += 1
            i += 1
            continue
    if "// Передаем ID текущего пользователя" in line:
        out.append('    <script type="application/json" id="app-boot-config" nonce="{{ csp_nonce() }}">\n')
        out.append("    {\n")
        out.append(
            '        "currentUserId": {% if current_user.is_authenticated %}{{ current_user.id }}{% else %}null{% endif %},\n'
        )
        out.append(
            '        "currentUsername": {{ (current_user.username or "")|tojson if current_user.is_authenticated else "null"|tojson }},\n'
        )
        out.append(
            '        "currentUserRole": {{ (current_user.role or "")|tojson if current_user.is_authenticated else "null"|tojson }},\n'
        )
        out.append(
            '        "staffChatEnabled": {{ "true" if current_user.is_authenticated and has_any_permission(\'view_orders\', \'create_orders\', \'edit_orders\', \'view_finance\', \'manage_finance\', \'view_warehouse\', \'manage_warehouse\', \'manage_shop\', \'salary.view\') else "false" }},\n'
        )
        out.append('        "staffChatPushSwUrl": "/staff-chat-push-sw.js",\n')
        out.append(
            '        "demoVisitorStatsEnabled": {{ "true" if demo_visitor_stats_enabled and current_user.is_authenticated else "false" }},\n'
        )
        out.append(
            '        "demoVisitorHeartbeat": {{ "true" if demo_visitor_stats_enabled and current_user.is_authenticated else "false" }},\n'
        )
        out.append(
            '        "demoVisitorPollOnline": {{ "true" if demo_visitor_stats_enabled and demo_visitor_stats_admin and current_user.is_authenticated else "false" }}\n'
        )
        out.append("    }\n")
        out.append("    </script>\n")
        out.append('    <script src="{{ url_for(\'static\', filename=\'js/app_boot.js\') }}"></script>\n')
        while i < len(lines) and "</script>" not in lines[i]:
            i += 1
        i += 1
        continue
    if "window.demoVisitorStatsEnabled = true" in line:
        while i < len(lines) and "</script>" not in lines[i]:
            i += 1
        i += 1
        continue
    if "// Global fetch() wrapper" in line:
        out.append(
            '    <script src="{{ url_for(\'static\', filename=\'js/app_fetch_csrf.js\') }}"></script>\n'
        )
        while i < len(lines) and "</script>" not in lines[i]:
            i += 1
        i += 1
        continue
    if "// Скрипт для управления состоянием меню" in line:
        out.append(
            '    <script src="{{ url_for(\'static\', filename=\'js/app_sidebar_menu.js\') }}"></script>\n'
        )
        while i < len(lines) and "</script>" not in lines[i]:
            i += 1
        i += 1
        continue
    out.append(line)
    i += 1
path.write_text("".join(out), encoding="utf-8")
print("OK")
