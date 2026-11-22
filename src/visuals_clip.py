"""render_clip: play a full-frame Blender render (renders/<episode>/<clip>/f_0001.png ...) behind the subtitles.

YAML:  visual: {type: render_clip, clip: catch, badge: ILLUSTRATIVE, labels: [{text: "GRID FINS", at: 2.0, until: 5.0, x: 540, y: 500}]}
If the frames are missing (for example on the cloud runner, where the heavy renders are not made), a simple
2D stand-in is drawn instead and a small "2D PREVIEW" tag is shown, so the episode still builds. Labels and the
CONFIRMED / ILLUSTRATIVE badge are drawn here (crisp text), not baked into the 3D render.
"""
import json
import math
from functools import lru_cache

from PIL import Image

from .common import ROOT, font
from .visuals_jet import _mix, _ease

W, H = 1080, 1920


def clip_dir(ep, clip):
    """Final renders first, then quick previews (renders/<id>_preview/)."""
    final = ROOT / "renders" / str(ep["id"]) / clip
    prev = ROOT / "renders" / f"{ep['id']}_preview" / clip
    return final if (final / "f_0001.png").exists() or not (prev / "f_0001.png").exists() else prev


@lru_cache(maxsize=32)
def _meta(path):
    m = path / "meta.json"
    try:
        return json.loads(m.read_text()) if m.exists() else None
    except Exception:
        return None


@lru_cache(maxsize=16)
def _frame(path, idx):
    return Image.open(path / f"f_{idx:04d}.png").convert("RGB").resize((W, H))


def frame_index(meta, progress):
    """Frame for scene progress 0..1: the whole clip is stretched to the scene's length. Pure (testable)."""
    n = int(meta["frames"])
    return max(1, min(n, int(round(max(0.0, min(1.0, progress)) * (n - 1))) + 1))


# ---------------------------------------------------------------- 2D stand-in (same story, simple shapes)
def _standin(d, col, clip, sec, u):
    bg, ac, tech, muted = col["bg"], col["accent"], col["tech"], col["muted"]
    d.rectangle([0, 1300, W, H], fill=_mix(bg, muted, 0.25))                 # ground
    tx = 250
    d.rectangle([tx - 40, 380, tx + 40, 1300], outline=ac, width=5)           # tower
    for y in range(420, 1300, 70):
        d.line([tx - 40, y, tx + 40, y + 50], fill=_mix(bg, ac, 0.5), width=2)
    hold_y = 640
    if clip in ("return", "catch"):
        y = hold_y - 520 * (1 - _ease(u * 1.2)) if clip == "catch" else 200 + 400 * _ease(u)
    else:
        y = hold_y
    close = _ease((u - 0.4) * 3) if clip == "catch" else (1.0 if clip in ("engineering", "ending") else 0.0)
    bx, bw, bh = 640, 150, 640
    d.rounded_rectangle([bx - bw / 2, y, bx + bw / 2, y + bh], radius=18, fill=_mix(bg, col["text"], 0.85))   # booster
    if clip in ("return", "catch") and u < 0.7:
        d.polygon([(bx - 50, y + bh), (bx + 50, y + bh), (bx, y + bh + 120 + 20 * math.sin(sec * 20))], fill=(255, 150, 40))
    for s in (-1, 1):                                                          # arms
        ay = hold_y + 200 + s * (1 - close) * 90
        d.line([tx + 40, ay, bx - bw / 2 + 4, ay], fill=ac, width=14)


def _standin_engine(d, col, clip, sec, u):
    """Simple end-on W16 sketch (four rows of cylinders around one crankshaft) or a plain car side view."""
    bg, ac, tech, muted, txt = col["bg"], col["accent"], col["tech"], col["muted"], col["text"]
    if clip in ("intro", "ending"):
        d.rounded_rectangle([140, 820, 940, 960], radius=60, fill=_mix(bg, txt, 0.25), outline=ac, width=4)
        d.rounded_rectangle([380, 740, 760, 840], radius=50, fill=_mix(bg, txt, 0.15))
        for x in (280, 800):
            d.ellipse([x - 85, 900, x + 85, 1070], fill=_mix(bg, txt, 0.1), outline=ac, width=4)
        return
    cx, cy = 540, 820
    d.ellipse([cx - 30, cy - 30, cx + 30, cy + 30], fill=_mix(bg, txt, 0.5))                     # crankshaft end
    for r, ang in enumerate((-52.5, -37.5, 37.5, 52.5)):
        a = math.radians(ang)
        for k in range(4):
            dist = 110 + 62 * k
            x, y = cx + dist * math.sin(a), cy - dist * math.cos(a)
            lit = clip == "layout" and _ease(sec * 0.4 - r * 0.17) > 0.5
            d.ellipse([x - 24, y - 24, x + 24, y + 24], outline=ac if r % 2 == 0 else tech, width=4,
                      fill=_mix(bg, ac if r % 2 == 0 else tech, 0.5 if lit else 0.12))
    if clip in ("turbos", "running"):
        for sx in (-1, 1):
            for sy in (-1, 1):
                x, y = cx + sx * 330, cy + 120 + sy * 150
                d.ellipse([x - 45, y - 45, x + 45, y + 45], outline=tech, width=5)
                ph = (sec * 0.5 + (sx + 2 * sy) * 0.13) % 1.0
                d.ellipse([cx + (x - cx) * ph - 9, cy + (y - cy) * ph - 9, cx + (x - cx) * ph + 9, cy + (y - cy) * ph + 9], fill=(255, 150, 40))


