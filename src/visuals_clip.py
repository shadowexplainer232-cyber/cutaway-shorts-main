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


def draw_render_clip(img, d, vis, scene_t, col, brand, ep, sec=0.0):
    clip = vis["clip"]
    path = clip_dir(ep, clip)
    meta = _meta(path)
    bg = col["bg"]
    if meta and (path / "f_0001.png").exists():
        img.paste(_frame(path, frame_index(meta, scene_t)), (0, 0))
        stand = False
    else:
        _standin(d, col, clip, sec, scene_t)
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
