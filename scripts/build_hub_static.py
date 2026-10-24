"""Build the static blog and docs for the nika-crm.ru hub.

Source of truth stays in this repository:
  docs/blog/*.md        -> /blog/<slug>/
  docs/USER_GUIDE.md    -> /docs/guide/
  docs/USER_WALKTHROUGH.md -> /docs/walkthrough/
  docs/ABOUT.md         -> /docs/about/
  docs/API.md           -> /docs/api/
  docs/assets/**        -> /docs/assets/**

Run from the repository root:

    python scripts/build_hub_static.py --out "C:/Users/111/NikaFitnessCrm/sites/nika-crm-hub"
"""
from __future__ import annotations

import argparse
import html
import re
import shutil
from datetime import datetime
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
BLOG_DIR = ROOT / "docs" / "blog"
DOCS_DIR = ROOT / "docs"
REGISTRY = ROOT / "app" / "routes" / "public_blog.py"
SITE = "https://www.nika-crm.ru"

DOC_PAGES = [
    ("guide", "USER_GUIDE.md", "Руководство пользователя", "Установка, заявки, склад, касса, зарплата и настройки Nika CRM."),
    ("walkthrough", "USER_WALKTHROUGH.md", "Пошаговый сценарий", "Первый рабочий день в Nika CRM: от заявки до закрытия и оплаты."),
    ("about", "ABOUT.md", "О программе", "Что такое Nika CRM, из чего состоит и как развернуть её у себя."),
    ("api", "API.md", "API", "HTTP API Nika CRM для интеграций и автоматизации."),
]

HEADER = """  <header class="site-header">
    <div class="header-inner">
      <a class="brand" href="https://www.nika-crm.ru/">
        <span class="brand-mark">N</span>
        <span>
          <span class="brand-title">Nika CRM</span>
          <span class="brand-sub">CRM для сервисного центра</span>
        </span>
      </a>
      <button class="nav-toggle" type="button" data-nika-toggle="collapse" data-nika-target="#hubNav" aria-controls="hubNav" aria-expanded="false" aria-label="Меню">
        <i class="bi bi-list" aria-hidden="true"></i>
      </button>
      <nav class="nav-panel" id="hubNav" aria-label="Навигация Nika CRM">
        <a class="nav-link" href="https://www.nika-crm.ru/#product">О CRM</a>
        <a class="nav-link" href="https://www.nika-crm.ru/#features">Возможности</a>
        <a class="nav-link" href="https://www.nika-crm.ru/#setup">Установка</a>
        <a class="nav-link" href="/blog/">Блог</a>
        <a class="nav-link" href="/docs/">Документация</a>
        <a class="ml-btn ml-btn-ghost" href="https://github.com/nika-sc/Nika-Service-CRM">GitHub</a>
        <a class="ml-btn ml-btn-primary" href="https://service.nika-crm.ru/">Открыть демо</a>
      </nav>
    </div>
  </header>
"""

FOOTER = """  <footer class="site-footer">
    <div class="footer-inner">
      <a class="brand" href="https://www.nika-crm.ru/">
        <span class="brand-mark brand-mark-sm">N</span>
        <strong>Nika CRM</strong>
      </a>
      <div class="footer-links">
        <a href="https://github.com/nika-sc/Nika-Service-CRM/blob/main/LICENSE">Лицензия © 2026 Alexander Smelkov</a>
        <a href="/blog/">Блог</a>
        <a href="/docs/guide/">Руководство</a>
        <a href="https://service.nika-crm.ru/">Демо</a>
        <a href="https://github.com/nika-sc/Nika-Service-CRM">GitHub</a>
      </div>
    </div>
  </footer>
"""

PAGE = """<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <meta name="description" content="{description}">
  <meta name="robots" content="index, follow, max-image-preview:large">
  <link rel="canonical" href="{canonical}">
  <meta property="og:type" content="article">
  <meta property="og:locale" content="ru_RU">
  <meta property="og:site_name" content="Nika CRM">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{description}">
  <meta property="og:url" content="{canonical}">
  <meta name="theme-color" content="#2bb8a6">
  <link rel="stylesheet" href="/vendor/bootstrap-icons/1.13.1/font/bootstrap-icons.min.css">
  <link rel="stylesheet" href="/css/hub-page.css">
  <link rel="stylesheet" href="/css/blog.css">
</head>
<body>
{header}
  <main class="wrap article-page">
{body}
  </main>
{footer}
  <script src="/js/nika-ui.js"></script>
</body>
</html>
"""

