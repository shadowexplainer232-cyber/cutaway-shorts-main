"""Engine cooling loop (2D, shaded), schematic.

  stage: overview | coolant | pump | radiator | air | thermostat
Coolant runs engine -> hot pipe -> radiator -> cold pipe (pump) -> engine. Red = hot, blue = cooled.
Air is pulled through the radiator fins by the fan. Illustrative, not an engineering drawing.
"""
import math

from .common import font
from .visuals_jet import _mix, _ease
from .visuals_turbo import _pipe, _wheel

W, H = 1080, 1920
HOT = (255, 90, 50)

ENGINE = (90, 700, 330, 960)
RAD = (620, 690, 860, 980)
A, B, C, D, E, F = (330, 745), (740, 745), (740, 925), (330, 925), (240, 925), (240, 745)
LOOP = [A, B, C, D, E, F, A]
BYPASS = [(300, 745), (300, 925), (240, 925), (240, 745), (300, 745)]
PUMP, VALVE, FAN = (515, 925), (515, 745), (950, 835)


def _along(pts, s):
    lens = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    total, target = sum(lens), (s % 1.0) * sum(lens)
    for i, ((a, b), n) in enumerate(zip(zip(pts, pts[1:]), lens)):
        if target <= n:
            f = target / n if n else 0
            return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f), i, f
        target -= n
    return pts[-1], len(lens) - 1, 1.0


def _loop_temp(seg, f):
    # segments of LOOP: A-B hot pipe, B-C radiator, C-D cold pipe, D-E, E-F engine passage, F-A
    return {0: 1.0, 1: 1.0 - f, 2: 0.0, 3: 0.0, 4: f, 5: 1.0}[seg]


def _tint(col, t):
    c, h = col["tech"], HOT
    return tuple(int(c[i] * (1 - t) + h[i] * t) for i in range(3))


