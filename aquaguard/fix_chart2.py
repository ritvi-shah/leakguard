#!/usr/bin/env python3
# fix_chart2.py - anchor+brace-based replacement (no exact-text guessing).
# Tiles 1-decimal; pressure chart shows ONLY the selected district.
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(ROOT, "dashboard", "templates", "index.html")

src = open(PATH, encoding="utf-8").read()
fails = []


def find_braced_block(text, start_marker):
    """Return (start, end) of the braced block whose header starts at
    start_marker; end is index after the matching closing brace."""
    i = text.find(start_marker)
    if i == -1:
        return None
    j = text.find("{", i)
    if j == -1:
        return None
    depth = 0
    k = j
    in_str = None
    while k < len(text):
        ch = text[k]
        if in_str:
            if ch == "\\":
                k += 2
                continue
            if ch == in_str:
                in_str = None
        else:
            if ch in ('"', "'"):
                in_str = ch
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return (i, k + 1)
        k += 1
    return None


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


# 1) tiles one decimal (tolerant: may already be applied)
rep('pv.textContent = (v === null ? "n/a" : v + " m");',
    'pv.textContent = (v === null ? "n/a" : v.toFixed(1) + " m");',
    "tile 1-decimal")

# 2) replace the psets segment: from 'var psets' to 'var press = new Chart'
p_start = src.find("var psets =")
p_end = src.find("var press = new Chart")
if p_start == -1 or p_end == -1 or p_end <= p_start:
    print("FAIL psets segment not found")
    fails.append("psets segment")
else:
    NEW_PSETS = (
        'var psets = S.data.meta.sensors.filter(function(s){\n'
        '      return s.id === S.sel; }).map(function(s){\n'
        '    var pd = (d.pressures && d.pressures["pressure_" + s.id])\n'
        '      || [];\n'
        '    return { label:zoneName(s.id),\n'
        '      data: pd.map(function(y, x){ return { x:x, y:y }; }),\n'
        '      borderColor: "#0b6e99",\n'
        '      borderWidth: 2.4,\n'
        '      pointRadius:0, tension:.1 }; });\n'
        '  ')
    src = src[:p_start] + NEW_PSETS + src[p_end:]
    print("OK   psets -> single selected district")

# 3) replace the whole selectSensor function (brace-aware)
blk = find_braced_block(src, "function selectSensor(id){")
if blk is None:
    print("FAIL selectSensor block not found")
    fails.append("selectSensor block")
else:
    NEW_FN = (
        'function selectSensor(id){\n'
        '  S.sel = id;\n'
        '  S.charts.forEach(function(c){ c.destroy(); });\n'
        '  S.charts = [];\n'
        '  buildCharts();\n'
        '  S.data.meta.sensors.forEach(function(s){\n'
        '    var t = $("tile_" + s.id);\n'
        '    if(t) t.classList.toggle("sel", s.id === id);\n'
        '  });\n'
        '}')
    src = src[:blk[0]] + NEW_FN + src[blk[1]:]
    print("OK   selectSensor rebuilt (rebuilds single-line chart)")

# 4) heading
rep('<h2 class="sect">Pressure in the six districts</h2>',
    '<h2 class="sect">Pressure - selected district</h2>',
    "chart heading")

# 5) integrity gate
js_all = src[src.find("<script>\n") + 9: src.rfind("</script>")]
checks = [
    ("js braces balanced", js_all.count("{") == js_all.count("}")),
    ("js parens balanced", js_all.count("(") == js_all.count(")")),
    ("js double quotes even", js_all.count('"') % 2 == 0),
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