"""Jet-engine animations drawn with Pillow (2D, simplified).

  jet_hook       engine + a bar race: gas temperature vs what the metal can survive
  jet_engine     cutaway engine; `stage` highlights intake / compression / combustion / exhaust
  blade_cooling  close-up of a cooled turbine blade: hot gas outside, cool air inside and in a film

All functions share the renderer signature (img, d, vis, scene_t, col, brand, ep, sec) where `sec`
is real seconds into the scene, so motion speed does not depend on how long a scene is.
Everything is schematic: shapes and speeds are illustrative, not engineering drawings.
"""
import math
import random

from .common import font

W, H = 1080, 1920
RED = (255, 86, 64)          # "danger" colour used only for heat warnings


def _mix(c1, c2, a):
    a = max(0.0, min(1.0, a))
    return tuple(int(c1[i] * (1 - a) + c2[i] * a) for i in range(3))


def _ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


# ---------------------------------------------------------------- engine geometry (x, half-height)
PROFILE = [(70, 150), (230, 150), (270, 100), (480, 58), (520, 78), (650, 78),
           (700, 62), (830, 84), (910, 72), (1010, 46)]
CX0, CX1 = 70, 1010
STAGE_ORDER = ["intake", "compression", "combustion", "exhaust"]
JET_NAMES = ["INTAKE", "COMPRESSION", "COMBUSTION", "EXHAUST"]


def _half(x):
    if x <= PROFILE[0][0]:
        return PROFILE[0][1]
    for (x0, h0), (x1, h1) in zip(PROFILE, PROFILE[1:]):
        if x <= x1:
            return h0 + (h1 - h0) * (x - x0) / (x1 - x0)
    return PROFILE[-1][1]


def _zone(x):
    if x < 235:
        return "intake"
    if x < 500:
        return "compression"
    if x < 655:
        return "combustion"
    return "exhaust"


def _zone_color(col, z, x):
    if z == "intake":
        return col["tech"]
    if z == "compression":
        return _mix(col["tech"], col["text"], 0.15 + 0.5 * (x - 235) / 265)
    if z == "combustion":
        return col["accent"]
    return _mix(col["accent"], col["muted"], 0.2 + 0.7 * (x - 655) / 355)


_rng = random.Random(5)
_PARTS = [(_rng.uniform(-1, 1), _rng.random()) for _ in range(80)]


def _rotor(d, cy, x, n, radius, rot, color):
    for j in range(n):
        ang = 2 * math.pi * j / n + rot
        d.line([(x, cy), (x, cy + radius * math.cos(ang))], fill=color, width=3 + int(4 * abs(math.sin(ang))))


