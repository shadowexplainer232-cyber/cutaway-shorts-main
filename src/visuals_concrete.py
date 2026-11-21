"""Roman concrete (2D with a shaded 3D look), schematic.

  stage: mix | dome | clast | heal   (heal takes `speed:` to play faster, e.g. in the hook)
mix    volcanic ash + lime go into a block of concrete
dome   shaded dome and drum (the Pantheon's shape, simplified)
clast  cross-section with white lime chunks highlighted
heal   a crack runs through a lime chunk, water arrives, the crack seals
Shapes and timings are illustrative, not a scientific drawing.
"""
import math
import random

from .common import font
from .visuals_jet import _mix, _ease

W, H = 1080, 1920
X0, X1, Y0, Y1 = 140, 940, 620, 1060            # cross-section block
CLAST = (540, 840)                              # the lime chunk the crack passes through
CRACK = [(468, 620), (500, 700), (478, 770), (540, 835), (578, 905), (552, 975), (592, 1060)]


def _blob(rnd, cx, cy, r, n=9):
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        rr = r * rnd.uniform(0.75, 1.15)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


def _section(d, col, highlight_clasts, k=1.0):
    bg = col["bg"]
    rnd = random.Random(11)
    d.rounded_rectangle([X0, Y0, X1, Y1], radius=18, fill=_mix(bg, col["muted"], 0.30))
    for _ in range(240):                                     # fine grains
        x, y, r = rnd.uniform(X0 + 12, X1 - 12), rnd.uniform(Y0 + 12, Y1 - 12), rnd.uniform(2, 5)
        d.ellipse([x - r, y - r, x + r, y + r], fill=_mix(bg, col["muted"], rnd.uniform(0.18, 0.55)))
    for _ in range(13):                                      # stones
        x, y = rnd.uniform(X0 + 60, X1 - 60), rnd.uniform(Y0 + 60, Y1 - 60)
        d.polygon(_blob(rnd, x, y, rnd.uniform(26, 46)), fill=_mix(bg, col["text"], rnd.uniform(0.22, 0.34)))
    spots = [CLAST, (250, 720), (800, 700), (270, 960), (790, 980)]
    for i, (x, y) in enumerate(spots):                       # lime clasts
        r = 30 if i == 0 else rnd.uniform(18, 26)
        d.polygon(_blob(rnd, x, y, r), fill=_mix(bg, col["text"], 0.95))
    d.rounded_rectangle([X0, Y0, X1, Y1], radius=18, outline=col["text"], width=4)
    if highlight_clasts:
        for i, (x, y) in enumerate(spots):
            r = (40 if i == 0 else 34) + 4 * math.sin(highlight_clasts * 4 + i)
            d.ellipse([x - r, y - r, x + r, y + r], outline=col["accent"], width=4)


def _polyline_part(pts, frac):
    """First `frac` of a polyline by length."""
    lens = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    target, out = frac * sum(lens), [pts[0]]
    for (a, b), n in zip(zip(pts, pts[1:]), lens):
        if target >= n:
            out.append(b)
            target -= n
        else:
            f = target / n if n else 0
            out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
            break
    return out


