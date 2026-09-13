#!/usr/bin/env python3
# fixjs.py - shows lines around the error, replaces smart/invisible characters
# that break inline JavaScript, reports exactly what it changed.
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(ROOT, "dashboard", "templates", "index.html")

REPLACEMENTS = {
    "\u2018": "'", "\u2019": "'",      # curly single quotes
    "\u201c": '"', "\u201d": '"',      # curly double quotes
    "\u00a0": " ",                      # non-breaking space
    "\u200b": "",                       # zero-width space
    "\u202f": " ",                      # narrow no-break space
    "\u2013": "-", "\u2014": "-",      # en/em dash
    "\u2026": "...",                    # ellipsis
    "\ufeff": "",                       # BOM
}


def main():
    src = open(PATH, encoding="utf-8").read()
    lines = src.splitlines()

    print("=== lines 253-265 (repr reveals invisible characters) ===")
    for i in range(252, min(265, len(lines))):
        print(i + 1, repr(lines[i]))
    print("=== end ===\n")

    fixed = src
    changed = []
    for bad, good in REPLACEMENTS.items():
        n = fixed.count(bad)
        if n:
            fixed = fixed.replace(bad, good)
            changed.append(f"{repr(bad)} x{n}")

    if changed:
        with open(PATH, "w", encoding="utf-8", newline="\n") as f:
            f.write(fixed)
        print("FIXED and saved:", "; ".join(changed))
        print("-> refresh the browser with Ctrl+Shift+R")
    else:
        print("No smart/invisible characters found.")
        print("-> paste the lines 253-265 output above back into the chat.")


if __name__ == "__main__":
    main()