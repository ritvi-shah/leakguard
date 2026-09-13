#!/usr/bin/env python3
# find_paren.py - finds which JS entry in final_build.py lost a parenthesis.
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import final_build as fb

js = "\n".join(fb.JS)
po, pc = js.count("("), js.count(")")
print("total ( =", po, "| total ) =", pc, "| diff =", po - pc)
print()

deltas = []
cum = 0
last_zero = -1
for i, ln in enumerate(fb.JS):
    instr = False
    code = []
    for ch in ln:
        if ch == '"':
            instr = not instr
            continue
        if not instr and ch in "()":
            code.append(ch)
    d = code.count("(") - code.count(")")
    deltas.append(d)
    cum += d
    if cum == 0:
        last_zero = i

print("Suspect entries (unbalanced code parens AFTER the last")
print("point where the whole file was back in balance):")
shown = 0
for i, d in enumerate(deltas):
    if d != 0 and i > last_zero:
        print("  [" + str(i) + "] delta=" + str(d))
        print("      " + fb.JS[i])
        shown += 1
if shown == 0:
    print("  (none isolated - paste me the full delta list below)")
print()
print("All entries with unbalanced code parens (for reference):")
for i, d in enumerate(deltas):
    if d != 0:
        print("  [" + str(i) + "] delta=" + str(d) + "  " + fb.JS[i])