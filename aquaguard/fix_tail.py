#!/usr/bin/env python3
# fix_tail.py - restores the closing tags dropped by the report replacement.
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(ROOT, "dashboard", "templates", "index.html")

src = open(PATH, encoding="utf-8").read()
print("current last 60 chars:", repr(src[-60:]))

if src.rstrip().endswith("</html>"):
    print("Tail already present - nothing to do.")
else:
    src = src.rstrip() + "\n</script>\n</body>\n</html>\n"
    with open(PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(src)
    print("appended closing tags")
    print("new last 60 chars:", repr(src[-60:]))
    print("NOW: browser -> Ctrl+Shift+R")