def draw_cooling(img, d, vis, scene_t, col, brand, ep, sec=0.0):
    stage = vis.get("stage", "overview")
    bg = col["bg"]
    K = {"overview": dict(e=1, r=1, p=1, v=1, f=1),
         "coolant": dict(e=1, r=.35, p=.5, v=.5, f=.3),
         "pump": dict(e=.5, r=.4, p=1, v=.5, f=.3),
         "radiator": dict(e=.5, r=1, p=.5, v=.5, f=.6),
         "air": dict(e=.4, r=1, p=.4, v=.4, f=1),
         "thermostat": dict(e=.7, r=.7, p=.6, v=1, f=.5)}[stage]

    # valve: closed for the first 2.2 s of the thermostat scene, then opens
    valve_open = 1.0 if stage != "thermostat" else _ease((sec - 2.2) / 0.5)

    # pipes
    for pts in ([A, B], [C, D]):
        _pipe(d, col, pts, col["accent"], 0.5 + 0.5 * K["p"])
    _pipe(d, col, [D, E, F, A][1:3], col["muted"], 0.3)

    # engine block (shaded, with cylinders)
    x0, y0, x1, y1 = ENGINE
    d.rounded_rectangle([x0 + 8, y0 + 8, x1 + 8, y1 + 8], radius=18, fill=_mix(bg, col["muted"], 0.10))
    d.rounded_rectangle([x0, y0, x1, y1], radius=18, fill=_mix(bg, col["muted"], 0.20 + 0.25 * K["e"]),
                        outline=_mix(bg, col["text"], 0.35 + 0.6 * K["e"]), width=6)
    for c in range(3):
        flash = max(0.0, math.sin(sec * 5 + c * 2.1)) ** 4
        d.rectangle([x0 + 70 + c * 52, y0 + 150, x0 + 104 + c * 52, y0 + 210],
                    fill=_mix(bg, HOT, 0.12 + 0.7 * flash * K["e"]))
    d.text(((x0 + x1) // 2, y1 + 40), "ENGINE", font=font(26), fill=_mix(bg, col["text"], 0.4 + 0.6 * K["e"]), anchor="mm")

    # radiator: tubes + fins
    rx0, ry0, rx1, ry1 = RAD
    d.rounded_rectangle([rx0, ry0, rx1, ry1], radius=14, fill=_mix(bg, col["muted"], 0.15 + 0.2 * K["r"]),
                        outline=_mix(bg, col["text"], 0.35 + 0.6 * K["r"]), width=5)
    for x in range(rx0 + 12, rx1 - 6, 12):                                        # fins
        d.line([(x, ry0 + 8), (x, ry1 - 8)], fill=_mix(bg, col["text"], 0.15 + 0.3 * K["r"]), width=2)
    for x in (650, 695, 740, 785, 830):                                           # core tubes
        d.line([(x, ry0 + 20), (x, ry1 - 20)], fill=_mix(bg, col["accent"], 0.45 + 0.5 * K["r"]), width=7)
    d.text(((rx0 + rx1) // 2, ry1 + 40), "RADIATOR", font=font(26), fill=_mix(bg, col["text"], 0.4 + 0.6 * K["r"]), anchor="mm")

    # pump
    _wheel(d, col, PUMP, 8.0 * sec * K["p"], col["tech"], K["p"], radius=34)
    d.text((PUMP[0], PUMP[1] + 78), "PUMP", font=font(24), fill=_mix(bg, col["text"], 0.4 + 0.6 * K["p"]), anchor="mm")

    # thermostat valve: a flap that turns from closed (across the pipe) to open (along it)
    vx, vy = VALVE
    d.ellipse([vx - 30, vy - 30, vx + 30, vy + 30], fill=bg, outline=_mix(bg, col["accent"], 0.4 + 0.6 * K["v"]), width=5)
    ang = math.pi / 2 * (1 - valve_open)
    d.line([(vx - 26 * math.cos(ang), vy - 26 * math.sin(ang)), (vx + 26 * math.cos(ang), vy + 26 * math.sin(ang))],
           fill=_mix(bg, col["accent"], 0.4 + 0.6 * K["v"]), width=8)
    d.text((vx, vy - 62), "THERMOSTAT", font=font(24), fill=_mix(bg, col["text"], 0.4 + 0.6 * K["v"]), anchor="mm")

    # fan
    fx, fy = FAN
    d.ellipse([fx - 62, fy - 62, fx + 62, fy + 62], outline=_mix(bg, col["muted"], 0.3 + 0.6 * K["f"]), width=5)
    for j in range(4):
        a = 7.0 * sec * K["f"] + math.pi / 2 * j
        d.polygon([(fx, fy), (fx + 56 * math.cos(a - 0.35), fy + 56 * math.sin(a - 0.35)),
                   (fx + 56 * math.cos(a + 0.35), fy + 56 * math.sin(a + 0.35))],
                  fill=_mix(bg, col["tech"], 0.25 + 0.6 * K["f"]))
    d.ellipse([fx - 10, fy - 10, fx + 10, fy + 10], fill=col["text"])
    d.text((fx, fy + 90), "FAN", font=font(24), fill=_mix(bg, col["text"], 0.4 + 0.6 * K["f"]), anchor="mm")

    # coolant parcels
    n = 16
    for i in range(n):
        s = (i / n + sec * 0.12) % 1.0
        if valve_open > 0.02:
            (x, y), seg, f = _along(LOOP, s)
            c = _tint(col, _loop_temp(seg, f))
            r = 8
            fade = _mix(bg, c, 0.25 + 0.75 * (K["e"] if seg in (4, 5, 0) else K["r"] if seg == 1 else K["p"]))
            d.ellipse([x - r, y - r, x + r, y + r], fill=_mix(bg, fade, valve_open))
        if valve_open < 0.98:
            (x, y), _, _ = _along(BYPASS, s)
            c = _tint(col, 0.55)
            d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=_mix(bg, c, 1 - valve_open))

    # air through the fins
    for j in range(14):
        row = j % 5
        ph = (j / 14 + sec * 0.28) % 1.0
        x = 1060 - ph * 470
        y = 735 + row * 50
        warm = max(0.0, min(1.0, (rx1 - x) / 120)) if x < rx1 else 0.0
        if x < rx0 - 10:
            continue
        c = _mix(col["tech"], col["accent"], 0.6 * warm)
        a = 0.15 + 0.85 * K["f"]
        d.line([(x, y), (x + 26, y)], fill=_mix(bg, c, a), width=5)

    # captions
    title = {"overview": "BURNING FUEL MAKES HEAT", "coolant": "COOLANT ABSORBS THE HEAT",
             "pump": "A PUMP KEEPS IT MOVING", "radiator": "HOT COOLANT FLOWS THROUGH THE RADIATOR",
             "air": "AIR TAKES THE HEAT AWAY", "thermostat": ""}[stage]
    if stage == "thermostat":
        title = "THERMOSTAT CLOSED: ENGINE WARMS UP" if valve_open < 0.5 else "THERMOSTAT OPEN: COOLANT GOES TO THE RADIATOR"
    size = 32
    while d.textlength(title, font=font(size)) > W - 80 and size > 22:
        size -= 2
    d.text((W // 2, 590), title, font=font(size), fill=_mix(bg, col["accent"], _ease(sec * 2)), anchor="mm")

    if vis.get("callout"):
        size = 42
        while d.textlength(vis["callout"], font=font(size)) > W - 100 and size > 26:
            size -= 2
        d.text((W // 2, 1200), vis["callout"], font=font(size), fill=_mix(bg, col["accent"], _ease(sec * 3.0)), anchor="mm")
    d.text((W // 2, 1252), "Simplified animation", font=font(24), fill=col["muted"], anchor="mm")
