"""Rocket steering in space (2D with a shaded 3D look), schematic.

  stage: space | push | gimbal | thrusters | wheels
Rocket sits at the centre of the frame and rotates there (no air, nothing to push on).
Shapes and speeds are illustrative, not an engineering drawing.
"""
import math
import random

from .common import font
from .visuals_jet import _mix, _ease

W, H = 1080, 1920
C = (540, 840)                       # rocket centre of mass


def _rot(p, a, o=(0.0, 0.0)):
    x, y = p[0] - o[0], p[1] - o[1]
    return (o[0] + x * math.cos(a) - y * math.sin(a), o[1] + x * math.sin(a) + y * math.cos(a))


def _place(pts, a):
    """Local coords (origin = centre of mass) -> screen, rotated by a."""
    return [(C[0] + q[0], C[1] + q[1]) for q in (_rot(p, a) for p in pts)]


def _stars(d, col, sec):
    rnd = random.Random(7)
    bg = col["bg"]
    for _ in range(46):
        x, y = rnd.uniform(30, W - 30), rnd.uniform(500, 1150)
        tw = 0.5 + 0.5 * math.sin(sec * 2 + x)
        r = rnd.choice([2, 2, 3])
        d.ellipse([x - r, y - r, x + r, y + r], fill=_mix(bg, col["text"], 0.25 + 0.4 * tw))


def _flame(d, col, nozzle_exit, direction, sec, power=1.0):
    """direction: unit vector the exhaust travels along (screen coords)."""
    bg = col["bg"]
    dx, dy = direction
    nx, ny = -dy, dx
    length = (150 + 26 * math.sin(sec * 30)) * power
    ex, ey = nozzle_exit
    for scale, c in ((1.0, _mix(bg, col["accent"], 0.9)), (0.62, _mix(col["accent"], col["text"], 0.6)),
                     (0.32, col["text"])):
        w = 26 * scale
        tip = (ex + dx * length * scale, ey + dy * length * scale)
        d.polygon([(ex + nx * w, ey + ny * w), tip, (ex - nx * w, ey - ny * w)], fill=c)
    for i in range(9):                                          # streaming exhaust gas
        s = (i / 9 + sec * 1.6) % 1.0
        dist = 40 + s * 330 * power
        off = 14 * math.sin(i * 2.3 + sec * 8) * s
        x, y = ex + dx * dist + nx * off, ey + dy * dist + ny * off
        r = 5 * (1 - 0.6 * s)
        d.ellipse([x - r, y - r, x + r, y + r], fill=_mix(bg, col["accent"], 0.9 * (1 - s)))


def _rocket(d, col, ang, gimbal=0.0, sec=0.0, flame=True):
    bg = col["bg"]
    # tail fins (behind the body)
    for sgn in (-1, 1):
        d.polygon(_place([(38 * sgn, 60), (88 * sgn, 135), (38 * sgn, 112)], ang), fill=_mix(bg, col["tech"], 0.6))
    # body with a lit left stripe and darker right edge for a rounded look
    d.polygon(_place([(-40, -150), (40, -150), (40, 112), (-40, 112)], ang), fill=_mix(bg, col["text"], 0.62))
    d.polygon(_place([(-40, -150), (-14, -150), (-14, 112), (-40, 112)], ang), fill=_mix(bg, col["text"], 0.85))
    d.polygon(_place([(20, -150), (40, -150), (40, 112), (20, 112)], ang), fill=_mix(bg, col["text"], 0.36))
    d.polygon(_place([(-40, -150), (40, -150), (0, -235)], ang), fill=col["accent"])
    d.polygon(_place([(-40, -150), (-14, -150), (-6, -190), (0, -235)], ang), fill=_mix(col["accent"], col["text"], 0.35))
    wx, wy = _place([(0, -60)], ang)[0]
    d.ellipse([wx - 17, wy - 17, wx + 17, wy + 17], fill=_mix(bg, col["tech"], 0.85), outline=col["muted"], width=4)
    d.polygon(_place([(-40, 20), (40, 20), (40, 34), (-40, 34)], ang), fill=_mix(bg, col["accent"], 0.8))
    # engine bell, swivelled about the hinge at the base of the body
    hinge = (0, 112)
    bell = [_rot(p, gimbal, hinge) for p in [(-20, 112), (20, 112), (34, 150), (-34, 150)]]
    d.polygon(_place(bell, ang), fill=_mix(bg, col["muted"], 0.95), outline=col["text"])
    if flame:
        exit_local = _rot((0, 150), gimbal, hinge)
        dir_local = _rot((0, 1), gimbal)
        (ex, ey), (px, py) = _place([exit_local], ang)[0], _place([dir_local], ang)[0]
        _flame(d, col, (ex, ey), (px - C[0], py - C[1]), sec)


def _puff(d, col, base, direction, sec, k):
    bg = col["bg"]
    dx, dy = direction
    nx, ny = -dy, dx
    bx, by = base
    for scale, c in ((1.0, _mix(bg, col["accent"], 0.9)), (0.5, col["text"])):
        L, w = 90 * k * scale, 16 * scale
        d.polygon([(bx + nx * w, by + ny * w), (bx + dx * L, by + dy * L), (bx - nx * w, by - ny * w)], fill=c)