def _standin_rocket_engine(d, col, clip, sec, u):
    """Side view: two propellant tanks, chamber, narrow throat, bell nozzle, exhaust dots."""
    bg, ac, tech, txt = col["bg"], col["accent"], col["tech"], col["text"]
    cx = 540
    d.rounded_rectangle([cx - 230, 330, cx - 30, 600], radius=30, outline=ac, width=5, fill=_mix(bg, ac, 0.15))
    d.rounded_rectangle([cx + 30, 330, cx + 230, 600], radius=30, outline=tech, width=5, fill=_mix(bg, tech, 0.15))
    d.rectangle([cx - 90, 700, cx + 90, 860], outline=txt, width=5)                          # chamber
    d.polygon([(cx - 90, 860), (cx + 90, 860), (cx + 35, 930), (cx - 35, 930)], outline=txt, width=5)   # throat
    d.polygon([(cx - 35, 930), (cx + 35, 930), (cx + 150, 1120), (cx - 150, 1120)], outline=txt, width=5)  # bell
    for k in range(10):
        ph = (sec * 0.5 + k / 10) % 1.0
        y = 880 + 380 * ph ** 1.5
        x = cx + 20 * math.sin(k * 3 + sec * 6) * (0.3 + ph)
        d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=(255, 150, 40))
    for sx, c in ((-1, ac), (1, tech)):
        for k in range(4):
            ph = (sec * 0.4 + k / 4) % 1.0
            d.ellipse([cx + sx * 130 - 8, 600 + 100 * ph - 8, cx + sx * 130 + 8, 600 + 100 * ph + 8], fill=c)


def _standin_solar(d, col, clip, sec, u):
    """Sun, tilted panel of cells, dots flowing to a small house."""
    bg, ac, tech, txt = col["bg"], col["accent"], col["tech"], col["text"]
    d.ellipse([780, 330, 920, 470], fill=ac)
    for k in range(5):
        ph = (sec * 0.4 + k / 5) % 1.0
        x, y = 850 - 400 * ph, 400 + 380 * ph
        d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=ac)
    for i in range(4):
        for j in range(3):
            x0, y0 = 220 + i * 100, 620 + j * 90
            d.polygon([(x0 + 20, y0), (x0 + 110, y0), (x0 + 90, y0 + 80), (x0, y0 + 80)], fill=_mix(bg, tech, 0.35), outline=txt)
    d.polygon([(620, 1010), (800, 1010), (710, 940)], fill=_mix(bg, ac, 0.4))                 # roof
    d.rectangle([640, 1010, 780, 1110], outline=txt, width=4)
    if clip in ("current", "home", "panel"):
        for k in range(6):
            ph = (sec * 0.35 + k / 6) % 1.0
            x, y = 440 + 260 * ph, 880 + 120 * ph
            d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=tech)


def draw_render_clip(img, d, vis, scene_t, col, brand, ep, sec=0.0):
    clip = vis["clip"]
    path = clip_dir(ep, clip)
    meta = _meta(path)
    bg = col["bg"]
    if meta and (path / "f_0001.png").exists():
        img.paste(_frame(path, frame_index(meta, scene_t)), (0, 0))
        stand = False
    else:
        {"engine": _standin_engine, "rocket_engine": _standin_rocket_engine, "solar": _standin_solar}.get(vis.get("standin"), _standin)(d, col, clip, sec, scene_t)
        stand = True
    if vis.get("badge"):
        f = font(28)
        w = d.textlength(vis["badge"], font=f) + 44
        d.rounded_rectangle([W / 2 - w / 2, 1620, W / 2 + w / 2, 1672], radius=26, fill=bg, outline=col["accent"], width=3)
        d.text((W // 2, 1646), vis["badge"], font=f, fill=col["accent"], anchor="mm")
    for lb in vis.get("labels", []) or []:
        a = _ease((sec - lb.get("at", 0)) * 3) * (1 - _ease((sec - lb.get("until", 99)) * 3))
        if a <= 0.02:
            continue
        f = font(lb.get("size", 38))
        w = d.textlength(lb["text"], font=f) + 40
        x, y = lb.get("x", 540), lb.get("y", 500)
        d.rounded_rectangle([x - w / 2, y - 34, x + w / 2, y + 34], radius=14, fill=_mix(bg, bg, 0), outline=_mix(bg, col["tech"], a), width=3)
        d.text((x, y), lb["text"], font=f, fill=_mix(bg, col["text"], a), anchor="mm")
    if stand:
        d.text((W // 2, 1710), "2D PREVIEW (3D render not made on this machine)", font=font(20), fill=col["muted"], anchor="mm")
