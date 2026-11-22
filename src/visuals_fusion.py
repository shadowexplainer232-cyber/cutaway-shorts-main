"""Nuclear fusion (energy). Stages: sun | fuse | heat | tokamak | power.

sun      the Sun glows; small flashes show fusion
fuse     two light nuclei join into one heavier one and release energy
heat     the fuel must get extremely hot: it becomes plasma
tokamak  ring-shaped machine, magnetic coils hold the plasma   (Blender 3D if rendered)
power    energy carried out by neutrons makes electricity       (Blender 3D if rendered)
The tokamak/power stages use assets/tokamak3d/ when it has been rendered by Blender, otherwise the
same geometry is drawn in 2D (identical projection). Schematic, not to scale.
"""
import json
import math
from functools import lru_cache

from PIL import Image

from .common import ROOT, font
from .visuals_jet import _mix, _ease

W, H = 1080, 1920
DIR = ROOT / "assets" / "tokamak3d"
FPS = 30
YC = 860
PLASMA = (255, 140, 30)
S = 1080 / 12.5                                    # pixels per world unit (matches the Blender camera)
ELEV = math.atan2(7, 11)
R, R_TUBE, R_PLASMA, N_COILS = 3.0, 1.1, 0.45, 16


def _proj(X, Y, Z):
    """Orthographic view from the front at elevation ELEV (same as the Blender camera)."""
    return 540 + X * S, YC - S * (Z * math.cos(ELEV) + Y * math.sin(ELEV))


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


def _glow(d, col, x, y, r, color, a=1.0):
    bg = col["bg"]
    for k in range(5, 0, -1):
        rr = r * (1 + 0.45 * k)
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=_mix(bg, color, 0.05 * (6 - k) * a))
    d.ellipse([x - r, y - r, x + r, y + r], fill=_mix(bg, color, 0.9 * a))


def _torus_2d(d, col, sec):
    bg = col["bg"]
    steps = 120
    ring = [(2 * math.pi * i / steps) for i in range(steps)]
    ring.sort(key=lambda th: -R * math.sin(th))                  # far (large Y) first
    for th in ring:
        x, y = _proj(R * math.cos(th), R * math.sin(th), 0)
        rr = R_TUBE * S * 0.92
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=_mix(bg, col["tech"], 0.10))
    for th in ring:
        x, y = _proj(R * math.cos(th), R * math.sin(th), 0)
        rr = R_PLASMA * S
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=_mix(bg, PLASMA, 0.55))
    # coils: rings around the tube, far ones first
    for k in sorted(range(N_COILS), key=lambda k: -math.sin(2 * math.pi * k / N_COILS)):
        th = 2 * math.pi * k / N_COILS
        cx_, cy_ = R * math.cos(th), R * math.sin(th)
        pts = []
        for j in range(25):
            a = 2 * math.pi * j / 24
            rr = R_TUBE + 0.45
            X = cx_ + rr * math.cos(a) * math.cos(th)
            Y = cy_ + rr * math.cos(a) * math.sin(th)
            pts.append(_proj(X, Y, rr * math.sin(a)))
        d.line(pts, fill=_mix(bg, col["tech"], 0.85), width=5)
    for k in range(18):                                          # glowing particles on a helical path
        th = 2 * math.pi * (k / 18 + sec * 0.15)
        psi = 3 * th
        rr = R + 0.28 * math.cos(psi)
        x, y = _proj(rr * math.cos(th), rr * math.sin(th), 0.28 * math.sin(psi))
        d.ellipse([x - 8, y - 8, x + 8, y + 8], fill=(255, 235, 170))


