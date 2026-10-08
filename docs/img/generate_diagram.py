"""Generates the FIWARE Made Simple architecture diagram.

Usage: python3 docs/img/generate_diagram.py docs/img/architecture.svg
"""
import sys
from xml.sax.saxutils import escape

W, H = 1600, 1290
FONT = "'Helvetica Neue', Helvetica, Arial, sans-serif"

C = dict(
    text="#1f2937", muted="#6b7280", line="#d1d5db",
    app_bg="#f5f3ff", app_bd="#ddd6fe", app_tx="#6d28d9",
    be_bg="#eff6ff", be_bd="#bfdbfe", be_tx="#1d4ed8",
    iot_bg="#ecfdf5", iot_bd="#a7f3d0", iot_tx="#047857",
    ge="#2563eb", comp="#94a3b8",
    tel="#0d9488", cmd="#ea580c", gray="#64748b",
)

out = []
add = out.append


def t(x, y, s, size=14, weight=400, fill=None, anchor="start", italic=False, ls=None):
    style = f' font-style="italic"' if italic else ""
    spacing = f' letter-spacing="{ls}"' if ls else ""
    add(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill or C["text"]}" '
        f'text-anchor="{anchor}"{style}{spacing}>{escape(s)}</text>')


def rect(x, y, w, h, fill, stroke, r=14, sw=1.2, dash=None, extra=""):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d} {extra}/>')


HEADERS = []


def band(y, h, bg, bd, tx, title, subtitle):
    rect(40, y, W - 80, h, bg, bd, r=18)
    HEADERS.append((y, bg, tx, title, subtitle))


def band_headers():
    """Drawn last, with a background, so the arrows pass behind the text."""
    for y, bg, tx, title, subtitle in HEADERS:
        sx = 64 + len(title) * 12 + 14
        w = sx - 64 + len(subtitle) * 6.9 + 18
        rect(56, y + 13, w, 28, bg, bg, r=8, sw=0)
        t(64, y + 32, title, 15, 700, tx, ls="1.5")
        t(sx, y + 32, subtitle, 13.5, 400, C["muted"])


def chip(x, y, label, published=True, color=None):
    color = color or C["be_tx"]
    w = 9 + len(label) * 7.4 + (14 if published else 0)
    if published:
        rect(x - w, y, w, 22, color, color, r=11, sw=1)
        add(f'<circle cx="{x - w + 11}" cy="{y + 11}" r="3.2" fill="#ffffff"/>')
        t(x - w + 19, y + 15.5, label, 12, 600, "#ffffff")
    else:
        rect(x - w, y, w, 22, "#ffffff", C["comp"], r=11, sw=1.2, dash="3 2")
        t(x - w / 2, y + 15.5, label, 12, 600, C["muted"], anchor="middle")


def card(x, y, w, h, title, lines, kind=None, chips=()):
    """kind: 'ge' (FIWARE Generic Enabler), 'comp' (complementary), or None."""
    rect(x, y, w, h, "#ffffff", C["line"], r=12, extra='filter="url(#shadow)"')
    ty = y + 32
    if kind:
        accent = C["ge"] if kind == "ge" else C["comp"]
        add(f'<rect x="{x}" y="{y}" width="6" height="{h}" rx="3" fill="{accent}"/>')
        tag = "FIWARE GE" if kind == "ge" else "COMPLEMENTARY"
        t(x + 22, y + 24, tag, 10.5, 700, accent, ls="1.2")
        ty = y + 48
    t(x + 22, ty, title, 18, 700)
    for i, ln in enumerate(lines):
        t(x + 22, ty + 24 + i * 21, ln, 13.5, 400, C["muted"])
    cx = x + w - 14
    for label, pub in chips:
        chip(cx, y + 12, label, pub)
        cx -= 9 + len(label) * 7.4 + (14 if pub else 0) + 6


