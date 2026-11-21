"""Intercooler animation. Uses the Blender loop (assets/intercooler3d/) when it has been rendered,
otherwise draws a 2D version with the same layout, so a video builds either way.

  stage: overview | hot | cool | dense
World x (Blender) -> video pixels: PX(x). The 3D frame is pasted so its centre is at video y = 860.
Illustrative, not an engineering drawing.
"""
import json
import math
from functools import lru_cache

from PIL import Image

from .common import ROOT, font
from .visuals_jet import _mix, _ease
from .visuals_turbo import _wheel

W, H = 1080, 1920
DIR = ROOT / "assets" / "intercooler3d"
FPS = 30
HOT = (255, 100, 40)
YC = 860                                           # centre line of the diagram

SCALE = 1080 / 17.6 * math.cos(0.26)               # pixels per world unit (orthographic camera)


def PX(x):
    return 540 + (x + 1.1) * SCALE


CORE_X0, CORE_X1 = -2.6, 1.8
KEYS = [(0.0, -9.0), (0.2, -5.5), (0.5, 1.8), (1.0, 6.8)]     # same mapping as the Blender scene


def _x_of(u):
    for (u0, x0), (u1, x1) in zip(KEYS, KEYS[1:]):
        if u <= u1:
            return x0 + (x1 - x0) * (u - u0) / (u1 - u0)
    return KEYS[-1][1]


def _temp(x):
    s = lambda v: max(0.0, min(1.0, v)) ** 2 * (3 - 2 * max(0.0, min(1.0, v)))
    if x < -5.9:
        return 0.0
    if x < -4.9:
        return s(x + 5.9)
    if x < CORE_X0:
        return 1.0
    if x < CORE_X1:
        return 1.0 - (x - CORE_X0) / (CORE_X1 - CORE_X0)
    return 0.0


@lru_cache(maxsize=1)
def _meta():
    m = DIR / "meta.json"
    try:
        return json.loads(m.read_text()) if m.exists() else None
    except Exception:
        return None


@lru_cache(maxsize=100)
def _frame(i):
    return Image.open(DIR / f"f_{i:03d}.png").convert("RGBA")


def _draw_3d(img, sec):
    n = _meta()["frames"]
    f = _frame(int(sec * FPS) % n)
    img.paste(f, (0, YC - f.height // 2), f)


def _draw_2d(d, col, sec):
    bg = col["bg"]
    # pipe
    x_a, x_b = PX(-9.0), PX(6.8)
    d.rounded_rectangle([x_a, YC - 26, x_b, YC + 26], radius=20, fill=_mix(bg, col["muted"], 0.25))
    # compressor
    _wheel(d, col, (PX(-5.5), YC), 9.0 * sec, col["accent"], 1.0, radius=80)
    # intercooler core with tubes and fins
    cx0, cx1 = PX(CORE_X0), PX(CORE_X1)
    d.rounded_rectangle([cx0 - 14, YC - 140, cx1 + 14, YC + 140], radius=14, fill=_mix(bg, col["muted"], 0.18),
                        outline=_mix(bg, col["text"], 0.7), width=4)
    for z in (-1.2, -0.6, 0.0, 0.6, 1.2):
        y = YC - z * SCALE * 0.7
        d.line([(cx0, y), (cx1, y)], fill=_mix(bg, col["accent"], 0.7), width=7)
    x = cx0 + 14
    while x < cx1:
        d.line([(x, YC - 130), (x, YC + 130)], fill=_mix(bg, col["text"], 0.30), width=2)
        x += 14
    # engine
    ex0, ex1 = PX(4.2), PX(6.8)
    d.rounded_rectangle([ex0, YC - 110, ex1, YC + 110], radius=16, fill=_mix(bg, col["muted"], 0.5),
                        outline=col["text"], width=4)
    for k in range(4):
        d.rectangle([ex0 + 14 + k * 34, YC - 140, ex0 + 36 + k * 34, YC - 110], fill=_mix(bg, col["text"], 0.8))
    # air parcels: sparse and hot, then cooled and denser
    for j in range(28):
        u = (j / 28 + sec * 0.04) % 1.0
        x = _x_of(u)
        spread = 0.0
        if CORE_X0 - 0.4 < x < CORE_X1 + 0.4:
            spread = min(1.0, (x - (CORE_X0 - 0.4)) / 0.4, (CORE_X1 + 0.4 - x) / 0.4)
        lane = (-1.2, -0.6, 0.0, 0.6, 1.2)[j % 5]
        y = YC - lane * spread * SCALE * 0.7
        t = _temp(x)
        c = tuple(int(col["tech"][i] * (1 - t) + HOT[i] * t) for i in range(3))
        r = 10
        d.ellipse([PX(x) - r, y - r, PX(x) + r, y + r], fill=c)
    # outside air falling through the fins
    for k in range(14):
        ph = (k * 0.37 + sec * 0.25) % 1.0
        xx = PX(CORE_X0 + 0.3 + 0.28 * k)
        yy = YC - 150 + ph * 300
        d.ellipse([xx - 5, yy - 5, xx + 5, yy + 5], fill=_mix(bg, col["tech"], 0.95))


def draw_intercooler(img, d, vis, scene_t, col, brand, ep, sec=0.0):
    stage = vis.get("stage", "overview")
    bg = col["bg"]
    if _meta():
        try:
            _draw_3d(img, sec)
        except Exception:                                   # missing/corrupt frame: use the 2D drawing
            _draw_2d(d, col, sec)
    else:
        _draw_2d(d, col, sec)

    a = _ease(sec * 2)
    region = {"hot": (PX(-6.4), PX(-2.6), HOT, "HOT, THIN AIR"),
              "cool": (PX(CORE_X0) - 20, PX(CORE_X1) + 20, col["accent"], "THE INTERCOOLER"),
              "dense": (PX(CORE_X1) + 20, PX(6.8), col["tech"], "COOLER, DENSER AIR")}.get(stage)
    if region:
        x0, x1, c, label = region
        d.rounded_rectangle([x0, YC - 180, x1, YC + 180], radius=26, outline=_mix(bg, c, a), width=5)
        d.text(((x0 + x1) / 2, YC - 214), label, font=font(30), fill=_mix(bg, c, a), anchor="mm")
    if stage == "cool":                                     # outside air arrows into the core
        for k in range(3):
            x = PX(-1.2 + 1.0 * k)
            y = YC - 300 + 14 * math.sin(sec * 5 + k)
            d.polygon([(x, y + 40), (x - 18, y), (x + 18, y)], fill=_mix(bg, col["tech"], a))
        d.text((PX(-0.4), YC - 330), "COOL AIR FROM OUTSIDE", font=font(26), fill=_mix(bg, col["tech"], a), anchor="mm")

    for text, x in (("COMPRESSOR", PX(-5.5)), ("INTERCOOLER", PX(-0.4)), ("ENGINE", PX(5.5))):
        d.text((x, YC + 250), text, font=font(26), fill=col["text"], anchor="mm")

    if vis.get("callout"):
        size = 42
        while d.textlength(vis["callout"], font=font(size)) > W - 100 and size > 26:
            size -= 2
        d.text((W // 2, 1200), vis["callout"], font=font(size), fill=_mix(bg, col["accent"], _ease(sec * 3.0)), anchor="mm")
    d.text((W // 2, 1252), "Simplified animation", font=font(24), fill=col["muted"], anchor="mm")
