"""Nuclear power plant (civilian), simplified schematic with a shaded look.

  stage: plant | heat | turbine | pwr | rods
Heat in the reactor makes steam, steam spins a turbine, the turbine turns a generator.
`pwr` shows the two-loop version (hot pressurised water -> steam generator -> steam loop).
Illustrative, not an engineering drawing, and not to scale.
"""
import math

from .common import font
from .visuals_jet import _mix, _ease
from .visuals_turbo import _flow, _pipe, _wheel

W, H = 1080, 1920


def _layout(two_loop):
    if two_loop:
        return dict(vessel=(70, 640, 230, 980), sg=(320, 700, 440, 920),
                    loop1a=[(230, 730), (320, 730)], loop1b=[(320, 890), (230, 890)],
                    steam=[(380, 700), (380, 650), (560, 650), (560, 775)], turb=(560, 830),
                    ret=[(560, 885), (560, 1020), (380, 1020), (380, 920)],
                    gen=(650, 770, 810, 890), bulb=(930, 830))
    return dict(vessel=(100, 640, 300, 980), sg=None,
                steam=[(300, 700), (500, 700), (500, 775)], turb=(500, 830),
                ret=[(500, 885), (500, 1020), (200, 1020), (200, 980)],
                gen=(600, 770, 780, 890), bulb=(900, 830))


def _vessel(d, col, box, k, sec, rods_depth, glow):
    bg = col["bg"]
    x0, y0, x1, y1 = box
    d.rounded_rectangle([x0, y0, x1, y1], radius=24, fill=_mix(bg, col["muted"], 0.15 + 0.2 * k),
                        outline=_mix(bg, col["text"], 0.35 + 0.6 * k), width=6)
    d.rounded_rectangle([x0 + 10, y0 + 140, x1 - 10, y1 - 10], radius=16, fill=_mix(bg, col["tech"], 0.10 + 0.15 * k))
    n = 5
    for i in range(n):                                         # fuel rods
        x = x0 + (x1 - x0) * (i + 0.5) / n
        g = glow * (0.65 + 0.35 * math.sin(sec * 4 + i))
        d.rounded_rectangle([x - 8, y0 + 220, x + 8, y1 - 30], radius=6, fill=_mix(bg, col["accent"], 0.15 + 0.85 * g * k))
    for i in range(n - 1):                                     # control rods between them
        x = x0 + (x1 - x0) * (i + 1) / n
        yb = y0 - 40 + (220 + 40) * rods_depth
        d.line([(x, y0 - 40), (x, yb)], fill=_mix(bg, col["text"], 0.7), width=7)
        d.rectangle([x - 6, y0 - 46, x + 6, y0 - 34], fill=col["muted"])
    for i in range(8):                                         # bubbles rising
        s = (i / 8 + sec * 0.28) % 1.0
        bx = x0 + 24 + (i * 37) % (x1 - x0 - 48)
        by = y1 - 36 - s * (y1 - y0 - 200)
        d.ellipse([bx - 5, by - 5, bx + 5, by + 5], fill=_mix(bg, col["text"], 0.5 * k * (1 - 0.5 * s)))


def _bulb(d, col, pos, k):
    bg = col["bg"]
    x, y = pos
    for r, a in ((78, 0.07), (56, 0.12), (40, 0.2)):
        d.ellipse([x - r, y - r, x + r, y + r], fill=_mix(bg, col["accent"], a * k))
    d.ellipse([x - 28, y - 28, x + 28, y + 28], fill=_mix(bg, col["accent"], 0.25 + 0.75 * k), outline=col["text"], width=3)
    d.rectangle([x - 16, y + 28, x + 16, y + 46], fill=_mix(bg, col["muted"], 0.8))