BLOG_CSS = """/* Article pages for the nika-crm.ru hub (blog + docs). */
.article-page { max-width: 880px; padding-top: 28px; padding-bottom: 56px; }
.article-page .eyebrow { color: #0d7d70; font-weight: 600; letter-spacing: .04em; text-transform: uppercase; font-size: .8rem; margin: 0 0 8px; }
.article-page h1 { font-size: clamp(1.6rem, 2.6vw, 2.3rem); line-height: 1.2; margin: 0 0 10px; color: #10221f; }
.article-date { color: #6b7c78; margin: 0 0 26px; font-size: .92rem; }
.article-body { color: #1c2b28; font-size: 1.03rem; line-height: 1.65; }
.article-body h2 { margin: 34px 0 12px; font-size: 1.45rem; color: #10221f; }
.article-body h3 { margin: 26px 0 10px; font-size: 1.18rem; color: #10221f; }
.article-body p { margin: 0 0 14px; }
.article-body ul, .article-body ol { margin: 0 0 16px 22px; }
.article-body li { margin: 4px 0; }
.article-body a { color: #0d7d70; }
.article-body img { max-width: 100%; height: auto; border-radius: 12px; box-shadow: 0 8px 24px rgba(16,34,31,.12); margin: 10px 0; }
.article-body figure { margin: 18px 0; }
.article-body figcaption { color: #6b7c78; font-size: .9rem; margin-top: 6px; }
.article-body table { border-collapse: collapse; width: 100%; margin: 16px 0; font-size: .95rem; }
.article-body th, .article-body td { border: 1px solid #dbe6e3; padding: 8px 10px; text-align: left; vertical-align: top; }
.article-body th { background: #f2f8f6; }
.article-body code { background: #f2f8f6; padding: 1px 5px; border-radius: 5px; font-size: .92em; }
.article-body pre { background: #10221f; color: #e8f5f2; padding: 14px 16px; border-radius: 10px; overflow-x: auto; }
.article-body pre code { background: none; color: inherit; padding: 0; }
.article-body blockquote { border-left: 3px solid #2bb8a6; margin: 16px 0; padding: 4px 0 4px 14px; color: #3d5450; }
.post-list { list-style: none; margin: 0; padding: 0; }
.post-list li { border-bottom: 1px solid #e2ecea; padding: 16px 0; }
.post-list a { font-size: 1.12rem; font-weight: 600; color: #0d7d70; text-decoration: none; }
.post-list .post-date { color: #6b7c78; font-size: .86rem; display: block; margin-bottom: 4px; }
.post-list .post-teaser { color: #3d5450; margin: 6px 0 0; }
"""


def slugify_date(value: str) -> str:
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d %H:%M").strftime("%d.%m.%Y")
    except ValueError:
        return value


def read_registry() -> list[dict]:
    text = REGISTRY.read_text(encoding="utf-8")
    start = text.index("_POSTS = [")
    end = text.index("\n]", start)
    body = text[start:end]
    posts = []
    for block in re.split(r"\n    \},\n    \{", body):
        slug = re.search(r'"slug": "([^"]+)"', block)
        file = re.search(r'"file": "blog/([^"]+)"', block)
        date = re.search(r'"date": "([^"]+)"', block)
        title = re.search(r'"title": "([^"]+)"', block)
        teaser = re.search(r'"teaser": "([^"]+)"', block)
        if not (slug and file and date and title):
            continue
        posts.append({
            "slug": slug.group(1),
            "file": file.group(1),
            "date": date.group(1),
            "title": title.group(1),
            "teaser": teaser.group(1) if teaser else "",
        })
    return posts


def rewrite_links(md_text: str) -> str:
    replacements = {
        "](USER_GUIDE.md)": "](/docs/guide/)",
        "](USER_WALKTHROUGH.md)": "](/docs/walkthrough/)",
        "](ABOUT.md)": "](/docs/about/)",
        "](API.md)": "](/docs/api/)",
        "](/blog/windows-setup-1-0-11)": "](/blog/windows-setup-1-0-11/)",
    }
    for old, new in replacements.items():
        md_text = md_text.replace(old, new)
    # relative images inside docs/ -> absolute static assets
    md_text = re.sub(r"!\[([^\]]*)\]\((assets/)([^)]+)\)", r"![\1](/docs/\2\3)", md_text)
    # links to .md pages with anchors
    md_text = re.sub(r"\((USER_GUIDE|USER_WALKTHROUGH|ABOUT|API)\.md#([^)]+)\)", r"(/docs/\1/#\2)", md_text)
    return md_text


