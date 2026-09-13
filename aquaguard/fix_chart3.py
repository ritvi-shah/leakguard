#!/usr/bin/env python3
# fix_chart3.py - Charts: all districts by default, single focus on click,
# red alert dots restored (per-district in "all" view), Show-all button.
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(ROOT, "dashboard", "templates", "index.html")

src = open(PATH, encoding="utf-8").read()
fails = []


def find_braced_block(text, start_marker):
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


# 1) state: add chartMode
rep("exp:null, why:null };",
    "exp:null, why:null, chartMode:\"all\" };",
    "chartMode in state")

# 2) rebuild buildCharts entirely (brace-aware)
blk = find_braced_block(src, "function buildCharts(){")
if blk is None:
    print("FAIL buildCharts not found")
    fails.append("buildCharts")
else:
    NEW = (
        'function buildCharts(){\n'
        '  var d = S.d.series, N = d.times.length;\n'
        '  var pal = ["#0b6e99","#177245","#b3261e",\n'
        '    "#6d5bb8","#c07a1a","#0e8f8f"];\n'
        '  var flowData = (d.source_flow_Ls || []).map(function(y, x){\n'
        '    return { x:x, y:y }; });\n'
        '  var thrData = (d.source_flow_Ls || []).map(function(_, x){\n'
        '    return { x:x, y:d.mnf_threshold }; });\n'
        '  var flow = new Chart($("flowChart"), { type:"line",\n'
        '    data:{ datasets:[\n'
        '      { label:"Flow (L/s)", data:flowData,\n'
        '        borderColor:"#0b6e99", borderWidth:2,\n'
        '        pointRadius:0, tension:.12 },\n'
        '      { label:"Night alert line", data:thrData,\n'
        '        borderColor:"#c07a1a", borderDash:[7,5],\n'
        '        borderWidth:1.6, pointRadius:0 } ] },\n'
        '    options:{ animation:false, maintainAspectRatio:false,\n'
        '      scales:{ x:xScale(N),\n'
        '        y:{ title:{ display:true, text:"L/s" } } },\n'
        '      plugins:{ shade:{ on:!!S.d.leak_node,\n'
        '        from:leakStartIdx() },\n'
        '        legend:{ labels:{ boxWidth:12, font:{ size:11 } } } } },\n'
        '    plugins:[marker, shade] });\n'
        '  var psets = [];\n'
        '  if(S.chartMode === "single"){\n'
        '    S.data.meta.sensors.forEach(function(s){\n'
        '      if(s.id !== S.sel) return;\n'
        '      var pd = (d.pressures && d.pressures["pressure_" + s.id])\n'
        '        || [];\n'
        '      psets.push({ label:zoneName(s.id),\n'
        '        data: pd.map(function(y, x){ return { x:x, y:y }; }),\n'
        '        borderColor:"#0b6e99", borderWidth:2.4,\n'
        '        pointRadius:0, tension:.1 }); });\n'
        '    psets.push({ label:"Alerts", data:alertMarkerData(),\n'
        '      showLine:false, pointRadius:3.5,\n'
        '      pointBackgroundColor:"rgba(179,38,30,.9)",\n'
        '      pointBorderColor:"#fff", pointBorderWidth:.5 });\n'
        '  } else {\n'
        '    S.data.meta.sensors.forEach(function(s, j){\n'
        '      var pd = (d.pressures && d.pressures["pressure_" + s.id])\n'
        '        || [];\n'
        '      psets.push({ label:zoneName(s.id),\n'
        '        data: pd.map(function(y, x){ return { x:x, y:y }; }),\n'
        '        borderColor: pal[j % pal.length], borderWidth:1.6,\n'
        '        pointRadius:0, tension:.1, alpha:.85 }); });\n'
        '    S.data.meta.sensors.forEach(function(s){\n'
        '      var pts = [];\n'
        '      S.d.series.twin_flag.forEach(function(f, i){\n'
        '        if(f){\n'
        '          var y = pressAt(s.id, i);\n'
        '          if(y !== null) pts.push({ x:i, y:y }); } });\n'
        '      if(pts.length){\n'
        '        psets.push({ label:"Alerts-" + zoneName(s.id),\n'
        '          data:pts, showLine:false, pointRadius:2.6,\n'
        '          pointBackgroundColor:"rgba(179,38,30,.75)",\n'
        '          pointBorderColor:"#fff", pointBorderWidth:.4 }); }\n'
        '    });\n'
        '  }\n'
        '  var press = new Chart($("pChart"), { type:"line",\n'
        '    data:{ datasets:psets },\n'
        '    options:{ animation:false, maintainAspectRatio:false,\n'
        '      scales:{ x:xScale(N),\n'
        '        y:{ title:{ display:true, text:"pressure (m)" } } },\n'
        '      plugins:{ shade:{ on:!!S.d.leak_node,\n'
        '        from:leakStartIdx() },\n'
        '        legend:{ labels:{ boxWidth:12, font:{ size:10 },\n'
        '          filter:function(ds){\n'
        '            return ds.label.indexOf("Alerts") !== 0; } } } } },\n'
        '    plugins:[marker, shade] });\n'
        '  var ab = $("allBtn");\n'
        '  if(ab) ab.hidden = (S.chartMode !== "single");\n'
        '  S.charts = [flow, press];\n'
        '}'
    )
    src = src[:blk[0]] + NEW + src[blk[1]:]
    print("OK   buildCharts rebuilt (two modes + alert dots)")