def _stage_heal(d, col, sec):
    bg = col["bg"]
    _section(d, col, 0)
    p1 = _ease((sec - 0.5) / 1.6)
    crack = _polyline_part(CRACK, p1)
    if len(crack) > 1:
        d.line(crack, fill=_mix(bg, (0, 0, 0), 0.95), width=9, joint="curve")
    # water drops fall onto the crack
    if 2.4 < sec < 4.6:
        for i in range(6):
            s = ((sec - 2.4) * 0.9 + i / 6) % 1.0
            x = CRACK[0][0] + 14 * i - 30
            y = 560 + s * 90
            d.ellipse([x - 6, y - 6, x + 6, y + 8], fill=col["tech"])
        d.text((W // 2, 530), "WATER SEEPS IN", font=font(30), fill=col["tech"], anchor="mm")
    p2 = _ease((sec - 3.0) / 2.4)
    if p2 > 0:                                               # white mineral grows outward from the lime chunk
        mid = 3.3 / 7.0                                      # where the clast sits along the crack (approx.)
        lo = _polyline_part(CRACK, max(0.0, mid - mid * p2))
        full_to_mid = _polyline_part(CRACK, mid)
        seg_a = full_to_mid[len(lo) - 1:] if len(lo) > 1 else full_to_mid
        hi = _polyline_part(CRACK, mid + (1 - mid) * p2)
        seg_b = hi[len(full_to_mid) - 1:] if len(hi) >= len(full_to_mid) else []
        for seg in (seg_a, seg_b):
            if len(seg) > 1:
                d.line(seg, fill=col["text"], width=11, joint="curve")
    msg = "A CRACK FORMS"
    c = col["accent"]
    if sec > 2.4:
        msg, c = "WATER MEETS THE LIME", col["tech"]
    if sec > 4.4:
        msg, c = "THE CRACK SEALS ITSELF", col["accent"]
    if sec < 2.4:
        d.text((W // 2, 530), msg, font=font(30), fill=c, anchor="mm")
    elif sec > 4.6:
        d.text((W // 2, 530), msg, font=font(30), fill=c, anchor="mm")
    d.text((CLAST[0] + 125, CLAST[1] + 10), "LIME CHUNK", font=font(24), fill=col["accent"], anchor="lm")


def _stage_mix(d, col, sec):
    bg = col["bg"]
    t = _ease(sec / 3.0)
    # block fills as the piles shrink
    d.rounded_rectangle([340, 700, 740, 900], radius=18, fill=_mix(bg, col["muted"], 0.15 + 0.3 * t),
                        outline=col["text"], width=4)
    rnd = random.Random(5)
    for _ in range(int(160 * t)):
        x, y = rnd.uniform(352, 728), rnd.uniform(712, 888)
        d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=_mix(bg, col["muted"] if rnd.random() < 0.5 else col["text"], rnd.uniform(0.3, 0.9)))
    d.text((540, 800), "ROMAN CONCRETE", font=font(30), fill=_mix(bg, col["text"], t), anchor="mm")
    # piles
    for cx, color, label in ((230, col["muted"], "VOLCANIC ASH"), (850, col["text"], "LIME")):
        h = 180 * (1 - 0.7 * t)
        d.polygon([(cx - 110, 980), (cx, 980 - h), (cx + 110, 980)], fill=_mix(bg, color, 0.7))
        d.polygon([(cx - 110, 980), (cx, 980 - h), (cx - 20, 980)], fill=_mix(bg, color, 0.95))
        d.text((cx, 1030), label, font=font(28), fill=col["text"], anchor="mm")
        for i in range(7):                                   # grains flying into the block
            s = (i / 7 + sec * 0.5) % 1.0
            x0, y0 = cx, 940
            x1, y1 = 540, 840
            x, y = x0 + (x1 - x0) * s, y0 + (y1 - y0) * s - 110 * math.sin(math.pi * s)
            d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=_mix(bg, color, 0.9))
    d.text((W // 2, 590), "ASH + LIME PASTE = DURABLE MORTAR", font=font(30),
           fill=_mix(bg, col["accent"], _ease(sec * 2)), anchor="mm")


def _stage_dome(d, col, sec):
    bg = col["bg"]
    cx, base, R = 540, 930, 270
    for i in range(14):                                      # shaded layers give a rounded look
        f = i / 13
        r = R * (1 - 0.05 * i)
        ox, oy = -34 * f, -12 * f
        pts = [(cx + ox + r * math.cos(math.pi + math.pi * j / 40), base + oy - r * 0.95 * math.sin(math.pi * j / 40))
               for j in range(41)]
        d.polygon(pts, fill=_mix(bg, col["text"], 0.20 + 0.04 * i))
    for j in range(1, 8):                                    # ribs
        a = math.pi * j / 8
        d.line([(cx + R * 0.1 * math.cos(math.pi + a), base - 20),
                (cx + R * 0.96 * math.cos(math.pi + a), base - R * 0.91 * math.sin(a))],
               fill=_mix(bg, col["muted"], 0.5), width=2) if False else None
    d.ellipse([cx - 34, base - R * 0.95 - 8, cx + 34, base - R * 0.95 + 22], fill=bg, outline=col["accent"], width=4)
    d.rectangle([cx - R - 10, base, cx + R + 10, base + 110], fill=_mix(bg, col["text"], 0.45), outline=col["text"], width=3)
    for i in range(1, 9):
        x = cx - R - 10 + i * (2 * R + 20) / 9
        d.line([(x, base + 8), (x, base + 102)], fill=_mix(bg, col["muted"], 0.8), width=4)
    a = _ease(sec * 1.2)
    d.text((W // 2, 590), "THE PANTHEON'S DOME", font=font(34), fill=_mix(bg, col["accent"], a), anchor="mm")
    d.text((W // 2, 1100), "NO STEEL INSIDE", font=font(30), fill=_mix(bg, col["tech"], _ease((sec - 1.0) * 2)), anchor="mm")


def draw_concrete(img, d, vis, scene_t, col, brand, ep, sec=0.0):
    stage = vis.get("stage", "heal")
    bg = col["bg"]
    s = sec * float(vis.get("speed", 1.0))
    if stage == "mix":
        _stage_mix(d, col, sec)
    elif stage == "dome":
        _stage_dome(d, col, sec)
    elif stage == "clast":
        _section(d, col, sec)
        a = _ease(sec * 2)
        d.text((W // 2, 560), "THOSE WHITE SPECKS ARE LIME", font=font(32), fill=_mix(bg, col["accent"], a), anchor="mm")
    else:
        _stage_heal(d, col, s)
    if vis.get("callout"):
        a = _ease(sec * 3.0)
        size = 42
        while d.textlength(vis["callout"], font=font(size)) > W - 100 and size > 26:
            size -= 2
        d.text((W // 2, 1200), vis["callout"], font=font(size), fill=_mix(bg, col["accent"], a), anchor="mm")
    d.text((W // 2, 1252), "Simplified animation", font=font(24), fill=col["muted"], anchor="mm")
