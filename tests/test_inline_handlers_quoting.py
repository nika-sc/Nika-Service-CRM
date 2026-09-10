"""Inline handlers must not embed |tojson: it emits double quotes and kills the attribute."""
import re
from pathlib import Path

BROKEN = re.compile(r'on(?:click|change|submit|input)="[^"]*\|\s*tojson')


def test_no_tojson_inside_inline_handlers():
    offenders = []
    for template in Path("templates").rglob("*.html"):
        if BROKEN.search(template.read_text(encoding="utf-8")):
            offenders.append(str(template))
    assert not offenders, f"pass values via data-* attributes instead: {offenders}"
