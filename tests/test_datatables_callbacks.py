"""DataTables hides its "Подождите…" overlay on the last line of the draw handler.

Any ReferenceError inside drawCallback / initComplete therefore leaves the
spinner on top of an already rendered table (был баг на /clients и /all_orders).
So every helper a callback calls has to exist in the global scope.
"""
import re
from pathlib import Path

TEMPLATES = Path("templates")
STATIC = Path("static")

CALLBACK = re.compile(
    r'"(?:drawCallback|initComplete)"\s*:\s*function\s*\([^)]*\)\s*\{(.*?)\n\s{16}\}',
    re.S,
)
CALL = re.compile(r"^\s*([A-Za-z_$][\w$]*)\s*\(", re.M)

# Defined by the browser, jQuery or DataTables itself, not by our code.
BUILTINS = {
    "if", "for", "while", "switch", "return", "function", "catch", "setTimeout",
    "parseInt", "parseFloat", "String", "Number", "Array", "Object", "JSON",
    "$", "jQuery",
}


def _globals_from_static():
    names = set()
    for path in STATIC.rglob("*.js"):
        if "cdn" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        names.update(re.findall(r"window\.([A-Za-z_$][\w$]*)\s*=", text))
        # Top-level declarations are global too (files without an IIFE).
        names.update(re.findall(r"^function\s+([A-Za-z_$][\w$]*)", text, re.M))
        names.update(re.findall(r"^(?:var|let|const)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:function|\()", text, re.M))
    return names


def test_datatables_callbacks_only_call_defined_helpers():
    static_globals = _globals_from_static()
    offenders = []
    for template in TEMPLATES.rglob("*.html"):
        text = template.read_text(encoding="utf-8")
        for body in CALLBACK.findall(text):
            for name in CALL.findall(body):
                if name in BUILTINS or name in static_globals:
                    continue
                # Defined somewhere in the same template?
                if re.search(rf"function\s+{re.escape(name)}\s*\(", text):
                    continue
                if re.search(rf"(?:var|let|const)\s+{re.escape(name)}\s*=", text):
                    continue
                offenders.append(f"{template}: {name}()")
    assert not offenders, "undefined helper in a DataTables callback: " + ", ".join(offenders)


def test_theme_helper_is_exported_for_templates():
    themes = (STATIC / "themes.js").read_text(encoding="utf-8")
    assert "window.applyTableTheme" in themes
