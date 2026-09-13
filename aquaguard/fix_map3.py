#!/usr/bin/env python3
# fix_map3.py - big invisible click-areas on map districts, hover glow,
# defensive tail fix. Writes only if all checks pass.
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


# 0) defensive: ensure closing tags exist
if not src.rstrip().endswith("</html>"):
    src = src.rstrip() + "\n</script>\n</body>\n</html>\n"
    print("OK   closing tags restored (tail was missing)")

# 1) big invisible hit-area + group class for hover
rep('    if(n.is_sensor) g.appendChild(el("circle",\n'
    '      { cx:x, cy:y, r:10, "class":"mring" }));',
    '    if(n.is_sensor){\n'
    '      g.setAttribute("class", "mgrp");\n'
    '      g.appendChild(el("circle",\n'
    '        { cx:x, cy:y, r:10, "class":"mring" }));\n'
    '      g.appendChild(el("circle",\n'
    '        { cx:x, cy:y, r:16, fill:"transparent",\n'
    '          "pointer-events":"all" }));\n'
    '    }',
    "16px hit-area on districts")

# 2) hover glow css
rep(".mring{fill:none;stroke:#0b6e99;stroke-width:2.2}",
    ".mring{fill:none;stroke:#0b6e99;stroke-width:2.2}\n"
    ".mgrp{cursor:pointer}\n"
    ".mgrp:hover .mring{stroke-width:3.8}\n"
    ".mgrp:hover .mdot.sndot{fill:#085a7d}",
    "district hover glow")

# 3) verify integrity of the whole script section
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