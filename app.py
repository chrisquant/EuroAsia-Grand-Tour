#!/usr/bin/env python3
"""欧亚自驾规划可视化。分页方式对齐 Tokyo-A 集群门户：侧栏 st.navigation + 指标 + Plotly。"""

import importlib
import json
import math
from datetime import date, timedelta
from html import escape

import folium
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import trip_data as td

td = importlib.reload(td)

TRIP_START = date(2030, 3, 1)
TRIP_END = date(2030, 9, 16)
LATE_NAMES = {"伊宁", "霍尔果斯", "扎门乌德"}
OVERVIEW_ZOOM2 = {"伊宁", "霍尔果斯", "扎门乌德", "安卡拉", "伊兹密尔", "波尔图"}
OVERVIEW_ZOOM3 = {"弗拉季高加索", "特拉布宗", "卢布尔雅那", "萨格勒布", "加来", "湖区", "塞济斯菲厄泽", "奇姆肯特", "塔拉兹", "布哈拉"}
KM_NOTE = "城市间里程是规划估算，按全程约 3.4 万公里缩放，不是实测轨迹。"


def _mercator_mid(a, b):
    """墨卡托直线的中点和屏幕方向。Leaflet 的线段是这条直线，箭头要落在上面。"""
    def xy(lat, lon):
        lat = max(min(lat, 85.0), -85.0)
        x = math.radians(lon)
        y = math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
        return x, y
    x1, y1 = xy(a["lat"], a["lon"])
    x2, y2 = xy(b["lat"], b["lon"])
    x, y = (x1 + x2) / 2, (y1 + y2) / 2
    lon = math.degrees(x)
    lat = math.degrees(2 * math.atan(math.exp(y)) - math.pi / 2)
    bearing = (math.degrees(math.atan2(x2 - x1, y2 - y1)) + 360) % 360
    return lat, lon, bearing


def _overview_arrow(m, a, b):
    lat, lon, bearing = _mercator_mid(a, b)
    deg = bearing - 90
    html = (
        '<div class="route-arrow route-arrow-hidden">'
        '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24">'
        f'<g transform="rotate({deg:.0f} 12 12)">'
        '<polygon points="9,8 16,12 9,16" fill="#E2C7A0"/></g></svg></div>'
    )
    folium.Marker(
        [lat, lon],
        icon=folium.DivIcon(icon_size=(14, 14), icon_anchor=(7, 7), html=html),
    ).add_to(m)


def _overview_name(name, shift, color, tier=0):
    klass = {
        2: ' class="late-label late-hidden"',
        3: ' class="mid-label mid-hidden"',
        4: ' class="via-label via-hidden"',
    }.get(tier, "")
    return (
        f'<div{klass} style="transform:{shift};white-space:nowrap;text-align:center;'
        f"color:{color};background:rgba(22,27,34,0.82);padding:1px 5px;border-radius:4px;"
        f'font-size:11px;line-height:1.25;font-family:sans-serif;">{escape(name)}</div>'
    )