def arrow(points, color, style="solid", width=2.2, marker=None):
    dash = {"solid": "", "mqtt": ' stroke-dasharray="9 6"', "mongo": ' stroke-dasharray="2 5"'}[style]
    cap = ' stroke-linecap="round"' if style == "mongo" else ""
    d = "M" + " L".join(f"{x} {y}" for x, y in points)
    m = marker or {C["tel"]: "tel", C["cmd"]: "cmd", C["gray"]: "gray"}[color]
    add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}"{dash}{cap} marker-end="url(#a-{m})"/>')


def badge(x, y, label, color):
    add(f'<circle cx="{x}" cy="{y}" r="12" fill="{color}" stroke="#ffffff" stroke-width="2.5"/>')
    t(x, y + 4.5, label, 12.5, 700, "#ffffff", anchor="middle")


def label(x, y, s, color=None, anchor="start", size=12.5, weight=600):
    t(x, y, s, size, weight, color or C["muted"], anchor=anchor)


# ---------------------------------------------------------------- header
add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
    f'font-family="{FONT}" role="img" aria-labelledby="title desc">')
add('<title id="title">FIWARE Made Simple: architecture</title>')
add('<desc id="desc">Application, back-end, and IoT layers of FIWARE Made Simple, with the telemetry and command flows.</desc>')
add('<defs>')
add('<filter id="shadow" x="-5%" y="-5%" width="110%" height="120%"><feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#0f172a" flood-opacity="0.08"/></filter>')
for name, color in (("tel", C["tel"]), ("cmd", C["cmd"]), ("gray", C["gray"])):
    add(f'<marker id="a-{name}" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        f'<path d="M0 0 L10 5 L0 10 z" fill="{color}"/></marker>')
add('</defs>')
add(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')

t(40, 52, "FIWARE Made Simple", 30, 700)
t(40, 80, "Platform architecture  ·  Orion 4.5  ·  IoT Agent UltraLight 3.7  ·  STH-Comet 2.11  ·  Mosquitto 2.0  ·  MongoDB 8.0",
  14.5, 400, C["muted"])

# columns (center) and cards
CW = 300
X = [100, 480, 860, 1240]          # x inicial de cada coluna
MID = [x + CW / 2 for x in X]

# ---------------------------------------------------------------- APPLICATION
AY, AH = 104, 196
band(AY, AH, C["app_bg"], C["app_bd"], C["app_tx"], "APPLICATION", "consumes and controls the data")
cy, ch = AY + 56, 116
card(X[0], cy, CW, ch, "Provisioning", ["Postman · scripts", "registers service groups and devices"])
card(X[1], cy, CW, ch, "Context applications", ["Postman · web · mobile · AI", "query entities, send commands"])
card(X[2], cy, CW, ch, "Dashboards", ["dashboard.py (Dash) · chart.py", "query the history"])
card(X[3], cy, CW, ch, "Data analysis", ["Compass · Python · BI", "reader user (read-only)"])
APP_BOTTOM = cy + ch

# ---------------------------------------------------------------- BACK-END
BY, BH = 330, 480
band(BY, BH, C["be_bg"], C["be_bd"], C["be_tx"], "BACK-END",
     "Docker Compose on a server, VM, or cloud (x86_64)  ·  internal “fiware” network")
R1, R2, RH = BY + 66, BY + 290, 140
card(X[0], R1, CW, RH, "IoT Agent UltraLight", ["translates MQTT/HTTP ↔ NGSI-v2", "and forwards the commands"], "ge",
     chips=((":7896", True), (":4041", True)))
card(X[1], R1, CW, RH, "Orion Context Broker", ["CURRENT state of the entities", "NGSI-v2 API · subscriptions"], "ge",
     chips=((":1026", True),))
card(X[2], R1, CW, RH, "STH-Comet", ["short-term history", "lastN queries and aggregations"], "ge",
     chips=((":8666", True),))
card(X[3], R1, CW, RH, "MongoDB · history", ["sth_<service> databases", "authentication enabled"], "comp",
     chips=((":27017", True),))
MW = 230
card(X[0], R2, MW, RH, "Mosquitto", ["MQTT broker", "+ :9001 (WebSocket)"], "comp", chips=((":1883", True),))
card(X[1], R2, CW, RH, "MongoDB · context", ["orion-<service> · iotagentul", "no password"], "comp",
     chips=(("internal", False),))

# internal network note
nx, ny, nw, nh = X[2], R2, X[3] + CW - X[2], RH
rect(nx, ny, nw, nh, "#ffffff", C["be_bd"], r=12, dash="5 4", sw=1.4)
t(nx + 22, ny + 32, "Internal Docker network", 15, 700, C["be_tx"])
t(nx + 22, ny + 56, "Containers reach each other by service name:", 13.5, 400, C["muted"])
t(nx + 22, ny + 80, "orion:1026 · iot-agent:4041 · sth-comet:8666", 13.5, 600, C["text"])
t(nx + 22, ny + 101, "mosquitto:1883 · mongo-db:27017 · mongo-db-sth:27017", 13.5, 600, C["text"])
def chip_w(label, pub):
    return 9 + len(label) * 7.4 + (14 if pub else 0)


cx0 = nx + 22 + chip_w(":1026", True)
chip(cx0, ny + 110, ":1026", True)
t(cx0 + 8, ny + 125.5, "published on the host", 12.5, 400, C["muted"])
cx1 = cx0 + 150 + chip_w("internal", False)
chip(cx1, ny + 110, "internal", False)
t(cx1 + 8, ny + 125.5, "internal network only, no outside access", 12.5, 400, C["muted"])

# ---------------------------------------------------------------- IoT
IY, IH = 840, 186
band(IY, IH, C["iot_bg"], C["iot_bd"], C["iot_tx"], "IoT", "devices that sense and act")
iy, ih = IY + 50, 116
card(X[0], iy, MW, ih, "ESP32 · Smart Lamp", ["LDR + LED", "or simulator (Python/Wokwi)"])
HX = 345
card(HX, iy, 270, ih, "HTTP device", ["UltraLight over HTTP", "e.g., Postman (folder 3)"])
ox = 660
rect(ox, iy, X[3] + CW - ox, ih, "#ffffff", C["iot_bd"], r=12, dash="5 4", sw=1.4)
t(ox + 22, iy + 32, "Other devices", 15, 700, C["iot_tx"])
t(ox + 22, iy + 56, "sensors, actuators, robots, drones, vehicles...", 13.5, 400, C["muted"])
t(ox + 22, iy + 78, "any equipment that publishes over MQTT or sends HTTP:", 13.5, 400, C["muted"])
t(ox + 22, iy + 100, "publishes /<apikey>/<device_id>/attrs  ·  subscribes /<apikey>/<device_id>/cmd", 13.5, 600, C["text"])

# ---------------------------------------------------------------- arrows
IOTA_B, IOTA_T = R1 + RH, R1
MOS_T, MOS_B = R2, R2 + RH
ESP_T = iy
# Application -> back-end
arrow([(MID[0], APP_BOTTOM), (MID[0], R1 - 4)], C["gray"])
label(MID[0] + 10, APP_BOTTOM + 30, "provisions :4041")
arrow([(MID[1], APP_BOTTOM), (MID[1], R1 - 4)], C["cmd"])
badge(MID[1], APP_BOTTOM + 25, "A", C["cmd"])
label(MID[1] + 20, APP_BOTTOM + 30, "NGSI-v2 :1026", C["cmd"])
arrow([(MID[2], APP_BOTTOM), (MID[2], R1 - 4)], C["tel"])
badge(MID[2], APP_BOTTOM + 25, "6", C["tel"])
label(MID[2] + 20, APP_BOTTOM + 30, "GET :8666", C["tel"])
arrow([(MID[3], APP_BOTTOM), (MID[3], R1 - 4)], C["gray"], "mongo")
label(MID[3] + 10, APP_BOTTOM + 30, "reader :27017")

# IoT Agent <-> Orion
arrow([(X[0] + CW, R1 + 58), (X[1] - 4, R1 + 58)], C["tel"])
badge(X[0] + CW + 40, R1 + 58, "3", C["tel"])
arrow([(X[1], R1 + 102), (X[0] + CW + 4, R1 + 102)], C["cmd"])
badge(X[0] + CW + 40, R1 + 102, "B", C["cmd"])
# Orion -> STH-Comet (subscription)
arrow([(X[1] + CW, R1 + 70), (X[2] - 4, R1 + 70)], C["tel"])
badge(X[1] + CW + 40, R1 + 70, "4", C["tel"])
label(X[1] + CW + 40, R1 + 100, "notification", C["tel"], anchor="middle")
# STH-Comet -> history mongo
arrow([(X[2] + CW, R1 + 70), (X[3] - 4, R1 + 70)], C["tel"], "mongo")
badge(X[2] + CW + 40, R1 + 70, "5", C["tel"])
# Orion -> context mongo ; IoT Agent -> context mongo
arrow([(MID[1], IOTA_B), (MID[1], R2 - 4)], C["gray"], "mongo")
arrow([(X[0] + CW, IOTA_B - 20), (X[1] - 4, R2 + 30)], C["gray"], "mongo")
# Mosquitto <-> IoT Agent (MQTT)
mx1, mx2 = X[0] + 80, X[0] + 150
arrow([(mx1, MOS_T), (mx1, IOTA_B + 4)], C["tel"], "mqtt")
badge(mx1, (MOS_T + IOTA_B) / 2, "2", C["tel"])
arrow([(mx2, IOTA_B), (mx2, MOS_T - 4)], C["cmd"], "mqtt")
badge(mx2, (MOS_T + IOTA_B) / 2, "C", C["cmd"])
# IoT device <-> Mosquitto (MQTT)
arrow([(mx1, ESP_T), (mx1, MOS_B + 4)], C["tel"], "mqtt")
badge(mx1, (ESP_T + MOS_B) / 2 - 2, "1", C["tel"])
arrow([(mx2, MOS_B), (mx2, ESP_T - 4)], C["cmd"], "mqtt")
badge(mx2, (ESP_T + MOS_B) / 2 - 2, "C", C["cmd"])
# HTTP device -> IoT Agent :7896
hx = 375
arrow([(hx, ESP_T), (hx, IOTA_B + 4)], C["tel"])
badge(hx, (ESP_T + MOS_B) / 2 - 2, "1", C["tel"])
label(hx + 18, (ESP_T + MOS_B) / 2 + 3, "HTTP :7896", C["tel"])

band_headers()

# ---------------------------------------------------------------- legend
LY = IY + IH + 24
LH = H - LY - 30
rect(40, LY, W - 80, LH, "#f8fafc", "#e2e8f0", r=18)

col1, col2, col3 = 64, 600, 1130
t(col1, LY + 34, "Telemetry: from sensor to application", 15, 700, C["tel"])
steps_t = [
    ("1", "IoT device publishes a measurement to Mosquitto (or over HTTP)"),
    ("2", "Mosquitto delivers it to the IoT Agent (subscribed to /+/+/attrs)"),
    ("3", "IoT Agent updates the entity in Orion"),
    ("4", "Orion notifies STH-Comet (subscription)"),
    ("5", "STH-Comet stores the time series"),
    ("6", "Dashboard queries the history in STH-Comet"),
]
for i, (n, s) in enumerate(steps_t):
    yy = LY + 64 + i * 27
    badge(col1 + 12, yy - 4.5, n, C["tel"])
    t(col1 + 34, yy, s, 13.5)

t(col2, LY + 34, "Command: from application to actuator", 15, 700, C["cmd"])
steps_c = [
    ("A", "Application sends the “on” command to Orion (PATCH)"),
    ("B", "Orion forwards it to the IoT Agent (registration)"),
    ("C", "IoT Agent publishes /<apikey>/<device_id>/cmd; the device runs it"),
    ("D", "IoT device confirms on /cmdexe through path 1 → 2"),
    ("E", "IoT Agent sets on_status = OK in Orion (path 3)"),
]
for i, (n, s) in enumerate(steps_c):
    yy = LY + 64 + i * 27
    badge(col2 + 12, yy - 4.5, n, C["cmd"])
    t(col2 + 34, yy, s, 13.5)

t(col3, LY + 34, "How to read", 15, 700)
leg = LY + 60
for i, (style, name) in enumerate((("solid", "HTTP / NGSI-v2 (REST)"), ("mqtt", "MQTT"), ("mongo", "MongoDB"))):
    yy = leg + i * 26
    arrow([(col3, yy), (col3 + 52, yy)], C["gray"], style, width=2)
    t(col3 + 66, yy + 4.5, name, 13.5)
t(col3, leg + 86, "Arrows start at whoever initiates the connection.", 13.5, 400, C["muted"])
add(f'<rect x="{col3}" y="{leg + 102}" width="6" height="22" rx="3" fill="{C["ge"]}"/>')
t(col3 + 16, leg + 118, "FIWARE Generic Enabler", 13.5)
add(f'<rect x="{col3 + 196}" y="{leg + 102}" width="6" height="22" rx="3" fill="{C["comp"]}"/>')
t(col3 + 212, leg + 118, "complementary", 13.5)

add("</svg>")

with open(sys.argv[1], "w", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n")