def render_markdown(text: str) -> str:
    text = re.sub(r"\A\s*#\s+[^\n]+\n", "", text)
    return markdown.markdown(
        rewrite_links(text),
        extensions=["extra", "toc", "sane_lists"],
        output_format="html5",
    )


def page(title: str, description: str, canonical: str, body: str) -> str:
    return PAGE.format(
        title=html.escape(title),
        description=html.escape(description),
        canonical=canonical,
        header=HEADER,
        footer=FOOTER,
        body=body,
    )


def build_blog(out: Path, posts: list[dict]) -> None:
    index_items = []
    for post in posts:
        source = BLOG_DIR / post["file"]
        if not source.is_file():
            print("missing post:", source)
            continue
        body = render_markdown(source.read_text(encoding="utf-8"))
        title = re.sub(r"\s+—\s+Nika CRM$", "", post["title"])
        url = f"/blog/{post['slug']}/"
        canonical = f"{SITE}{url}"
        article = (
            f'    <p class="eyebrow"><a href="/blog/">Блог</a></p>\n'
            f"    <h1>{html.escape(title)}</h1>\n"
            f'    <p class="article-date">{slugify_date(post["date"])}</p>\n'
            f'    <article class="article-body">\n{body}\n    </article>'
        )
        target = out / "blog" / post["slug"] / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page(f"{title} — Nika CRM", post["teaser"] or title, canonical, article), encoding="utf-8")
        index_items.append(
            f'        <li><span class="post-date">{slugify_date(post["date"])}</span>'
            f'<a href="{url}">{html.escape(title)}</a>'
            + (f'<p class="post-teaser">{html.escape(post["teaser"])}</p>' if post["teaser"] else "")
            + "</li>"
        )
    index_body = (
        '    <p class="eyebrow">Nika CRM</p>\n'
        "    <h1>Блог</h1>\n"
        '    <p class="article-date">История версий, разборы и инструкции.</p>\n'
        '    <ul class="post-list">\n' + "\n".join(index_items) + "\n    </ul>"
    )
    (out / "blog").mkdir(parents=True, exist_ok=True)
    (out / "blog" / "index.html").write_text(
        page("Блог Nika CRM", "История версий, разборы и инструкции Nika CRM.", f"{SITE}/blog/", index_body),
        encoding="utf-8",
    )


def build_docs(out: Path) -> None:
    cards = []
    for slug, filename, title, description in DOC_PAGES:
        source = DOCS_DIR / filename
        if not source.is_file():
            print("missing doc:", source)
            continue
        body = render_markdown(source.read_text(encoding="utf-8"))
        url = f"/docs/{slug}/"
        article = (
            f'    <p class="eyebrow"><a href="/docs/">Документация</a></p>\n'
            f"    <h1>{html.escape(title)}</h1>\n"
            f'    <article class="article-body">\n{body}\n    </article>'
        )
        target = out / "docs" / slug / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page(f"{title} — Nika CRM", description, f"{SITE}{url}", article), encoding="utf-8")
        cards.append(
            f'        <li><a href="{url}">{html.escape(title)}</a>'
            f'<p class="post-teaser">{html.escape(description)}</p></li>'
        )
    index_body = (
        '    <p class="eyebrow">Nika CRM</p>\n'
        "    <h1>Документация</h1>\n"
        '    <p class="article-date">Руководство, сценарий работы и API.</p>\n'
        '    <ul class="post-list">\n' + "\n".join(cards) + "\n    </ul>"
    )
    (out / "docs").mkdir(parents=True, exist_ok=True)
    (out / "docs" / "index.html").write_text(
        page("Документация Nika CRM", "Руководство пользователя, сценарий работы и API Nika CRM.", f"{SITE}/docs/", index_body),
        encoding="utf-8",
    )


def copy_assets(out: Path) -> None:
    source = DOCS_DIR / "assets"
    target = out / "docs" / "assets"
    if target.exists():
        for item in target.rglob("*"):
            try:
                item.chmod(0o666)
            except OSError:
                pass
        shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(source, target, dirs_exist_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="hub site root (sites/nika-crm-hub)")
    args = parser.parse_args()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "css").mkdir(parents=True, exist_ok=True)
    (out / "css" / "blog.css").write_text(BLOG_CSS, encoding="utf-8")
    posts = read_registry()
    build_blog(out, posts)
    build_docs(out)
    copy_assets(out)
    print(f"blog posts: {len(posts)}")
    print(f"docs pages: {len(DOC_PAGES)}")
    print(f"output: {out}")


if __name__ == "__main__":
    main()