def figure_overview_map(day):
    cities = td.flat_cities()
    line = td.route_vertices(cities)
    pos = td.track_on(day)
    m = folium.Map(
        location=[48, 50],
        zoom_start=2,
        tiles=None,
        zoom_control=True,
        scrollWheelZoom=True,
        width="100%",
        height="650px",
    )
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
        attr="Esri, USGS, NOAA",
        name="base",
        control=False,
    ).add_to(m)
    m.get_root().header.add_child(folium.Element(
        "<style>html,body{background:#1B2430!important;margin:0;padding:0;height:100%}"
        ".folium-map{height:100%!important;background:#1B2430}"
        ".leaflet-container{background:#1B2430}"
        ".leaflet-div-icon{background:transparent;border:none}"
        ".leaflet-control-attribution{background:rgba(22,27,34,.8)!important;color:#c8c2b8!important}"
        ".leaflet-control-attribution a{color:#e2c7a0!important}"
        ".map-reset{display:block;margin-top:8px;height:30px;padding:0 8px;background:#fff;color:#333;"
        "border:2px solid rgba(0,0,0,.2);border-radius:4px;cursor:pointer;font:12px/26px sans-serif}"
        ".map-reset:hover{background:#f4f4f4}"
        ".map-full{height:30px;padding:0 8px;background:#fff;color:#333;border:2px solid rgba(0,0,0,.2);border-radius:4px;cursor:pointer;font:12px/26px sans-serif}"
        ".map-full:hover{background:#f4f4f4}"
        ".via-label.via-hidden,.mid-label.mid-hidden,.late-label.late-hidden,.route-arrow.route-arrow-hidden{display:none}"
        ".ov-legend{background:rgba(22,27,34,.78);color:#F2EFE9;padding:6px 8px;border-radius:4px;"
        "font:12px/1.7 sans-serif;margin:0 0 8px 8px}"
        ".ov-swatch{display:inline-block;width:16px;height:3px;background:#E2C7A0;margin-right:6px;vertical-align:middle}"
        ".ov-dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;vertical-align:middle}"
        "</style>"
    ))
    folium.PolyLine(
        [(p["lat"], p["lon"]) for p in line],
        color="#E2C7A0", weight=2.5, opacity=0.95,
    ).add_to(m)
    for a, b in zip(line, line[1:]):
        if (a["lat"], a["lon"]) != (b["lat"], b["lon"]):
            _overview_arrow(m, a, b)
    for i, c in enumerate(cities):
        been = c["arrive"] <= day
        folium.CircleMarker(
            [c["lat"], c["lon"]],
            radius=6 if been else 4,
            color="#F2EFE9" if been else "#C8C2B8",
            weight=1,
            fill=True,
            fill_color=c["color"] if been else "#5C6570",
            fill_opacity=0.95,
            tooltip=c["name"],
        ).add_to(m)
        folium.Marker(
            [c["lat"], c["lon"]],
            icon=folium.DivIcon(
                icon_size=(0, 0), icon_anchor=(0, 0),
                html=_overview_name(
                    c["name"], _LABEL_SHIFT[i % len(_LABEL_SHIFT)],
                    "#F2EFE9" if been else "#C8C2B8",
                    tier=2 if c["name"] in OVERVIEW_ZOOM2 else 3 if c["name"] in OVERVIEW_ZOOM3 else 0,
                ),
            ),
        ).add_to(m)
    for j, c in enumerate(td.ZOOM_LABELS):
        if c["name"] == "嘉峪关":
            reached = next(city for city in cities if city["name"] == "乌鲁木齐")
            tone = "#F2EFE9" if reached["arrive"] <= day else "#C8C2B8"
            tier = 0
        else:
            tone, tier = "#F2EFE9", 4
        folium.Marker(
            [c["lat"], c["lon"]],
            icon=folium.DivIcon(
                icon_size=(0, 0), icon_anchor=(0, 0),
                html=_overview_name(c["name"], _LABEL_SHIFT[(j + 2) % len(_LABEL_SHIFT)], tone, tier=tier),
            ),
        ).add_to(m)
    star = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">'
        '<polygon points="8,1 10,6 15,6.4 11.2,9.6 12.4,14.6 8,12 3.6,14.6 4.8,9.6 1,6.4 6,6" '
        'fill="#F5C16C" stroke="#161B22" stroke-width="0.6"/></svg>'
    )
    folium.Marker(
        [pos["lat"], pos["lon"]],
        tooltip=f"{pos['name']} · {pos['country']}",
        icon=folium.DivIcon(icon_size=(16, 16), icon_anchor=(8, 8), html=star),
    ).add_to(m)
    script = (
        "<script>(function(){var map=" + m.get_name() + ";"
        "var home=[[18,-20],[79,126]];"
        "map.fitBounds(home,{padding:[8,8],animate:false});"
        "var homeZoom=map.getZoom()+1;"
        "map.setView([43.83,87.62],homeZoom,{animate:false});"
        "var baseZoom=homeZoom;"
        "var saved=null;try{saved=JSON.parse(localStorage.getItem('eurasia-overview-v2'));}catch(e){}"
        "if(saved&&typeof saved.zoom==='number'){map.setView([saved.lat,saved.lon],saved.zoom,{animate:false});}"
        "function syncZoom(){var z=map.getZoom();var show=z>=baseZoom+1;var showLate=z>=baseZoom+2;var showMid=z>=baseZoom+3;var showVia=z>=baseZoom+4;"
        "map.getContainer().querySelectorAll('.via-label').forEach(function(el){el.classList.toggle('via-hidden',!showVia);});"
        "map.getContainer().querySelectorAll('.mid-label').forEach(function(el){el.classList.toggle('mid-hidden',!showMid);});"
        "map.getContainer().querySelectorAll('.late-label').forEach(function(el){el.classList.toggle('late-hidden',!showLate);});"
        "map.getContainer().querySelectorAll('.route-arrow').forEach(function(el){el.classList.toggle('route-arrow-hidden',!show);});}"
        "map.on('zoomend',syncZoom);"
        "map.on('moveend',function(){try{var c=map.getCenter();"
        "localStorage.setItem('eurasia-overview-v2',JSON.stringify({lat:c.lat,lon:c.lng,zoom:map.getZoom()}));}catch(err){}});"
        "syncZoom();"
        "var Reset=L.Control.extend({options:{position:'topleft'},onAdd:function(){"
        "var btn=L.DomUtil.create('button','map-reset');btn.type='button';btn.title='回到最初范围';btn.textContent='复位';"
        "L.DomEvent.disableClickPropagation(btn);"
        "L.DomEvent.on(btn,'click',function(e){L.DomEvent.stop(e);try{localStorage.removeItem('eurasia-overview-v2');}catch(err){}"
        "map.setView([43.83,87.62],homeZoom,{animate:false});});return btn;}});"
        "map.addControl(new Reset());"
        "var Legend=L.Control.extend({options:{position:'bottomleft'},onAdd:function(){"
        "var d=L.DomUtil.create('div','ov-legend');"
        "d.innerHTML='<div><span class=\"ov-swatch\"></span>环线</div>"
        "<div><span class=\"ov-dot\" style=\"background:#C45C26\"></span>已经过</div>"
        "<div><span class=\"ov-dot\" style=\"background:#5C6570\"></span>未到</div>"
        "<div><span style=\"color:#F5C16C\">★</span> 当天</div>';"
        "return d;}});map.addControl(new Legend());" + _fullscreen_control_js() + "})();</script>"
    )
    return m.get_root().render() + script


