#!/usr/bin/env python3
# fix_chart.py - 1-decimal tiles; pressure chart shows ONLY selected district.
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


# 1) tiles: one decimal
rep('    pv.textContent = (v === null ? "n/a" : v + " m");',
    '    pv.textContent = (v === null ? "n/a" : v.toFixed(1) + " m");',
    "tile 1-decimal format")

# 2) pressure chart: only the selected district
rep('  var psets = S.data.meta.sensors.map(function(s, j){\n'
    '    var pd = (d.pressures && d.pressures["pressure_" + s.id])\n'
    '      || [];\n'
    '    return { label:zoneName(s.id),\n'
    '      data: pd.map(function(y, x){ return { x:x, y:y }; }),\n'
    '      borderColor: pal[j % pal.length],\n'
    '      borderWidth: s.id === S.sel ? 2.6 : 1.4,\n'
    '      pointRadius:0, tension:.1,\n'
    '      alpha: s.id === S.sel ? 1 : .5 }); });',
    '  var psets = S.data.meta.sensors.filter(function(s){\n'
    '      return s.id === S.sel; }).map(function(s){\n'
    '    var pd = (d.pressures && d.pressures["pressure_" + s.id])\n'
    '      || [];\n'
    '    return { label:zoneName(s.id),\n'
    '      data: pd.map(function(y, x){ return { x:x, y:y }; }),\n'
    '      borderColor: "#0b6e99",\n'
    '      borderWidth: 2.4,\n'
    '      pointRadius:0, tension:.1 }); });',
    "chart shows only selected district")

# 3) clicking a district rebuilds the chart with only that line
rep('function selectSensor(id){\n'
    '  S.sel = id;\n'
    '  if(S.charts[1]){\n'
    '    S.charts[1].data.datasets.forEach(function(ds){\n'
    '      if(ds.label === "TwinAlert"){\n'
    '        ds.data = alertMarkerData(); return;\n'
    '      }\n'
    '      var on = ds.label === zoneName(id);\n'
    '      ds.borderWidth = on ? 2.6 : 1.4;\n'
    '      ds.alpha = on ? 1 : .5;\n'
    '    });\n'
    '    S.charts[1].update("none");\n'
    '  }',
    'function selectSensor(id){\n'
    '  S.sel = id;\n'
    '  S.charts.forEach(function(c){ c.destroy(); });\n'
    '  S.charts = [];\n'
    '  buildCharts();',
    "selectSensor rebuilds single-line chart")

# 4) heading matches behavior
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