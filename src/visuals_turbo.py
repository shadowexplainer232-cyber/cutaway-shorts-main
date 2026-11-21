"""Turbocharger animation (2D, Pillow, schematic).

Exhaust leaves the engine, spins the turbine; a shaft turns the compressor; the compressor forces
air into the engine. `stage` decides what is highlighted:
  idle        everything dim, a pulsing ring on the turbine (used for the hook)
  air         engine + air path (more air -> more fuel -> more power)
  turbine     exhaust path + turbine + shaft
  compressor  air path + compressor + shaft
  lag         everything, with the wheels spinning up slowly after the pedal press
  all         everything
Shapes and speeds are illustrative, not an engineering drawing.
"""
import math

from .common import font
from .visuals_jet import _mix, _ease

W, H = 1080, 1920
DY = 20
R = 95


def _p(x, y):
    return (x, y + DY)


ENGINE = (400, 520, 680, 700)                       # x0, y0, x1, y1 before DY
EXH = [_p(680, 590), _p(830, 590), _p(830, 760), _p(750, 840), _p(750, 950), _p(750, 1075 - DY)]
AIR_IN = [_p(60, 950), _p(330, 950)]
AIR_OUT = [_p(330, 950), _p(330, 590), _p(400, 590)]
COMP, TURB = _p(330, 950), _p(750, 950)

# how brightly each part is drawn for each stage (1 = lit)
LIT = {
    "idle":       dict(engine=.4, exh=.4, turb=.4, shaft=.4, comp=.4, air_in=.4, air_out=.4),
    "air":        dict(engine=1, exh=.3, turb=.3, shaft=.3, comp=.3, air_in=1, air_out=1),
    "turbine":    dict(engine=.5, exh=1, turb=1, shaft=1, comp=.3, air_in=.3, air_out=.3),
    "compressor": dict(engine=.5, exh=.3, turb=.3, shaft=1, comp=1, air_in=1, air_out=1),
    "lag":        dict(engine=1, exh=1, turb=1, shaft=1, comp=1, air_in=1, air_out=1),
    "all":        dict(engine=1, exh=1, turb=1, shaft=1, comp=1, air_in=1, air_out=1),
}


def _point(pts, s):
    lens = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    target = s * sum(lens)
    for (a, b), n in zip(zip(pts, pts[1:]), lens):
        if target <= n:
            f = target / n if n else 0
            return a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
        target -= n
    return pts[-1]


def _pipe(d, col, pts, color, k):
    bg = col["bg"]
    d.line(pts, fill=_mix(bg, col["muted"], 0.15 + 0.4 * k), width=42, joint="curve")
    d.line(pts, fill=_mix(bg, color, 0.04 + 0.16 * k), width=32, joint="curve")


def _flow(d, col, pts, n, speed, sec, color_fn, k):
    bg = col["bg"]
    for i in range(n):
        s = (i / n + sec * speed) % 1.0
        x, y = _point(pts, s)
        c = _mix(bg, color_fn(s), 0.15 + 0.85 * k)
        d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=c)


def _wheel(d, col, centre, rot, color, k, radius=R):
    bg, (x, y) = col["bg"], centre
    r = radius
    d.ellipse([x - r - 10, y - r - 10, x + r + 10, y + r + 10], outline=_mix(bg, col["muted"], 0.3 + 0.5 * k), width=6)
    d.ellipse([x - r, y - r, x + r, y + r], fill=_mix(bg, color, 0.06 + 0.12 * k))
    for j in range(10):
        a = rot + 2 * math.pi * j / 10
        d.line([(x, y), (x + r * 0.95 * math.cos(a), y + r * 0.95 * math.sin(a))],
               fill=_mix(bg, color, 0.3 + 0.7 * k), width=7)
    d.ellipse([x - 14, y - 14, x + 14, y + 14], fill=col["text"])


def _omega(stage, sec):
    if stage == "idle":
        return 2.5
    if stage == "air":
        return 5.0
    if stage == "lag":
        return 2.0 + 9.0 * _ease((sec - 1.2) / 3.5)      # spins up slowly after the pedal press
    return 10.0


def _rotation(stage, sec):
    if stage != "lag":
        return _omega(stage, 0) * sec
    steps = int(sec / 0.02)
    return sum(_omega("lag", i * 0.02) * 0.02 for i in range(steps))


