#!/usr/bin/env python3
# fix_labels.py - zone names now come from the data file (single source of
# truth), not hardcoded JS. Renaming for another city = edit one label table.
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(ROOT, "dashboard", "templates", "index.html")

src = open(PATH, encoding="utf-8").read()
fails = []


def rep(a, b, label):
    global src
    n = src.count(a)
    if n == 1:
        src = src.replace(a, b)
        print("OK   " + label)
    elif n == 0 and b in src:
        print("SKIP " + label + " (already applied)")
    else:
        print("FAIL " + label + " (found " + str(n) + ")")
        fails.append(label)


# 1) remove the hardcoded zone map
rep('var ZONE = { "15":"Northside", "35":"Downtown", "101":"Eastside",\n'
    '  "105":"Central Park", "113":"Westside", "201":"South Harbor" };',
    'var ZONE = null;',
    "hardcoded zone map removed")

# 2) build it at runtime from the data labels (meta.sensors)
rep('  S.data = raw;\n  buildExpectation();',
    '  S.data = raw;\n'
    '  ZONE = {};\n'
    '  S.data.meta.sensors.forEach(function(s){\n'
    '    var lbl = s.label || s.id;\n'
    '    lbl = lbl.replace(/\\s+(Residential|Commercial|Industrial|'
    'District|Suburb|Zone)$/i, "");\n'
    '    ZONE[s.id] = lbl;\n'
    '  });\n'
    '  buildExpectation();',
    "labels loaded from data")

# 3) integrity gate
js_all = src[src.find("<script>\n") + 9: src.rfind("</script>")]
checks = [
    ("js braces balanced", js_all.count("{") == js_all.count("}")),
    ("js parens balanced", js_all.count("(") == js_all.count(")")),
    ("js double quotes even", js_all.count('"') % 2 == 0),
    ("no apostrophes in js", "'" not in js_all),
    ("ends with </html>", src.rstrip().endswith("</html>")),
]
for name, ok in checks:
    print(("  OK  " if ok else "  FAIL") + " " + name)

if fails or not all(ok for _, ok in checks):
    print("FAILED:", fails, "- NOTHING WRITTEN.")
else:
    with open(PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(src)
    print("saved (" + str(len(src)) + " chars)")
    print("INTEGRITY: OK - browser -> Ctrl+Shift+R")


main()