def draw_reactor(img, d, vis, scene_t, col, brand, ep, sec=0.0):
    stage = vis.get("stage", "plant")
    bg = col["bg"]
    two = stage == "pwr"
    L = _layout(two)
    K = {"plant": dict(v=.8, s=.8, t=.8, g=.8, b=.7, r=.8),
         "heat": dict(v=1, s=.3, t=.3, g=.3, b=.2, r=.3),
         "turbine": dict(v=.5, s=1, t=1, g=1, b=1, r=1),
         "pwr": dict(v=1, s=1, t=1, g=1, b=1, r=1),
         "rods": dict(v=1, s=.5, t=.5, g=.5, b=.4, r=.5)}[stage]
    glow, depth = 0.9, 0.0
    if stage == "rods":
        ph = (sec % 6.0) / 6.0
        depth = _ease(ph * 2) if ph < 0.5 else 1 - _ease((ph - 0.5) * 2)       # in, then out
        glow = 1.0 - 0.75 * depth
    elif stage == "heat":
        glow = 0.6 + 0.4 * _ease(sec / 2.0)

    # pipes first
    _pipe(d, col, L["steam"], col["accent"], K["s"])
    _pipe(d, col, L["ret"], col["tech"], K["r"])
    if two:
        _pipe(d, col, L["loop1a"], (230, 80, 60), K["v"])
        _pipe(d, col, L["loop1b"], col["tech"], K["v"])
        sx0, sy0, sx1, sy1 = L["sg"]
        d.rounded_rectangle([sx0, sy0, sx1, sy1], radius=18, fill=_mix(bg, col["accent"], 0.10 + 0.15 * K["s"]),
                            outline=_mix(bg, col["text"], 0.35 + 0.6 * K["s"]), width=6)
        for i in range(4):                                     # hot tubes inside the steam generator
            y = sy0 + 50 + i * 50
            d.line([(sx0 + 18, y), (sx1 - 18, y)], fill=_mix(bg, (230, 80, 60), 0.5 + 0.4 * K["v"]), width=6)

    _vessel(d, col, L["vessel"], K["v"], sec, depth, glow)

    # turbine + generator
    tx, ty = L["turb"]
    rot = 9.0 * sec * K["t"]
    _wheel(d, col, (tx, ty), rot, col["accent"], K["t"], radius=55)
    gx0, gy0, gx1, gy1 = L["gen"]
    d.rectangle([tx + 55, ty - 8, gx0, ty + 8], fill=_mix(bg, col["text"], 0.25 + 0.5 * K["g"]))
    d.rounded_rectangle([gx0, gy0, gx1, gy1], radius=16, fill=_mix(bg, col["tech"], 0.10 + 0.22 * K["g"]),
                        outline=_mix(bg, col["tech"], 0.35 + 0.65 * K["g"]), width=6)
    d.text(((gx0 + gx1) // 2, ty), "GEN", font=font(34), fill=_mix(bg, col["tech"], 0.4 + 0.6 * K["g"]), anchor="mm")
    wire = [(gx1, ty), (L["bulb"][0] - 40, ty)]
    d.line(wire, fill=_mix(bg, col["tech"], 0.3 + 0.7 * K["b"]), width=6)
    _bulb(d, col, L["bulb"], K["b"])

    # flows
    _flow(d, col, L["steam"], 7, 0.22, sec, lambda s: _mix(col["accent"], col["text"], 0.5), K["s"])
    _flow(d, col, L["ret"], 7, 0.22, sec, lambda s: col["tech"], K["r"])
    _flow(d, col, wire, 3, 0.3, sec, lambda s: col["accent"], K["b"])
    if two:
        _flow(d, col, L["loop1a"], 3, 0.25, sec, lambda s: (240, 100, 70), K["v"])
        _flow(d, col, L["loop1b"], 3, 0.25, sec, lambda s: col["tech"], K["v"])

    # labels
    def lab(text, x, y, color, size=26):
        d.text((x, y), text, font=font(size), fill=color, anchor="mm")
    vx = (L["vessel"][0] + L["vessel"][2]) // 2
    lab("REACTOR", vx, 1100, _mix(bg, col["text"], 0.4 + 0.6 * K["v"]))
    lab("TURBINE", tx, 1100, _mix(bg, col["text"], 0.4 + 0.6 * K["t"]))
    lab("ELECTRICITY", L["bulb"][0] - 10, 940 if two else 930, _mix(bg, col["accent"], 0.4 + 0.6 * K["b"]), 24)
    if two:
        lab("STEAM GENERATOR", 380, 960, _mix(bg, col["text"], 0.4 + 0.6 * K["s"]), 22)

    title = {"plant": "A WAY TO BOIL WATER", "heat": "ATOMS SPLIT AND RELEASE HEAT",
             "turbine": "STEAM SPINS THE TURBINE", "pwr": "TWO LOOPS: PRESSURE KEEPS IT FROM BOILING",
             "rods": ""}[stage]
    if stage == "rods":
        title = "RODS IN: SLOWER" if depth > 0.5 else "RODS OUT: FASTER"
    d.text((W // 2, 560), title, font=font(32), fill=_mix(bg, col["accent"], _ease(sec * 2)), anchor="mm")

    if vis.get("callout"):
        a = _ease(sec * 3.0)
        size = 42
        while d.textlength(vis["callout"], font=font(size)) > W - 100 and size > 26:
            size -= 2
        d.text((W // 2, 1200), vis["callout"], font=font(size), fill=_mix(bg, col["accent"], a), anchor="mm")
    d.text((W // 2, 1252), "Simplified animation", font=font(24), fill=col["muted"], anchor="mm")