def _fullscreen_control_js():
    return (
        "var Full=L.Control.extend({options:{position:'topright'},onAdd:function(){"
        "var btn=L.DomUtil.create('button','map-full');btn.type='button';btn.title='看大图';btn.textContent='全屏';"
        "L.DomEvent.disableClickPropagation(btn);"
        "L.DomEvent.on(btn,'click',function(e){L.DomEvent.stop(e);window.parent.postMessage({type:'eurasia-fullscreen'},'*');});"
        "window.addEventListener('message',function(ev){if(!ev.data||ev.data.type!=='eurasia-fullscreen-state')return;"
        "btn.textContent=ev.data.on?'退出':'全屏';setTimeout(function(){map.invalidateSize();},200);});"
        "return btn;}});map.addControl(new Full);"
        "window.addEventListener('resize',function(){map.invalidateSize();});"
    )


def _fullscreen_host():
    st.html(
        """
<script>
(function(){
  if (window.__eurasiaFs) return;
  window.__eurasiaFs = true;
  function tell(iframe){
    var on = document.fullscreenElement === iframe;
    try { iframe.contentWindow.postMessage({type:'eurasia-fullscreen-state', on:on}, '*'); } catch (err) {}
  }
  window.addEventListener('message', function(e){
    if (!e.data || e.data.type !== 'eurasia-fullscreen') return;
    var iframe = null;
    document.querySelectorAll('iframe').forEach(function(f){ if (f.contentWindow === e.source) iframe = f; });
    if (!iframe) return;
    var req = iframe.requestFullscreen || iframe.webkitRequestFullscreen;
    var done = function(){ tell(iframe); };
    if (document.fullscreenElement === iframe) document.exitFullscreen().then(done).catch(done);
    else if (req) req.call(iframe).then(done).catch(done);
  });
  document.addEventListener('fullscreenchange', function(){
    document.querySelectorAll('iframe').forEach(tell);
  });
})();
</script>
""",
        unsafe_allow_javascript=True,
    )


def _stamp_days(points):
    stays = [p for p in points if p["role"] == "stay" and p.get("arrive")]
    for i, p in enumerate(stays):
        if p.get("until"):
            end = p["until"]
        elif i + 1 < len(stays):
            end = stays[i + 1]["arrive"]
        else:
            end = p["arrive"]
        p["days"] = max((end - p["arrive"]).days, 1)


_LABEL_SHIFT = (
    "translate(-50%,-140%)",
    "translate(6px,-50%)",
    "translate(-106%,-50%)",
    "translate(-50%,8px)",
)


def _map_label(point, shift):
    klass = "late-label late-hidden" if point["name"] in LATE_NAMES else ""
    if point["role"] == "stay" and point.get("arrive"):
        text = f"{point['name']}<br>{point['arrive'].month}月{point['arrive'].day}日 · {point['days']}天"
        size = "12px"
    else:
        edge = {"in": "入境前", "out": "出境后", "both": "入境前 / 出境后"}.get(point.get("edge") or "")
        text = f"{point['name']}<br><span style='opacity:.85'>{edge}</span>" if edge else point["name"]
        size = "12px" if point["name"] == "嘉峪关" else "11px"
        if not klass and point.get("via"):
            klass = "via-label via-hidden"
    return (
        f'<div class="{klass}" style="transform:{shift};white-space:nowrap;text-align:center;'
        "color:#F2EFE9;background:rgba(22,27,34,0.82);padding:2px 6px;border-radius:4px;"
        f'font-size:{size};line-height:1.25;font-family:sans-serif;">{text}</div>'
    )


def _bearing(a, b):
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def _arrow(m, a, b, color):
    lat = (a[0] + b[0]) / 2
    lon = (a[1] + b[1]) / 2
    deg = _bearing(a, b) - 90
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">'
        f'<g transform="rotate({deg:.0f} 12 12)">'
        f'<polygon points="9,7 18,12 9,17" fill="{color}"/></g></svg>'
    )
    folium.Marker(
        [lat, lon],
        icon=folium.DivIcon(icon_size=(24, 24), icon_anchor=(12, 12), html=svg),
    ).add_to(m)


def _nearest_near(pts, start, step):
    i = start
    while 0 <= i < len(pts):
        if pts[i]["role"] == "near":
            return pts[i]
        if pts[i]["role"] != "pass":
            return None
        i += step
    return None


