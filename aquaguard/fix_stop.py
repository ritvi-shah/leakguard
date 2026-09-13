#!/usr/bin/env python3
# fix_stop.py v2 - makes the button a true toggle: Watch detection -> Stop.
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(ROOT, "dashboard", "templates", "index.html")

OLD_WIRE = ('  $("playBtn").onclick = function(){\n'
            '    var fa = firstIdx(S.d.series.twin_flag);\n'
            '    if(fa === null){\n'
            '      showFatal("Baseline scenario: nothing to detect -" +\n'
            '        " pick a leak scenario to watch.");\n'
            '      return;\n'
            '    }\n'
            '    pause();\n'
            '    setIndex(Math.max(0, fa - 96));\n'
            '    S.playing = true; tickLoop(); };')

NEW_WIRE = ('  $("playBtn").onclick = function(){\n'
            '    if(S.playing){ pause(); return; }\n'
            '    var fa = firstIdx(S.d.series.twin_flag);\n'
            '    if(fa === null){\n'
            '      showFatal("Baseline scenario: nothing to detect -" +\n'
            '        " pick a leak scenario to watch.");\n'
            '      return;\n'
            '    }\n'
            '    pause();\n'
            '    setIndex(Math.max(0, fa - 96));\n'
            '    S.playing = true; tickLoop(); };')


def main():
    src = open(PATH, encoding="utf-8").read()
    n = src.count(OLD_WIRE)
    if n != 1:
        print("SKIP: click-handler not found exactly once (found " +
              str(n) + "). Tell the chat.")
        return
    src = src.replace(OLD_WIRE, NEW_WIRE)
    with open(PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(src)
    print("OK  stop-branch added to button handler")
    print("saved (" + str(len(src)) + " chars)")
    print("NOW: browser -> Ctrl+Shift+R")


if __name__ == "__main__":
    main()