def draw_engine(d, col, cy, vs, active, sec, hot=False, labels=True):
    bg = col["bg"]

    def lit(z):
        return active in ("all", z)

    # gas path, coloured by zone; the active zone is bright
    for x in range(CX0, CX1, 6):
        z = _zone(x)
        a = 0.5 if lit(z) else 0.1
        if z == "combustion" and lit(z):
            a = 0.6 + 0.2 * math.sin(sec * 12 + x * 0.05)
        h = _half(x + 3) * vs
        d.rectangle([x, cy - h, x + 6, cy + h], fill=_mix(bg, _zone_color(col, z, x), a))

    # walls, outer casing, shaft, nose cone
    xs = list(range(CX0, CX1 + 1, 10))
    d.line([(x, cy - _half(x) * vs) for x in xs], fill=col["muted"], width=10)
    d.line([(x, cy + _half(x) * vs) for x in xs], fill=col["muted"], width=10)
    casing = _mix(bg, col["muted"], 0.6)
    d.line([(x, cy - _half(x) * vs - 24) for x in xs], fill=casing, width=4)
    d.line([(x, cy + _half(x) * vs + 24) for x in xs], fill=casing, width=4)
    d.rectangle([130, cy - 12 * vs, 830, cy + 12 * vs], fill=_mix(bg, col["muted"], 0.8))
    d.polygon([(CX0 + 10, cy), (130, cy - 26 * vs), (130, cy + 26 * vs)], fill=col["muted"])

    # rotating blades (side view: each blade's visible length follows cos of its angle)
    rot = sec * 7.5
    _rotor(d, cy, 140, 8, _half(140) * vs * 0.95, rot, col["text"])
    for x in range(275, 480, 40):
        _rotor(d, cy, x, 9, _half(x) * vs * 0.9, rot, _mix(col["tech"], col["text"], 0.5))
        h = _half(x + 18) * vs
        for sgn in (-1, 1):                       # fixed guide vanes
            d.line([(x + 18, cy + sgn * h), (x + 18, cy + sgn * h * 0.62)], fill=col["muted"], width=4)
    turb = RED if hot else col["accent"]
    for x in (690, 735, 780):
        _rotor(d, cy, x, 9, _half(x) * vs * 0.9, rot, turb)

    # fuel injectors and flame
    for k in range(3):
        xk = 530 + k * 45
        wall = cy - _half(xk) * vs
        d.line([(xk, wall - 14), (xk, wall + 10)], fill=col["text"], width=6)
        if lit("combustion"):
            yy = wall + 10 + ((sec * 1.8 + k * 0.33) % 1) * 38 * vs
            d.ellipse([xk - 4, yy - 4, xk + 4, yy + 4], fill=col["text"])
    if lit("combustion"):
        for k in range(6):
            fx = 520 + k * 22
            fr = (18 + 8 * math.sin(sec * 13 + k * 1.9)) * vs
            fy = cy + 30 * math.sin(sec * 9 + k * 2.3) * vs
            c = _mix(col["accent"], RED, 0.3 + 0.3 * math.sin(sec * 7 + k))
            d.ellipse([fx - fr, fy - fr * 0.8, fx + fr, fy + fr * 0.8], fill=c)
            d.ellipse([fx - fr * 0.5, fy - fr * 0.4, fx + fr * 0.5, fy + fr * 0.4], fill=_mix(c, col["text"], 0.55))

    # air / gas particles flowing left to right, faster toward the nozzle
    for lane, u0 in _PARTS:
        s = (u0 + sec * 0.16) % 1.0
        x = CX0 + 25 + (CX1 - CX0 - 45) * (s ** 1.25)
        y = cy + lane * _half(x) * vs * 0.8
        z = _zone(x)
        c = _mix(bg, _zone_color(col, z, x), 1.0 if lit(z) else 0.3)
        tail = 10 + 14 * s * s
        d.line([(x - tail, y), (x, y)], fill=c, width=5)
        d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=c)

    if labels:
        names = [("FAN", 140, 0, "intake"), ("COMPRESSOR", 375, 1, "compression"),
                 ("COMBUSTOR", 580, 0, "combustion"), ("TURBINE", 735, 1, "exhaust"), ("NOZZLE", 940, 0, "exhaust")]
        base = cy + 150 * vs + 52
        for name, x, row, z in names:
            if active == "all":
                c = col["text"]
            else:
                c = col["accent"] if z == active else col["muted"]
            d.text((x, base + row * 36), name, font=font(24), fill=c, anchor="mm")