def _mark_edges(legs):
    for n, leg in enumerate(legs):
        pts = leg["points"]
        stays = [i for i, p in enumerate(pts) if p["role"] == "stay"]
        if not stays:
            continue
        prev = _nearest_near(pts, stays[0] - 1, -1)
        if prev is not None:
            prev["edge"] = "in"
        nxt = _nearest_near(pts, stays[-1] + 1, 1)
        if nxt is not None:
            nxt["edge"] = "out"
            continue
        for later in legs[n + 1:]:
            hit = next((p for p in later["points"] if p["role"] == "near"), None)
            if any(p["role"] == "stay" for p in later["points"]):
                break
            if hit is not None:
                hit["edge"] = "out"
                break


def figure_country_map(country):
    legs = td.MAP_LEGS[country["id"]]
    color = td.COUNTRY_COLORS[country["id"]]
    first = legs[0]["points"][0]
    # Carto dark_all 现在没有 key 只返回占位图。Esri 深色底图能看到海岸和国界。
    m = folium.Map(
        location=[first["lat"], first["lon"]],
        zoom_start=5,
        tiles=None,
        zoom_control=True,
        scrollWheelZoom=True,
        width="100%",
        height="650px",
    )
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
        attr="Esri, USGS, NOAA",
        name="base",
        control=False,
    ).add_to(m)
    m.get_root().header.add_child(folium.Element(
        "<style>html,body{background:#1B2430!important;margin:0;padding:0;height:100%}"
        ".folium-map{height:100%!important;background:#1B2430}"
        ".leaflet-container{background:#1B2430}"
        ".leaflet-div-icon{background:transparent;border:none}"
        ".leaflet-control-attribution{background:rgba(22,27,34,.8)!important;color:#c8c2b8!important}"
        ".leaflet-control-attribution a{color:#e2c7a0!important}"
        ".map-reset{display:block;margin-top:8px;height:30px;padding:0 8px;background:#fff;color:#333;"
        "border:2px solid rgba(0,0,0,.2);border-radius:4px;cursor:pointer;font:12px/26px sans-serif}"
        ".map-reset:hover{background:#f4f4f4}"
        ".map-full{height:30px;padding:0 8px;background:#fff;color:#333;border:2px solid rgba(0,0,0,.2);border-radius:4px;cursor:pointer;font:12px/26px sans-serif}"
        ".map-full:hover{background:#f4f4f4}"
        ".city-card{position:absolute;z-index:800;top:12px;right:12px;width:min(380px,calc(100% - 70px));"
        "max-height:calc(100% - 24px);overflow:auto;background:#161B22;color:#F2EFE9;"
        "border:1px solid #3A4250;border-radius:8px;padding:12px 14px;box-shadow:0 8px 24px rgba(0,0,0,.35);"
        "font:14px/1.65 sans-serif}"
        ".city-card-head{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:8px}"
        ".city-card-head b{font-size:16px}"
        ".city-card-close{background:#343B46;color:#F2EFE9;border:none;border-radius:4px;padding:2px 8px;cursor:pointer}"
        ".via-label.via-hidden,.late-label.late-hidden{display:none}"
        "</style>"
    ))
    _mark_edges(legs)
    edge_at = {}
    for leg in legs:
        for p in leg["points"]:
            if p.get("edge"):
                spot = (round(p["lat"], 2), round(p["lon"], 2))
                edge_at.setdefault(spot, set()).add(p["edge"])
    for leg in legs:
        _stamp_days(leg["points"])
    best_days = {}
    for leg in legs:
        for p in leg["points"]:
            if p["role"] == "stay" and p.get("arrive") and p.get("days"):
                key = (p["name"], p["arrive"])
                best_days[key] = max(p["days"], best_days.get(key, 0))
    for leg in legs:
        for p in leg["points"]:
            key = (p["name"], p.get("arrive"))
            if key in best_days:
                p["days"] = best_days[key]
    seen = set()
    coords = []
    clickables = []
    for leg in legs:
        pts = leg["points"]
        latlon = [(p["lat"], p["lon"]) for p in pts]
        coords.extend(latlon)
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            pair = [(a["lat"], a["lon"]), (b["lat"], b["lon"])]
            if leg["kind"] == "ferry":
                folium.PolyLine(
                    pair, color="#E2C7A0", weight=3, opacity=0.9, dash_array="8 8",
                    tooltip=f"渡轮 · {a['name']} → {b['name']}",
                ).add_to(m)
                _arrow(m, pair[0], pair[1], "#E2C7A0")
            elif a["role"] == "near" or b["role"] == "near" or a.get("foreign") or b.get("foreign") or a.get("gate") or b.get("gate"):
                folium.PolyLine(
                    pair, color="#9AA3AE", weight=2.5, opacity=0.8, dash_array="6 8",
                    tooltip=f"出入境 · {a['name']} → {b['name']}",
                ).add_to(m)
                _arrow(m, pair[0], pair[1], "#9AA3AE")
            elif leg["kind"] == "road":
                folium.PolyLine(pair, color=color, weight=3, opacity=0.95).add_to(m)
                _arrow(m, pair[0], pair[1], color)
        for p in pts:
            spot = (round(p["lat"], 2), round(p["lon"], 2))
            if p["role"] != "stay" and any(s == spot and not isinstance(tag, str) for s, tag in seen):
                continue
            key = (spot, p.get("arrive") if p["role"] == "stay" else p["role"])
            if key in seen:
                continue
            seen.add(key)
            circle = None
            if spot not in {s for s, _ in seen - {key}}:
                stay = p["role"] == "stay" or p["name"] == "嘉峪关"
                circle = folium.CircleMarker(
                    [p["lat"], p["lon"]],
                    radius=7 if stay else 5,
                    color="#F2EFE9",
                    weight=1,
                    fill=True,
                    fill_color=color if stay else "#8B939E",
                    fill_opacity=0.95,
                )
                circle.add_to(m)
            tags = edge_at.get(spot) or set()
            if tags == {"in", "out"}:
                p["edge"] = "both"
            elif tags:
                p["edge"] = next(iter(tags))
            nth = sum(1 for s, _ in seen if s == spot)
            shift = _LABEL_SHIFT[(len(seen) + nth) % len(_LABEL_SHIFT)]
            label = folium.Marker(
                [p["lat"], p["lon"]],
                icon=folium.DivIcon(icon_size=(0, 0), icon_anchor=(0, 0), html=_map_label(p, shift)),
            )
            label.add_to(m)
            if p["role"] == "stay":
                text = td.CITY_BLURBS.get(p["name"]) or next((s["note"] for s in td.STOPS if s["name"] == p["name"]), "")
                money = td.spend_plan()["city"].get((p["name"], p.get("arrive")))
                if money:
                    text = f"停留 {money['days']} 天，食宿、燃油和路桥停车大约 {money['yuan']:,} 元。" + text
                if text:
                    handles = [label.get_name()]
                    if circle is not None:
                        handles.append(circle.get_name())
                    clickables.append((handles, p["name"], text))
    if len(coords) >= 2:
        max_zoom = 7 if len(set(coords)) <= 2 else None
        m.fit_bounds(coords, padding=(70, 70), max_zoom=max_zoom)
    else:
        max_zoom = None
    home = ",".join(f"[{lat},{lon}]" for lat, lon in coords)
    zoom_opt = "opts.maxZoom=7;" if max_zoom == 7 else ""
    script = (
        f"<script>(function(){{var map={m.get_name()};var home=[{home}];"
        "var Reset=L.Control.extend({options:{position:'topleft'},onAdd:function(){"
        "var btn=L.DomUtil.create('button','map-reset');btn.type='button';"
        "btn.title='回到最初范围';btn.textContent='复位';"
        "L.DomEvent.disableClickPropagation(btn);"
        "L.DomEvent.on(btn,'click',function(e){L.DomEvent.stop(e);"
        "if(home.length>=2){var opts={padding:[70,70],animate:false};" + zoom_opt + "map.fitBounds(home,opts);}"
        "else if(home.length===1){map.setView(home[0],5);}});"
        "return btn;}});map.addControl(new Reset());"
        "var baseZoom=map.getZoom();"
        "function syncVia(){var show=map.getZoom()>=baseZoom+1;var showLate=map.getZoom()>=baseZoom+2;"
        "map.getContainer().querySelectorAll('.via-label').forEach(function(el){el.classList.toggle('via-hidden',!show);});"
        "map.getContainer().querySelectorAll('.late-label').forEach(function(el){el.classList.toggle('late-hidden',!showLate);});}"
        "map.on('zoomend',syncVia);syncVia();" + _fullscreen_control_js() + "})();</script>"
    )
    return m.get_root().render() + script + _city_card_script(m, clickables)