# 3) selectSensor -> single mode
blk = find_braced_block(src, "function selectSensor(id){")
if blk is None:
    print("FAIL selectSensor not found")
    fails.append("selectSensor")
else:
    NEW = (
        'function selectSensor(id){\n'
        '  S.sel = id;\n'
        '  S.chartMode = "single";\n'
        '  S.charts.forEach(function(c){ c.destroy(); });\n'
        '  S.charts = [];\n'
        '  buildCharts();\n'
        '  S.data.meta.sensors.forEach(function(s){\n'
        '    var t = $("tile_" + s.id);\n'
        '    if(t) t.classList.toggle("sel", s.id === id);\n'
        '  });\n'
        '}'
    )
    src = src[:blk[0]] + NEW + src[blk[1]:]
    print("OK   selectSensor -> single mode")

# 4) showAll function (insert before downloadReport)
if "function showAllDistricts(){" not in src:
    rep("function downloadReport(){",
        'function showAllDistricts(){\n'
        '  S.chartMode = "all";\n'
        '  S.charts.forEach(function(c){ c.destroy(); });\n'
        '  S.charts = [];\n'
        '  buildCharts();\n'
        '}\n'
        'function downloadReport(){',
        "showAll function")

# 5) wire the button
rep('  $("dlBtn").onclick = function(){',
    '  $("allBtn").onclick = showAllDistricts;\n'
    '  $("dlBtn").onclick = function(){',
    "allBtn wired")

# 6) heading + hint + button (index-based, tolerant of prior edits)
h = src.find('<h2 class="sect">Pressure')
if h == -1:
    print("FAIL pressure heading not found")
    fails.append("heading")
else:
    p_end = src.find("</p>", h)
    if p_end == -1:
        print("FAIL hint paragraph not found")
        fails.append("hint")
    else:
        p_end += 4
        NEWH = ('<h2 class="sect">Pressure in the districts</h2>\n'
                '<p class="secthint">All six districts are shown together. '
                'Red dots mark moments the model flagged. To focus on one '
                'district, click its card on the Overview tab (or its dot '
                'on the map).</p>\n'
                '<button id="allBtn" class="dlbtn" hidden>'
                'Show all districts</button>\n')
        src = src[:h] + NEWH + src[p_end:]
        print("OK   heading + hint + Show-all button")

# 7) integrity gate
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