"""Manual gearbox animation (2D with a 3D look: extruded, shaded gears), schematic.

  stage: engine | low | high | clutch | lug
A rev gauge sits on top (green band = the engine's best range). Below it a gear pair
(engine side -> wheel side), or the clutch discs. Shapes and speeds are illustrative.
"""
import math
import random

from .common import font
from .visuals_jet import _mix, _ease, RED

W, H = 1080, 1920
GY = 850                                   # gear centre line
BAND = (0.38, 0.72)                        # best-range band on the gauge (0..1)


def _gear_poly(cx, cy, r, teeth, rot, depth=16):
    pts = []
    for i in range(teeth * 2):
        a = rot + math.pi * i / teeth
        rr = r + depth if i % 2 == 0 else r
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


def _gear(d, col, cx, cy, r, rot, color, k=1.0, thick=34):
    """Extruded gear: stacked darker copies behind (thickness), then lit face and hub."""
    bg = col["bg"]
    teeth = max(8, int(r / 7))
    for layer in range(thick, 0, -3):                       # back to front
        shade = 0.10 + 0.25 * (1 - layer / thick)
        d.polygon(_gear_poly(cx + layer * 0.55, cy + layer * 0.45, r, teeth, rot),
                  fill=_mix(bg, color, shade * (0.4 + 0.6 * k)))
    d.polygon(_gear_poly(cx, cy, r, teeth, rot), fill=_mix(bg, color, 0.55 * (0.4 + 0.6 * k)),
              outline=_mix(bg, col["text"], 0.55 * k))
    # face shading: a lighter disc off-centre toward the light, then a recessed ring
    d.ellipse([cx - r * 0.82, cy - r * 0.82, cx + r * 0.82, cy + r * 0.82],
              fill=_mix(bg, color, 0.30 * (0.4 + 0.6 * k)))
    d.ellipse([cx - r * 0.74 - 5, cy - r * 0.74 - 5, cx + r * 0.50, cy + r * 0.50],
              fill=_mix(bg, color, 0.42 * (0.4 + 0.6 * k)))
    for j in range(4):                                       # spokes show the rotation
        a = rot + math.pi / 2 * j
        d.line([(cx, cy), (cx + r * 0.7 * math.cos(a), cy + r * 0.7 * math.sin(a))],
               fill=_mix(bg, col["text"], 0.45 * k), width=6)
    d.ellipse([cx - r * 0.22, cy - r * 0.22, cx + r * 0.22, cy + r * 0.22], fill=_mix(bg, col["text"], 0.8 * k))


def _gauge(d, col, pos, label_on=True, red=False):
    bg = col["bg"]
    x0, x1, y0, y1 = 120, 960, 560, 600
    d.rounded_rectangle([x0, y0, x1, y1], radius=14, outline=col["muted"], width=3)
    bx0, bx1 = x0 + (x1 - x0) * BAND[0], x0 + (x1 - x0) * BAND[1]
    d.rounded_rectangle([bx0, y0 + 5, bx1, y1 - 5], radius=10, fill=_mix(bg, col["tech"], 0.35))
    d.rounded_rectangle([x1 - 90, y0 + 5, x1 - 6, y1 - 5], radius=10, fill=_mix(bg, RED, 0.35))
    d.text((90, 535), "ENGINE SPEED", font=font(24), fill=col["muted"], anchor="lm")
    d.text(((bx0 + bx1) / 2, 656), "BEST RANGE", font=font(22), fill=col["tech"], anchor="mm")
    d.text((x1 - 48, 656), "REDLINE", font=font(22), fill=_mix(bg, RED, 0.9), anchor="mm")
    nx = x0 + (x1 - x0) * pos
    c = RED if red else col["accent"]
    d.polygon([(nx, y1 + 4), (nx - 14, y1 + 30), (nx + 14, y1 + 30)], fill=c)
    d.line([(nx, y0 - 6), (nx, y1 + 4)], fill=c, width=6)


def _pair(d, col, rl, rr, sec, w, tint_l, tint_r, k=1.0):
    """Engine-side gear (left) driving a wheel-side gear (right)."""
    cl = 540 - (2 * rl + 2 * rr + 20) / 2 + rl
    cr = cl + rl + rr + 20
    rot_l = w * sec
    rot_r = math.pi / max(8, int(rr / 7)) - rot_l * rl / rr
    _gear(d, col, cr, GY, rr, rot_r, col["accent"], tint_r)
    _gear(d, col, cl, GY, rl, rot_l, col["tech"], tint_l)
    d.text((cl, 1030), "ENGINE", font=font(26), fill=col["text"], anchor="mm")
    d.text((cr, 1030), "WHEELS", font=font(26), fill=col["text"], anchor="mm")