def _city_card_script(m, clickables):
    if not clickables:
        return ""
    binds = []
    for handles, name, text in clickables:
        card = (
            "<div class='city-card-head'><b>" + escape(name) + "</b>"
            "<button type='button' class='city-card-close'>收起</button></div>"
            "<div class='city-card-body'>" + escape(text) + "</div>"
        )
        targets = ",".join(handles)
        binds.append(
            f"[{targets}].forEach(function(layer){{layer.on('click',function(e){{"
            f"L.DomEvent.stopPropagation(e);toggle({json.dumps(name, ensure_ascii=False)},{json.dumps(card, ensure_ascii=False)});}});}});"
        )
    return (
        "<script>(function(){var map=" + m.get_name() + ";var current=null;var card=null;"
        "function hide(){if(card)card.style.display='none';current=null;}"
        "function toggle(name,html){"
        "if(!card){card=L.DomUtil.create('div','city-card',map.getContainer());"
        "L.DomEvent.disableClickPropagation(card);L.DomEvent.disableScrollPropagation(card);}"
        "if(current===name&&card.style.display!=='none'){hide();return;}"
        "card.innerHTML=html;card.style.display='block';current=name;"
        "var btn=card.querySelector('.city-card-close');"
        "if(btn)L.DomEvent.on(btn,'click',function(e){L.DomEvent.stop(e);hide();});"
        "}" + "".join(binds) + "})();</script>"
    )


