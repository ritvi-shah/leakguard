#!/usr/bin/env python3
# fix_legend.py v2 - legend filter must use ds.text (Chart.js), not ds.label.
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(ROOT, "dashboard", "templates", "index.html")

OLD = 'return ds.label.indexOf("Alerts") !== 0;'
NEW = 'return String(ds.text || ds.label || "").indexOf("Alerts") !== 0;'


def main():
    src = open(PATH, encoding="utf-8").read()

    n = src.count(OLD)
    if n == 1:
        src = src.replace(OLD, NEW)
        print("OK   legend filter fixed")
    elif NEW in src:
        print("SKIP already applied")
        return
    else:
        print("FAIL pattern not found (" + str(n) + ") - tell the chat")
        return

    js = src[src.find("<script>\n") + 9: src.rfind("</script>")]
    checks = [
        ("js braces balanced", js.count("{") == js.count("}")),
        ("js parens balanced", js.count("(") == js.count(")")),
        ("js double quotes even", js.count('"') % 2 == 0),
        ("ends with </html>", src.rstrip().endswith("</html>")),
    ]
    ok = True
    for name, p in checks:
        print(("  OK  " if p else "  FAIL") + " " + name)
        ok = ok and p
    if not ok:
        print("NOTHING WRITTEN.")
        return
    with open(PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(src)
    print("saved (" + str(len(src)) + " chars)")
    print("INTEGRITY: OK - browser -> Ctrl+Shift+R")


main()