def draw_rocket_steer(img, d, vis, scene_t, col, brand, ep, sec=0.0):
    stage = vis.get("stage", "space")
    bg = col["bg"]
    _stars(d, col, sec)

    if stage in ("space", "push"):
        _rocket(d, col, 0.0, 0.0, sec)
        if stage == "space":
            a = _ease(sec * 1.5)
            d.text((W // 2, 570), "NO AIR. NOTHING TO PUSH ON?", font=font(34), fill=_mix(bg, col["accent"], a), anchor="mm")
        else:
            a1, a2 = _ease((sec - 0.6) * 3), _ease((sec - 1.8) * 3)
            d.text((170, 950), "THE ROCKET PUSHES", font=font(26), fill=_mix(bg, col["muted"], a1), anchor="mm")
            d.text((170, 984), "THE GAS DOWN", font=font(26), fill=_mix(bg, col["accent"], a1), anchor="mm")
            d.text((910, 700), "THE GAS PUSHES", font=font(26), fill=_mix(bg, col["muted"], a2), anchor="mm")
            d.text((910, 734), "THE ROCKET UP", font=font(26), fill=_mix(bg, col["tech"], a2), anchor="mm")
            if a2 > 0.1:
                d.polygon([(910, 600), (886, 650), (934, 650)], fill=_mix(bg, col["tech"], a2))
            if a1 > 0.1:
                d.polygon([(170, 1070), (146, 1020), (194, 1020)], fill=_mix(bg, col["accent"], a1))
        _caption(d, col, vis, sec)
        return

    if stage == "gimbal":
        k = _ease((sec - 0.8) / 0.8)
        g = 0.32 * k
        ang = -0.65 * _ease((sec - 1.2) / 2.8)
        _rocket(d, col, ang, g, sec)
        if k > 0.1:
            d.text((W // 2, 590), "ENGINE SWIVELS: THE PUSH POINTS SIDEWAYS", font=font(30),
                   fill=_mix(bg, col["accent"], k), anchor="mm")

    elif stage == "thrusters":
        ang = 0.55 * _ease((sec - 1.0) / 2.2)
        _rocket(d, col, ang, 0.0, sec, flame=False)
        t = sec % 3.4
        if 1.0 < t < 2.4:                                    # a pair fires on opposite sides
            k = 1.0
            base1 = _place([(-42, -92)], ang)[0]
            base2 = _place([(42, 72)], ang)[0]
            d1 = _rot((-1, 0), ang)
            d2 = _rot((1, 0), ang)
            _puff(d, col, base1, d1, sec, k)
            _puff(d, col, base2, d2, sec, k)
        for loc in ((-42, -92), (42, 72)):
            x, y = _place([loc], ang)[0]
            d.ellipse([x - 8, y - 8, x + 8, y + 8], fill=col["accent"])
        d.text((W // 2, 590), "SMALL THRUSTERS FIRE IN PAIRS", font=font(30),
               fill=_mix(bg, col["accent"], _ease(sec * 2)), anchor="mm")

    elif stage == "wheels":
        ang = -0.55 * _ease((sec - 1.0) / 2.5)
        body = [(-110, -75), (110, -75), (110, 75), (-110, 75)]
        d.polygon(_place([(-300, -28), (-120, -28), (-120, 28), (-300, 28)], ang), fill=_mix(bg, col["tech"], 0.55))
        d.polygon(_place([(120, -28), (300, -28), (300, 28), (120, 28)], ang), fill=_mix(bg, col["tech"], 0.55))
        d.polygon(_place(body, ang), fill=_mix(bg, col["text"], 0.5), outline=col["text"])
        d.polygon(_place([(-110, -75), (-80, -75), (-80, 75), (-110, 75)], ang), fill=_mix(bg, col["text"], 0.8))
        wr = 56
        spin = 3.0 * sec + 4.0 * _ease((sec - 0.8) / 2.5) * sec
        d.ellipse([C[0] - wr - 8, C[1] - wr - 8, C[0] + wr + 8, C[1] + wr + 8], fill=_mix(bg, col["bg"], 1), outline=col["muted"], width=5)
        d.ellipse([C[0] - wr, C[1] - wr, C[0] + wr, C[1] + wr], fill=_mix(bg, col["accent"], 0.35))
        for j in range(6):
            a = spin + math.pi * j / 3
            d.line([(C[0], C[1]), (C[0] + wr * 0.9 * math.cos(a), C[1] + wr * 0.9 * math.sin(a))],
                   fill=_mix(bg, col["accent"], 0.95), width=7)
        d.ellipse([C[0] - 12, C[1] - 12, C[0] + 12, C[1] + 12], fill=col["text"])
        d.text((C[0], C[1] + 200), "SPINNING WHEEL INSIDE", font=font(26), fill=col["accent"], anchor="mm")
        d.text((W // 2, 590), "SPIN A WHEEL, THE SATELLITE TURNS", font=font(30),
               fill=_mix(bg, col["accent"], _ease(sec * 2)), anchor="mm")

    _caption(d, col, vis, sec)


def _caption(d, col, vis, sec):
    bg = col["bg"]
    if vis.get("callout"):
        a = _ease(sec * 3.0)
        size = 42
        while d.textlength(vis["callout"], font=font(size)) > W - 100 and size > 26:
            size -= 2
        d.text((W // 2, 1200), vis["callout"], font=font(size), fill=_mix(bg, col["accent"], a), anchor="mm")
    d.text((W // 2, 1252), "Simplified animation", font=font(24), fill=col["muted"], anchor="mm")