def _map_caption(country):
    """只说明这张图上真的画出来的线，没有的线不写。"""
    legs = td.MAP_LEGS[country["id"]]
    stay = solid = border = ferry = False
    for leg in legs:
        pts = leg["points"]
        if any(p["role"] == "stay" and p.get("arrive") for p in pts):
            stay = True
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            if leg["kind"] == "ferry":
                ferry = True
            elif a["role"] == "near" or b["role"] == "near" or a.get("foreign") or b.get("foreign") or a.get("gate") or b.get("gate"):
                border = True
            elif leg["kind"] == "road":
                solid = True
    parts = []
    if stay:
        parts.append("停留点上方写着到达日期和停留天数。")
    if solid or border or ferry:
        parts.append("箭头表示往哪个方向开。")
    if country["id"] == "fr" and (solid or border):
        parts.append("淡色虚线是入境法国之前和离开法国之后的公路，实线是进入法国之后的公路。途经城市默认只留圆点，放大地图后才写出名字。")
    else:
        if solid:
            parts.append("实线是这个国家里的公路。")
        if border:
            parts.append("淡色虚线连到入境前和出境后的城市。")
    if ferry:
        parts.append("浅金色虚线是渡轮。")
    if not parts and country["id"] == "az":
        parts.append("巴库和占贾只标位置，中间不画路线。")
    return "".join(parts)


def _timeline(rows, y_col, height):
    df = pd.DataFrame(rows)
    hover = [c for c in ("说明", "天数", "截止", "验收") if c in df.columns]
    fig = px.timeline(df, x_start="开始", x_end="结束", y=y_col, color=y_col, hover_data=hover)
    fig.update_yaxes(autorange="reversed", title=None, tickfont=dict(color="#F2EFE9"), gridcolor="#3A4250")
    fig.update_xaxes(tickfont=dict(color="#F2EFE9"), gridcolor="#3A4250", linecolor="#5C6778")
    fig.update_layout(
        height=height,
        showlegend=False,
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="#161B22",
        plot_bgcolor="#161B22",
        font=dict(color="#F2EFE9"),
    )
    return fig


def figure_prep():
    rows = [{
        "事项": p["必须完成"],
        "开始": p["start"],
        "结束": p["end"] + timedelta(days=1),
        "截止": "截止 " + p["截止"],
        "验收": p["验收"],
        "说明": p["说明"],
    } for p in td.PREP]
    return _timeline(rows, "事项", 360)


def figure_gantt():
    rows = [{
        "阶段": p["name"],
        "开始": p["start"],
        "结束": p["end"],
        "说明": p["task"],
        "天数": f"{(p['end'] - p['start']).days + 1} 天",
    } for p in td.PHASES]
    return _timeline(rows, "阶段", 580)


def _bar_with_dash(names, bars, caps, notes, bar_name, cap_name, y_title, bar_color, show_cap, height, label="bar"):
    x = list(range(len(names)))
    fig = go.Figure()
    fig.add_bar(
        x=x, y=bars, name=bar_name, marker_color=bar_color, width=0.62,
        text=[f"{v:,.0f}" for v in bars] if label == "bar" else None,
        textposition="outside", cliponaxis=False,
        textfont=dict(color="#F2EFE9", size=12),
        customdata=list(zip(names, caps, notes)),
        hovertemplate=f"%{{customdata[0]}}<br>{bar_name} %{{y:,.0f}} 元<br>{cap_name} %{{customdata[1]:,.0f}} 元<br>%{{customdata[2]}}<extra></extra>",
    )
    if show_cap:
        xs, ys = [], []
        for i, cap in enumerate(caps):
            xs += [i - 0.36, i + 0.36, None]
            ys += [cap, cap, None]
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", name=cap_name,
            line=dict(color="#E8D5C4", width=2, dash="dash"),
            hoverinfo="skip",
        ))
        if label == "range":
            fig.add_trace(go.Scatter(
                x=x, y=list(caps), mode="text", showlegend=False, hoverinfo="skip",
                text=[f"{b:,.0f}–{c:,.0f}" for b, c in zip(bars, caps)],
                textposition="top center", textfont=dict(color="#F2EFE9", size=12),
                cliponaxis=False,
            ))
    top = max(caps if show_cap else bars)
    fig.update_layout(
        height=height,
        bargap=0.28,
        margin=dict(l=0, r=8, t=36, b=72),
        paper_bgcolor="#161B22",
        plot_bgcolor="#161B22",
        font=dict(color="#F2EFE9"),
        legend=dict(orientation="h", y=1.12, x=0),
        yaxis=dict(
            title=dict(text=y_title, font=dict(color="#F2EFE9")),
            range=[0, top * (1.28 if label == "range" else 1.18)],
            gridcolor="#3A4250",
            tickfont=dict(color="#F2EFE9"),
        ),
        xaxis=dict(
            tickmode="array", tickvals=x, ticktext=names, tickangle=-24,
            tickfont=dict(color="#F2EFE9"),
        ),
    )
    return fig