def draw_turbo(img, d, vis, scene_t, col, brand, ep, sec=0.0):
    stage = vis.get("stage", "all")
    k = LIT.get(stage, LIT["all"])
    bg = col["bg"]
    w = _omega(stage, sec)
    rot = _rotation(stage, sec)
    fast = 0.10 + 0.20 * w / 11.0                          # flow speed follows wheel speed

    # pipes first, then parts on top
    _pipe(d, col, EXH, col["accent"], k["exh"])
    _pipe(d, col, AIR_IN, col["tech"], k["air_in"])
    _pipe(d, col, AIR_OUT, col["tech"], k["air_out"])

    # engine block with four cylinders firing in turn
    x0, y0, x1, y1 = ENGINE
    y0, y1 = y0 + DY, y1 + DY
    d.rounded_rectangle([x0, y0, x1, y1], radius=18, fill=_mix(bg, col["muted"], 0.2 + 0.25 * k["engine"]),
                        outline=_mix(bg, col["muted"], 0.4 + 0.5 * k["engine"]), width=6)
    for c in range(4):
        cx = x0 + 28 + c * 64
        flash = max(0.0, math.sin(sec * 5 + c * 1.57)) ** 4 * k["engine"]
        d.rectangle([cx, y0 + 26, cx + 46, y0 + 120], fill=_mix(bg, col["accent"], 0.08 + 0.85 * flash))
    d.text(((x0 + x1) // 2, y1 - 28), "ENGINE", font=font(28), fill=_mix(bg, col["text"], 0.4 + 0.6 * k["engine"]), anchor="mm")

    # flows
    _flow(d, col, AIR_IN, 6, fast, sec, lambda s: col["tech"], k["air_in"])
    _flow(d, col, AIR_OUT, 12, fast, sec, lambda s: _mix(col["tech"], col["text"], 0.55), k["air_out"])
    _flow(d, col, EXH, 12, fast, sec,
          lambda s: col["accent"] if s < 0.6 else _mix(col["accent"], col["muted"], 0.7), k["exh"])

    # shaft and wheels
    d.rectangle([COMP[0] + 14, COMP[1] - 10, TURB[0] - 14, COMP[1] + 10], fill=_mix(bg, col["text"], 0.25 + 0.5 * k["shaft"]))
    _wheel(d, col, COMP, rot, col["tech"], k["comp"])
    _wheel(d, col, TURB, rot, col["accent"], k["turb"])
    if stage == "idle":                                     # hook: draw the eye to the exhaust side
        r = R + 18 + 5 * math.sin(sec * 4)
        d.ellipse([TURB[0] - r, TURB[1] - r, TURB[0] + r, TURB[1] + r], outline=col["accent"], width=5)

    # labels
    def lab(text, xy, key, color):
        d.text(xy, text, font=font(24), fill=_mix(bg, color, 0.35 + 0.65 * k[key]), anchor="mm")

    lab("AIR IN", (150, 915 + DY), "air_in", col["tech"])
    lab("COMPRESSED AIR", (185, 770 + DY), "air_out", col["tech"])
    lab("EXHAUST GAS", (925, 560 + DY), "exh", col["accent"])
    lab("COMPRESSOR", (COMP[0], 1105), "comp", col["tech"])
    lab("TURBINE", (955, TURB[1]), "turb", col["accent"])
    lab("EXHAUST OUT", (TURB[0], 1105), "exh", col["muted"] if stage != "turbine" else col["accent"])

    if stage == "lag":
        if sec > 0.8:
            a = _ease((sec - 0.8) * 4)
            d.text((W // 2, 492), "PEDAL DOWN!", font=font(46), fill=_mix(bg, col["accent"], a), anchor="mm")
        d.text((90, 1150), "TURBO SPEED", font=font(26), fill=col["text"], anchor="lm")
        d.rounded_rectangle([320, 1136, 990, 1164], radius=10, outline=col["muted"], width=3)
        fill_w = 670 * _ease((sec - 1.2) / 3.5)
        if fill_w > 6:
            d.rounded_rectangle([320, 1136, 320 + fill_w, 1164], radius=10, fill=col["accent"])

    if vis.get("callout"):
        a = _ease(sec * 3.0)
        size = 42
        while d.textlength(vis["callout"], font=font(size)) > W - 100 and size > 26:
            size -= 2
        d.text((W // 2, 1200), vis["callout"], font=font(size), fill=_mix(bg, col["accent"], a), anchor="mm")
    d.text((W // 2, 1252), "Simplified animation", font=font(24), fill=col["muted"], anchor="mm")