def _chips(d, col, y, idx):
    x0, w = 45, 240
    for i, name in enumerate(JET_NAMES):
        on = i == idx
        box = [x0 + i * (w + 10), y, x0 + i * (w + 10) + w, y + 50]
        d.rounded_rectangle(box, radius=14, fill=col["accent"] if on else col["bg"],
                            outline=col["accent"] if on else col["muted"], width=3)
        d.text(((box[0] + box[2]) // 2, (box[1] + box[3]) // 2), name, font=font(24),
               fill=col["bg"] if on else col["muted"], anchor="mm")


# ---------------------------------------------------------------- scene: engine stages
def draw_jet_engine(img, d, vis, scene_t, col, brand, ep, sec=0.0):
    stage = vis.get("stage", "all")
    draw_engine(d, col, cy=830, vs=1.0, active=stage, sec=sec)
    idx = STAGE_ORDER.index(stage) if stage in STAGE_ORDER else None
    _chips(d, col, 1150, idx)
    d.text((W // 2, 1232), "Simplified animation", font=font(24), fill=col["muted"], anchor="mm")
    if vis.get("callout"):
        a = _ease(sec * 3.0)
        size = 66
        while d.textlength(vis["callout"], font=font(size)) > W - 100 and size > 30:
            size -= 2                                   # shrink long captions to fit the frame
        d.text((W // 2, 520), vis["callout"], font=font(size), fill=_mix(col["bg"], col["accent"], a), anchor="mm")
        if vis.get("callout_sub"):
            d.text((W // 2, 585), vis["callout_sub"], font=font(30), fill=_mix(col["bg"], col["text"], a), anchor="mm")


# ---------------------------------------------------------------- scene: the hook
def draw_jet_hook(img, d, vis, scene_t, col, brand, ep, sec=0.0):
    draw_engine(d, col, cy=640, vs=0.6, active="all", sec=sec, hot=True, labels=False)
    x0, limit, full = 90, 380, 880
    grow = _ease((sec - 0.5) / 2.6)
    gas = full * grow

    d.text((x0, 828), "WHAT THE METAL CAN SURVIVE", font=font(30), fill=col["tech"], anchor="lm")
    d.rounded_rectangle([x0, 860, x0 + limit, 914], radius=10, fill=col["tech"])
    d.text((x0, 958), "THE GAS INSIDE THE ENGINE", font=font(30), fill=col["accent"], anchor="lm")
    if gas > 0:
        d.rounded_rectangle([x0, 990, x0 + min(gas, limit), 1044], radius=10, fill=col["accent"])
    if gas > limit:
        flash = 0.6 + 0.4 * math.sin(sec * 14)
        d.rectangle([x0 + limit, 990, x0 + gas, 1044], fill=_mix(col["accent"], RED, flash))
    for lo, hi in ((850, 926), (980, 1056)):             # the limit line, bar rows only
        for y in range(lo, hi, 16):
            d.line([(x0 + limit, y), (x0 + limit, min(y + 8, hi))], fill=col["text"], width=4)
    if grow > 0.9:
        a = _ease((grow - 0.9) * 10)
        d.text((x0 + gas - 18, 1017), "1,500°C+", font=font(40), fill=_mix(RED, col["bg"], a), anchor="rm")
    d.text((W // 2, 1095), "Bar lengths are illustrative", font=font(24), fill=col["muted"], anchor="mm")


# ---------------------------------------------------------------- scene: blade cooling close-up
def _naca(x, t=0.30):
    """Half-thickness of a symmetric aerofoil (NACA 4-digit form), x in [0, 1]."""
    return 5 * t * (0.2969 * math.sqrt(x) - 0.1260 * x - 0.3516 * x ** 2 + 0.2843 * x ** 3 - 0.1015 * x ** 4)


_r2 = random.Random(9)
_GAS = [(_r2.choice((-1, 1)), _r2.choice((30, 60, 90)), _r2.random()) for _ in range(44)]


def draw_blade_cooling(img, d, vis, p, col, brand, ep, sec=0.0):
    bg = col["bg"]
    C, X0, cy = 620, 230, 810

    def X(f):
        return X0 + f * C

    def yt(f):
        return _naca(min(1.0, max(0.0, f))) * C

    # hot gas streaming past (always on)
    for side, dist, u0 in _GAS:
        s = (u0 + sec * 0.30) % 1.0
        x = 40 + s * 1000
        y = cy + side * (yt((x - X0) / C) + dist)
        c = _mix(col["accent"], RED, (x - X0) / 900)
        d.line([(x - 22, y), (x, y)], fill=c, width=5)
    d.text((W // 2, 520), "HOT GAS  1,500°C+", font=font(40), fill=col["accent"], anchor="mm")

    # the blade: starts red-hot, cools to steel once the cooling air arrives
    glow = 1 - _ease((p - 0.30) / 0.30)
    steel = _mix(bg, col["muted"], 0.75)
    fill = _mix(steel, RED, 0.8 * glow)
    fs = [i / 48 for i in range(49)]
    top = [(X(f), cy - yt(f)) for f in fs]
    bot = [(X(f), cy + yt(f)) for f in fs]
    d.polygon(top + bot[::-1], fill=fill)
    d.line(top, fill=col["text"], width=4)
    d.line(bot, fill=col["text"], width=4)

    # cooling air: pipe, hollow chambers, passages to the surface holes
    reveal = _ease((p - 0.22) / 0.12)
    if reveal > 0:
        cool = _mix(bg, col["tech"], 0.55 * reveal)

        def chamber(f0, f1, k):
            ff = [f0 + (f1 - f0) * i / 20 for i in range(21)]
            return [(X(f), cy - k * yt(f)) for f in ff] + [(X(f), cy + k * yt(f)) for f in ff[::-1]]

        d.polygon(chamber(0.10, 0.42, 0.55), fill=cool)
        d.polygon(chamber(0.48, 0.80, 0.50), fill=cool)
        d.rectangle([X(0.42), cy - 8, X(0.48), cy + 8], fill=cool)
        px = X(0.26)
        d.rectangle([px - 26, cy + 0.55 * yt(0.26), px + 26, cy + 360], fill=cool, outline=col["tech"], width=3)
        for k in range(5):                                          # air rising up the pipe
            yy = cy + 360 - ((k / 5 + sec * 0.6) % 1) * (360 - 0.55 * yt(0.26))
            d.ellipse([px - 6, yy - 6, px + 6, yy + 6], fill=col["tech"])
        for k in range(8):                                          # air spreading inside
            fx = 0.12 + ((k / 8 + sec * 0.35) % 1) * 0.28
            yy = cy + math.sin(k * 2.1 + sec * 3) * 0.35 * yt(fx)
            d.ellipse([X(fx) - 5, yy - 5, X(fx) + 5, yy + 5], fill=col["tech"])

    holes = [0.03, 0.07, 0.12, 0.18, 0.25]
    if p > 0.45:
        a = _ease((p - 0.45) / 0.1)
        line_c = _mix(bg, col["tech"], a)
        for side in (-1, 1):
            for f in holes:
                d.line([(X(0.16), cy + side * 0.5 * yt(0.16)), (X(f), cy + side * yt(f))], fill=line_c, width=3)
                hx, hy = X(f), cy + side * yt(f)
                d.ellipse([hx - 6, hy - 6, hx + 6, hy + 6], fill=bg, outline=line_c, width=3)

    if p > 0.55:                                                    # the protective film
        a = _ease((p - 0.55) / 0.15)
        film_c = _mix(bg, col["tech"], a)
        for side in (-1, 1):
            d.line([(X(f), cy + side * (yt(f) + 9)) for f in [0.03 + i * 0.02 for i in range(42)]],
                   fill=film_c, width=5)
            for k in range(10):
                f = 0.03 + ((k / 10 + sec * 0.55) % 1) * 0.8
                y = cy + side * (yt(f) + 9)
                d.ellipse([X(f) - 4, y - 4, X(f) + 4, y + 4], fill=film_c)

    # captions appear one at a time
    if p > 0.28:
        a = _ease((p - 0.28) / 0.08)
        d.text((X(0.26), cy + 395), "COOL AIR FROM THE COMPRESSOR", font=font(28),
               fill=_mix(bg, col["tech"], a), anchor="mm")
    if p > 0.48:
        a = _ease((p - 0.48) / 0.08)
        c = _mix(bg, col["text"], a)
        d.text((X(0.07), 575), "TINY COOLING HOLES", font=font(28), fill=c, anchor="mm")
        d.line([(X(0.07), 595), (X(0.07), cy - yt(0.07) - 12)], fill=c, width=3)
    if p > 0.62:
        a = _ease((p - 0.62) / 0.08)
        c = _mix(bg, col["tech"], a)
        d.text((X(0.62) + 60, 575), "PROTECTIVE LAYER", font=font(28), fill=c, anchor="mm")
        d.line([(X(0.55), 595), (X(0.55), cy - yt(0.55) - 14)], fill=c, width=3)
    d.text((W // 2, 1250), "Simplified illustration", font=font(24), fill=col["muted"], anchor="mm")