def _discs(d, col, sec):
    """Clutch: flywheel (engine) and clutch plate (gearbox). Pedal down opens the gap."""
    bg = col["bg"]
    t = sec % 5.0
    gap = 0.0
    if 1.2 < t < 3.8:
        gap = _ease(min((t - 1.2) / 0.5, 1.0, (3.8 - t) / 0.5))
    pedal = gap > 0.5
    cy = GY + 10
    fx = 400 - 50 * gap
    px = 620 + 50 * gap
    h = 230
    ew = 7.0 * sec
    gw = ew if gap < 0.15 else ew * (1 - gap * 0.8)           # gearbox side slows when the clutch is open
    # flywheel
    d.rounded_rectangle([fx - 46, cy - h / 2, fx, cy + h / 2], radius=10, fill=_mix(bg, col["tech"], 0.55),
                        outline=col["text"], width=3)
    # clutch plate
    d.rounded_rectangle([px, cy - h / 2, px + 46, cy + h / 2], radius=10, fill=_mix(bg, col["accent"], 0.55),
                        outline=col["text"], width=3)
    for i in range(7):                                         # moving stripes show rotation
        yy = (i / 7 + ew * 0.05) % 1.0 * (h - 30) + 15
        d.line([(fx - 40, cy - h / 2 + yy), (fx - 6, cy - h / 2 + yy)], fill=_mix(bg, col["text"], 0.7), width=4)
        yy = (i / 7 + gw * 0.05) % 1.0 * (h - 30) + 15
        d.line([(px + 6, cy - h / 2 + yy), (px + 40, cy - h / 2 + yy)], fill=_mix(bg, col["text"], 0.7), width=4)
    d.line([(fx - 46 - 90, cy), (fx - 46, cy)], fill=col["tech"], width=14)            # engine shaft
    d.line([(px + 46, cy), (px + 46 + 90, cy)], fill=col["accent"], width=14)          # gearbox shaft
    d.text((fx - 24, cy + h / 2 + 34), "FLYWHEEL", font=font(24), fill=col["tech"], anchor="mm")
    d.text((px + 24, cy + h / 2 + 34), "CLUTCH PLATE", font=font(24), fill=col["accent"], anchor="mm")
    d.text((fx - 100, cy - h / 2 - 28), "ENGINE", font=font(26), fill=col["text"], anchor="mm")
    d.text((px + 130, cy - h / 2 - 28), "GEARBOX", font=font(26), fill=col["text"], anchor="mm")
    msg, c = ("PEDAL DOWN: DISCONNECTED", RED) if pedal else ("PEDAL UP: CONNECTED", col["tech"])
    d.text((W // 2, cy + h / 2 + 110), msg, font=font(36), fill=c, anchor="mm")


def draw_gearbox(img, d, vis, scene_t, col, brand, ep, sec=0.0):
    stage = vis.get("stage", "engine")
    bg = col["bg"]
    pos, red = 0.55, False
    if stage == "engine":
        pos = 0.55 + 0.05 * math.sin(sec * 3)
    elif stage == "lug":
        if sec < 2.6:
            pos = 0.10 + 0.012 * math.sin(sec * 40)               # shaking at low speed
            red = True
        else:
            pos = 0.10 + 0.45 * _ease((sec - 2.6) / 1.0)
    _gauge(d, col, pos, red=red)

    if stage == "clutch":
        _discs(d, col, sec)
    else:
        if stage == "low":
            rl, rr = 70, 150
        elif stage == "high":
            rl, rr = 130, 100
        elif stage == "lug":
            rl, rr = (130, 100) if sec < 2.6 else (70, 150)
        else:
            rl, rr = 100, 120
        w = 3.0 if stage != "lug" or sec >= 2.6 else 1.0
        _pair(d, col, rl, rr, sec, w, 1.0, 1.0)
        tags = {"low": [("MORE PUSH", "tech"), ("LESS SPEED", "muted")],
                "high": [("LESS PUSH", "muted"), ("MORE SPEED", "tech")]}.get(stage)
        if tags:
            for i, (text, c) in enumerate(tags):
                a = _ease((sec - 0.6 - 0.6 * i) * 3)
                d.text((W // 2, 1095 + i * 44), text, font=font(34), fill=_mix(bg, col[c], a), anchor="mm")
        if stage == "lug":
            if sec < 2.6:
                d.text((W // 2, 1095), "LUGGING: HIGH GEAR, LOW SPEED", font=font(34), fill=RED, anchor="mm")
            else:
                a = _ease((sec - 2.6) * 3)
                d.text((W // 2, 1095), "DOWNSHIFT", font=font(40), fill=_mix(bg, col["accent"], a), anchor="mm")

    if vis.get("callout"):
        a = _ease(sec * 3.0)
        size = 42
        while d.textlength(vis["callout"], font=font(size)) > W - 100 and size > 26:
            size -= 2
        d.text((W // 2, 1200), vis["callout"], font=font(size), fill=_mix(bg, col["accent"], a), anchor="mm")
    d.text((W // 2, 1252), "Simplified animation", font=font(24), fill=col["muted"], anchor="mm")