def figure_budget(show_cap):
    df = pd.DataFrame(td.BUDGET_ITEMS)
    return _bar_with_dash(
        df["科目"], df["计划"], df["上限"], df["备注"],
        "计划", "控制上限", "元", "#C45C26", show_cap, 420,
    )


def figure_daily():
    df = pd.DataFrame(td.DAILY_BUDGET)
    return _bar_with_dash(
        df["区域"], df["低"], df["高"], df["办法"],
        "日预算下限", "日预算上限", "元/天", "#3E5C76", True, 380, label="range",
    )


def figure_temp():
    df = pd.DataFrame([{
        "国家": c["name"], "低": c["temp_low"], "高": c["temp_high"],
    } for c in td.COUNTRIES])
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["国家"],
        y=df["高"] - df["低"],
        base=df["低"],
        marker=dict(
            color=df["高"],
            colorscale=[[0, "#6BA3C7"], [0.45, "#E2B84A"], [1, "#D4532B"]],
            cmin=8,
            cmax=38,
            line=dict(width=0),
        ),
        customdata=df[["低", "高"]].to_numpy(),
        hovertemplate="%{x}<br>白天 %{customdata[0]}–%{customdata[1]} ℃<extra></extra>",
        text=[f"{lo}–{hi}" for lo, hi in zip(df["低"], df["高"])],
        textposition="outside",
        textfont=dict(color="#F2EFE9", size=12),
        cliponaxis=False,
        showlegend=False,
    ))
    fig.update_layout(
        height=360,
        margin=dict(l=0, r=8, t=28, b=0),
        paper_bgcolor="#161B22",
        plot_bgcolor="#161B22",
        font=dict(color="#F2EFE9"),
        bargap=0.32,
        yaxis=dict(title=dict(text="℃", font=dict(color="#F2EFE9")), range=[0, 52], gridcolor="#3A4250", tickfont=dict(color="#F2EFE9")),
        xaxis=dict(tickfont=dict(color="#F2EFE9"), tickangle=-40),
    )
    return fig


def page_overview():
    st.title("欧亚自驾")
    st.caption("2030 年 3 月 1 日出发 · 约 200 天 · 3月10日从霍尔果斯出境，9月8日从二连浩特入境（最晚9月14日）· 回国走西伯利亚、贝加尔湖、蒙古、鄂尔多斯、北京到上海 · 冰岛只看夏天，不追极光")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("总周期", "约 200 天")
    c1.caption("3月1日出，9月16日回上海")
    c2.metric("全程", "约 3.4 万 km")
    c3.metric("预算目标", "18.5 万")
    c3.caption("出发前准备 22 万")
    c4.metric("预备金", "3.5 万")
    c4.caption("不主动消费")

    st.subheader("路线")
    day = st.slider(
        "拖动日期，看当天走到哪",
        min_value=TRIP_START,
        max_value=TRIP_END,
        value=TRIP_START,
        format="YYYY-MM-DD",
        key="route_day_2030",
    )
    pos = td.track_on(day)
    st.components.v1.html(figure_overview_map(day), height=676, scrolling=False)
    st.info(f"**{day.isoformat()} · {pos['country']} · {pos['name']}** · 沿环线约 **{pos['along_km']:,.0f}** 公里。{KM_NOTE}")

    km_rows = []
    for d in td.daterange(TRIP_START, TRIP_END):
        p = td.track_on(d)
        km_rows.append({"日期": d, "沿环线里程": round(p["along_km"]), "所在": p["country"]})
    km = pd.DataFrame(km_rows)
    fig_km = px.line(km, x="日期", y="沿环线里程", hover_data=["所在"])
    fig_km.update_traces(line=dict(color="#C45C26", width=2))
    fig_km.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0), yaxis_title="公里（规划估算）")
    st.plotly_chart(fig_km, use_container_width=True)
    st.caption("环线只往前走，累计里程单调上升。横轴是计划日期，不是对边境开放的承诺。")

    st.subheader("出发前准备")
    st.plotly_chart(figure_prep(), use_container_width=True)
    st.caption("从左下往右上。12 月 1 日冻结路线后，签证、轮渡、ATA、驾照保险四条重叠着做；整备插在签证等待的后半段。只有最上面的最终验收排在最后。")
    st.subheader("行程甘特图")
    st.plotly_chart(figure_gantt(), use_container_width=True)
    st.subheader("白天气温")
    st.plotly_chart(figure_temp(), use_container_width=True)
    st.caption("每根柱从低温画到高温，对应这一段实际经过的月份。")

    st.subheader("预算")
    show_cap = st.toggle("对照控制上限", value=True)
    st.plotly_chart(figure_budget(show_cap), use_container_width=True)
    st.caption("柱子是计划金额，虚线是这个科目还能接受的控制上限。")
    b1, b2, b3 = st.columns(3)
    b1.metric("计划日常支出", "185,000")
    b2.metric("建议准备", "220,000")
    b2.caption("含 3.5 万预备金")
    b3.metric("各科目上限合计", "268,000")
    b3.caption("极端情形，不作为目标")
    st.plotly_chart(figure_daily(), use_container_width=True)
    st.caption("柱子按日常下限准备，虚线是这一档的上限。口岸和维修日从预备金里出。")

    st.subheader("红线")
    st.dataframe(pd.DataFrame(td.RED_LINES), use_container_width=True, hide_index=True)
    st.markdown("**每周**")
    for rule in td.WEEKLY_RULES:
        st.markdown(f"- {rule}")

    with st.expander("北返与俄罗斯决策门"):
        for line in td.RETURN_NOTES:
            st.markdown(f"- {line}")
    with st.expander("出发前必须改口的三件事"):
        for line in td.RISK_FIXES:
            st.markdown(f"- {line}")
    with st.expander("出发前倒排"):
        st.dataframe(pd.DataFrame(td.PREP)[["截止", "必须完成", "验收"]], use_container_width=True, hide_index=True)
    with st.expander("车辆装备与口岸"):
        for line in td.GEAR:
            st.markdown(f"- {line}")
        st.markdown(td.BORDER_FLOW)
        st.caption("出发前证件和车辆不达标，不出发。9月14日前必须从二连浩特进中国。申根大约 84 天，距 90 天留约 6 天。不用“应该免签”“现场再说”作为通关依据。")