def _ring(img, d, col, sec):
    if _meta():
        try:
            f = _frame(int(sec * FPS) % _meta()["frames"])
            img.paste(f, (0, YC - f.height // 2), f)
            return
        except Exception:
            pass
    _torus_2d(d, col, sec)


def _stage_sun(d, col, sec):
    bg = col["bg"]
    pulse = 1 + 0.03 * math.sin(sec * 3)
    _glow(d, col, 540, 860, 150 * pulse, (255, 170, 40))
    for i in range(10):                                          # fusion flashes inside
        ph = (sec * 0.8 + i * 0.37) % 1.0
        a = math.sin(math.pi * ph)
        x = 540 + 95 * math.cos(i * 2.4) * (0.4 + 0.6 * ph)
        y = 860 + 95 * math.sin(i * 2.4) * (0.4 + 0.6 * ph)
        d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=_mix((255, 170, 40), (255, 255, 255), a))
    d.text((540, 1090), "THE SUN RUNS ON FUSION", font=font(34), fill=_mix(bg, col["accent"], _ease(sec * 2)), anchor="mm")


def _nucleus(d, col, x, y, n_p, n_n, r=17):
    spots = [(0, 0), (r, 0), (-r * 0.5, r * 0.9), (-r * 0.5, -r * 0.9), (r * 0.5, r * 1.4)][: n_p + n_n]
    for i, (dx, dy) in enumerate(spots):
        c = col["accent"] if i < n_p else col["tech"]
        d.ellipse([x + dx - r, y + dy - r, x + dx + r, y + dy + r], fill=c, outline=col["bg"], width=2)


def _stage_fuse(d, col, sec):
    bg = col["bg"]
    t = (sec % 5.0) / 5.0
    approach = _ease(t / 0.45)
    if t < 0.5:
        _nucleus(d, col, 160 + 330 * approach, 860, 1, 1)
        _nucleus(d, col, 920 - 330 * approach, 860, 1, 2)
        d.text((220, 960), "LIGHT NUCLEUS", font=font(24), fill=col["muted"], anchor="mm")
        d.text((860, 960), "LIGHT NUCLEUS", font=font(24), fill=col["muted"], anchor="mm")
    else:
        k = _ease((t - 0.5) / 0.3)
        flash = max(0.0, 1 - (t - 0.5) / 0.12)
        if flash > 0:
            _glow(d, col, 540, 860, 60 + 50 * flash, (255, 240, 200), flash)
        _nucleus(d, col, 540 - 40 * k, 860, 2, 2, r=20)                      # one heavier nucleus
        x = 540 + 40 + 360 * k                                                # a neutron carries energy away
        d.ellipse([x - 12, 860 - 90 * k - 12, x + 12, 860 - 90 * k + 12], fill=col["tech"])
        d.text((500, 960), "ONE HEAVIER NUCLEUS", font=font(26), fill=col["text"], anchor="mm")
        d.text((760, 740), "ENERGY RELEASED", font=font(30), fill=_mix(bg, col["accent"], k), anchor="mm")


def _stage_heat(d, col, sec):
    bg = col["bg"]
    import random
    rnd = random.Random(4)
    _glow(d, col, 540, 860, 120, PLASMA, 0.6)
    for i in range(34):                                          # hot, fast particles
        a = rnd.uniform(0, 6.28)
        r = rnd.uniform(20, 200)
        x = 540 + r * math.cos(a + sec * rnd.uniform(1, 3)) + 12 * math.sin(sec * 9 + i)
        y = 860 + r * 0.8 * math.sin(a + sec * rnd.uniform(1, 3)) + 12 * math.cos(sec * 8 + i)
        d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=col["accent"] if i % 3 else col["tech"])
    h = _ease(sec / 2.5)                                         # temperature bar
    d.rounded_rectangle([140, 1100, 940, 1130], radius=12, outline=col["muted"], width=3)
    d.rounded_rectangle([140, 1100, 140 + 800 * h, 1130], radius=12, fill=_mix(col["accent"], (255, 90, 50), h))
    d.text((540, 1070), "OVER 100 MILLION °C", font=font(36), fill=_mix(bg, (255, 120, 60), _ease(sec * 1.5)), anchor="mm")
    d.text((540, 590), "MATTER BECOMES PLASMA", font=font(32), fill=_mix(bg, col["accent"], _ease(sec * 2)), anchor="mm")


def draw_fusion(img, d, vis, scene_t, col, brand, ep, sec=0.0):
    stage = vis.get("stage", "sun")
    bg = col["bg"]
    if stage == "sun":
        _stage_sun(d, col, sec)
    elif stage == "fuse":
        _stage_fuse(d, col, sec)
    elif stage == "heat":
        _stage_heat(d, col, sec)
    else:
        _ring(img, d, col, sec)
        a = _ease(sec * 2)
        if stage == "tokamak":
            d.text((W // 2, 570), "MAGNETIC FIELDS HOLD THE PLASMA", font=font(32), fill=_mix(bg, col["accent"], a), anchor="mm")
            d.text((540, 1135), "THE COILS", font=font(26), fill=_mix(bg, col["tech"], a), anchor="mm")
        else:                                                    # power: neutrons carry the energy out
            d.text((W // 2, 570), "NEUTRONS CARRY THE ENERGY OUT", font=font(32), fill=_mix(bg, col["accent"], a), anchor="mm")
            for k in range(8):
                ph = (sec * 0.5 + k / 8) % 1.0
                ang = 2 * math.pi * k / 8
                x, y = 540 + (150 + 330 * ph) * math.cos(ang), 860 + (80 + 200 * ph) * math.sin(ang)
                d.ellipse([x - 8, y - 8, x + 8, y + 8], fill=_mix(bg, col["tech"], 1 - 0.6 * ph))
            d.text((540, 1135), "HEAT → STEAM → ELECTRICITY", font=font(30), fill=_mix(bg, col["accent"], _ease((sec - 1.2) * 2)), anchor="mm")

    if vis.get("callout"):
        size = 42
        while d.textlength(vis["callout"], font=font(size)) > W - 100 and size > 26:
            size -= 2
        d.text((W // 2, 1200), vis["callout"], font=font(size), fill=_mix(bg, col["accent"], _ease(sec * 3.0)), anchor="mm")
    d.text((W // 2, 1252), "Simplified animation", font=font(24), fill=col["muted"], anchor="mm")