def country_heading(country, full=False):
    parts = country.get("parts")
    if parts and (full or not country.get("group_nav")):
        if full:
            return " / ".join(f"{name} · {en} · {flag}" for name, en, flag in parts)
        return " / ".join(f"{name}{flag}" for name, en, flag in parts)
    if full:
        return f"{country['name']} · {country['name_en']} · {country['flag']}"
    return f"{country['name']}{country['flag']}"


def page_country(country):
    st.title(country_heading(country, full=True))
    runs = td.visits(country)
    spend = td.spend_plan()["country"].get(country["id"])
    stay_days = spend["days"] if spend else country["days"]
    if len(runs) > 1:
        spans = "、".join(f"{r[0]['arrive'].isoformat()}–{r[-1]['arrive'].isoformat()}" for r in runs)
        st.caption(f"分 {len(runs)} 段经过：{spans}。共 {stay_days} 天。{country['blurb']}")
    else:
        st.caption(f"计划日期 {country['start'].isoformat()} – {country['end'].isoformat()} · {stay_days} 天 · {country['blurb']}")
    if country.get("banner"):
        st.warning(country["banner"])
    cities = [c for run in runs for c in run]
    elevs = [c["elev"] for c in cities]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("停留", f"{stay_days} 天")
    m2.metric("海拔", f"{min(elevs)} – {max(elevs)} 米")
    m3.metric("白天", f"{country['temp_low']}–{country['temp_high']} ℃")
    spend = td.spend_plan()["country"].get(country["id"])
    if spend:
        m4.metric("吃饭+交通费", f"{spend['yuan']:,} 元")
    else:
        m4.metric("吃饭+交通费", "不计入")
    st.caption("吃饭+交通费是这几天的吃饭、营地、油费、路桥停车和杂费。签证、车辆整备和维修不在这列。")

    st.components.v1.html(figure_country_map(country), height=676, scrolling=False)
    caption = _map_caption(country)
    if caption:
        st.caption(caption)

    st.subheader("历程")
    st.markdown(f"**路线** {country['route']}")
    st.markdown(f"**地形** {country['terrain']}")
    st.markdown(f"**气候** {country['climate']}")
    st.markdown(f"**海拔** {country['elev_note']}")
    if country["gdp"]:
        st.caption(f"人均 GDP 约 {country['gdp']:,} 美元。{country['budget_note']}")
    else:
        st.caption(country["budget_note"])

    st.subheader("注意事项")
    for line in [country["docs"], *country["focus"], *country["risks"]]:
        if line:
            st.markdown(f"- {line}")
    st.subheader("城市")
    city_spend = td.spend_plan()["city"]
    for c in cities:
        st.markdown(f"**{c['name']}** · {c['arrive'].isoformat()}")
        money = city_spend.get((c["name"], c["arrive"]))
        lead = ""
        if money:
            lead = f"停留 {money['days']} 天，食宿、燃油和路桥停车大约 {money['yuan']:,} 元。"
        st.markdown(lead + (td.CITY_BLURBS.get(c["name"]) or c["note"]))


def _country_page(cid):
    def _run():
        page_country(td.country_by_id(cid))
    _run.__name__ = f"page_country_{cid}"
    return _run


def main():
    st.set_page_config(page_title="欧亚自驾", layout="wide", initial_sidebar_state="expanded")
    _fullscreen_host()
    st.sidebar.markdown("**欧亚自驾**")
    pages = [st.Page(page_overview, title="总览", icon="🗺️", url_path="overview", default=True)]
    for c in td.COUNTRIES:
        pages.append(st.Page(_country_page(c["id"]), title=country_heading(c), icon="📍", url_path=c["id"]))
    st.navigation(pages, position="sidebar", expanded=True).run()


if __name__ == "__main__":
    main()
