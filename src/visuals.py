"""Frame renderer: procedural cutaway animations + subtitles, drawn with Pillow.

Layout (1080x1920), kept clear of YouTube's bottom interface:
  y 120-420   series tag + on-screen headline
  y 440-1180  animation
  y 1240-1480 subtitles
"""
import json
import math
from functools import lru_cache

from PIL import Image, ImageDraw

from .common import ROOT, font, rgb
from .visuals_jet import draw_jet_engine, draw_jet_hook, draw_blade_cooling
from .visuals_turbo import draw_turbo
from .visuals_boost import draw_boost_compare
from .visuals_cards import draw_fact_card
from .visuals_gears import draw_gearbox
from .visuals_rocket import draw_rocket_steer

W, H = 1080, 1920


def _blend(c1, c2, a):
    a = max(0.0, min(1.0, a))
    return tuple(int(c1[i] * (1 - a) + c2[i] * a) for i in range(3))


# ---------------------------------------------------------------- four-stroke engine
STROKE_NAMES = ["INTAKE", "COMPRESSION", "POWER", "EXHAUST"]
PHASE_START = {"intake": 0, "compression": 180, "power": 360, "exhaust": 540}


def _theta(visual, t):
    """Crank angle in degrees (0-720) for progress t in [0,1) of the scene."""
    phase = visual.get("phase", "all")
    if phase == "all":
        return (t * 720.0) % 720.0
    return PHASE_START[phase] + t * 180.0


def _draw_engine(d, theta, col):
    cx = W // 2
    r, rod = 100, 260                  # crank radius, connecting-rod length
    head_y = 560                       # underside of cylinder head
    crank_y = 1020
    bore = 340
    left, right = cx - bore // 2, cx + bore // 2
    idx = int(theta // 180) % 4
    local = (theta % 180) / 180.0

    # slider-crank geometry (real kinematics: TDC at theta = 0)
    rad = math.radians(theta)
    pin = (cx + r * math.sin(rad), crank_y - r * math.cos(rad))
    piston_pin_y = pin[1] - math.sqrt(rod ** 2 - (r * math.sin(rad)) ** 2)
    piston_top = piston_pin_y - 60

    # combustion chamber fill
    if idx == 0:
        fill = _blend(col["bg"], col["tech"], 0.15 + 0.15 * local)
    elif idx == 1:
        fill = _blend(col["bg"], col["tech"], 0.30 + 0.45 * local)
    elif idx == 2:
        fill = _blend(col["accent"], col["muted"], 0.15 + 0.75 * local)
    else:
        fill = _blend(col["muted"], col["bg"], 0.2 + 0.6 * local)
    d.rectangle([left + 4, head_y + 4, right - 4, piston_top], fill=fill)

    # cylinder walls and head
    d.rectangle([left - 14, head_y - 40, right + 14, head_y], fill=col["muted"])
    d.rectangle([left - 14, head_y, left, 900], fill=col["muted"])
    d.rectangle([right, head_y, right + 14, 900], fill=col["muted"])

    # crankcase circle, rod, pin
    d.ellipse([cx - r, crank_y - r, cx + r, crank_y + r], outline=col["muted"], width=8)
    d.line([pin, (cx, piston_pin_y)], fill=col["text"], width=14)
    d.ellipse([pin[0] - 18, pin[1] - 18, pin[0] + 18, pin[1] + 18], fill=col["accent"])
    d.ellipse([cx - 10, crank_y - 10, cx + 10, crank_y + 10], fill=col["text"])

    # piston
    d.rectangle([left + 6, piston_top, right - 6, piston_top + 90], fill=col["text"])
    for k in (18, 34):  # rings
        d.line([(left + 6, piston_top + k), (right - 6, piston_top + k)], fill=col["muted"], width=4)

    # valves (simplified timing: intake open in stroke 1, exhaust open in stroke 4)
    for vx, is_open, name in ((cx - 95, idx == 0, "INTAKE VALVE"), (cx + 95, idx == 3, "EXHAUST VALVE")):
        drop = 26 if is_open else 0
        d.rectangle([vx - 5, head_y - 90, vx + 5, head_y + drop - 4], fill=col["text"])
        d.rectangle([vx - 34, head_y + drop - 4, vx + 34, head_y + drop + 8],
                    fill=col["accent"] if is_open else col["text"])
    # gas flow arrows
    if idx == 0:
        _arrow(d, cx - 95, head_y - 200, cx - 95, head_y - 20, col["tech"])
    if idx == 3:
        _arrow(d, cx + 95, head_y - 20, cx + 95, head_y - 200, col["muted"])

    # spark plug and flash at the start of the power stroke
    d.rectangle([cx - 8, head_y - 110, cx + 8, head_y], fill=col["muted"])
    if idx == 2 and local < 0.18:
        s = 55 * (1 - local / 0.18) + 15
        pts = []
        for k in range(16):
            rr = s if k % 2 == 0 else s * 0.45
            a = math.pi * k / 8
            pts.append((cx + rr * math.cos(a), head_y + 30 + rr * math.sin(a)))
        d.polygon(pts, fill=col["accent"])

    # labels
    lf = font(30)
    d.text((left - 60, head_y - 150), "INTAKE", font=lf, fill=col["tech"], anchor="rm")
    d.text((right + 24, head_y - 150), "EXHAUST", font=lf, fill=col["muted"], anchor="lm")
    d.text((cx, head_y - 140), "SPARK", font=font(24), fill=col["muted"], anchor="mm")
    d.text((left - 24, piston_top + 45), "PISTON", font=lf, fill=col["text"], anchor="rm")
    d.text((right + 24, crank_y), "CRANKSHAFT", font=lf, fill=col["text"], anchor="lm")

    _chips(d, idx, col, 1130)
    d.text((cx, 1215), "Simplified animation", font=font(24), fill=col["muted"], anchor="mm")


def _chips(d, idx, col, y):
    chip_f = font(24)
    x0, w = 45, 240
    for i, name in enumerate(STROKE_NAMES):
        on = i == idx
        box = [x0 + i * (w + 10), y, x0 + i * (w + 10) + w, y + 50]
        d.rounded_rectangle(box, radius=14, fill=col["accent"] if on else col["bg"],
                            outline=col["accent"] if on else col["muted"], width=3)
        d.text(((box[0] + box[2]) // 2, (box[1] + box[3]) // 2), name, font=chip_f,
               fill=col["bg"] if on else col["muted"], anchor="mm")


# ---------------------------------------------------------------- optional 3D (Blender) frames
ENGINE3D = ROOT / "assets" / "engine3d"


@lru_cache(maxsize=1)
def _meta3d():
    m = ENGINE3D / "meta.json"
    return json.loads(m.read_text()) if m.exists() else None


@lru_cache(maxsize=48)
def _frame3d(i):
    return Image.open(ENGINE3D / f"f_{i:03d}.png").convert("RGBA")


def _engine_3d(img, d, theta, col):
    n = _meta3d()["frames"]
    pos = (theta % 720.0) / 720.0 * n
    i0 = int(pos) % n
    a = pos - int(pos)
    f = Image.blend(_frame3d(i0), _frame3d((i0 + 1) % n), a)   # blend neighbours for smooth motion
    img.paste(f, (0, 380), f)
    _chips(d, int(theta // 180) % 4, col, 1180)
    d.text((W // 2, 1262), "Simplified animation", font=font(24), fill=col["muted"], anchor="mm")


def _engine(img, d, vis, scene_t, col, brand, ep, sec=0.0):
    theta = _theta(vis, scene_t)
    if _meta3d():
        _engine_3d(img, d, theta, col)
    else:
        _draw_engine(d, theta, col)


# ---------------------------------------------------------------- brand outro
def _fade(color, bg, a):
    return _blend(bg, color, a)


def _outro(img, d, vis, t, col, brand, ep, sec=0.0):
    cx, cy, r = W // 2, 640, 190
    # logo: amber ring drawing itself, a cyan cut-away quarter, a turning gear
    sweep = 300 * min(1.0, t * 2.5)
    d.arc([cx - r, cy - r, cx + r, cy + r], start=-90, end=-90 + sweep, fill=col["accent"], width=18)
    d.pieslice([cx - 120, cy - 120, cx + 120, cy + 120], start=-90, end=0, fill=col["tech"])
    d.ellipse([cx - 120, cy - 120, cx + 120, cy + 120], outline=col["muted"], width=6)
    for k in range(10):
        a = math.radians(k * 36 + t * 70)
        x1, y1 = cx + 78 * math.cos(a), cy + 78 * math.sin(a)
        x2, y2 = cx + 104 * math.cos(a), cy + 104 * math.sin(a)
        d.line([(x1, y1), (x2, y2)], fill=col["bg"], width=12)
    d.ellipse([cx - 30, cy - 30, cx + 30, cy + 30], fill=col["bg"], outline=col["accent"], width=6)

    a = max(0.0, min(1.0, (t - 0.2) * 3))
    d.text((cx, 930), brand["channel_name"].upper(), font=font(120), fill=_fade(col["text"], col["bg"], a), anchor="mm")
    d.text((cx, 1030), brand["tagline"], font=font(42), fill=_fade(col["accent"], col["bg"], a), anchor="mm")
    b = max(0.0, min(1.0, (t - 0.45) * 3))
    box = [cx - 270, 1100, cx + 270, 1180]
    d.rounded_rectangle(box, radius=40, fill=_fade(col["accent"], col["bg"], b))
    d.text((cx, 1140), "FOLLOW FOR MORE", font=font(44), fill=_fade(col["bg"], col["accent"], b), anchor="mm")
    nxt = ep.get("next_up")
    if nxt:
        d.text((cx, 1235), "NEXT: " + nxt, font=font(32), fill=_fade(col["muted"], col["bg"], b), anchor="mm")


def _arrow(d, x1, y1, x2, y2, color):
    d.line([(x1, y1), (x2, y2)], fill=color, width=10)
    ang = math.atan2(y2 - y1, x2 - x1)
    for s in (-0.5, 0.5):
        d.line([(x2, y2), (x2 - 34 * math.cos(ang + s), y2 - 34 * math.sin(ang + s))], fill=color, width=10)


VISUALS = {"four_stroke": _engine, "outro": _outro, "jet_engine": draw_jet_engine,
           "jet_hook": draw_jet_hook, "blade_cooling": draw_blade_cooling, "turbo": draw_turbo,
           "boost_compare": draw_boost_compare, "fact_card": draw_fact_card, "gearbox": draw_gearbox, "rocket_steer": draw_rocket_steer}


# ---------------------------------------------------------------- text helpers
def _wrap(text, f, max_w, d):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if d.textlength(trial, font=f) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def subtitle_chunks(text, per_chunk=3):
    """Split narration into short chunks, each a list of (word, weight)."""
    words = text.split()
    return [words[i:i + per_chunk] for i in range(0, len(words), per_chunk)]


def _draw_subtitle(d, text, progress, col, speaking_pad):
    """Show 3-word chunks timed by character count; current word highlighted."""
    words = text.split()
    weights = [len(w) + 2 for w in words]
    total = sum(weights)
    speech = max(0.01, 1.0 - speaking_pad)
    p = min(progress / speech, 0.9999)
    acc, cur = 0.0, 0
    for i, wgt in enumerate(weights):
        if p < (acc + wgt) / total:
            cur = i
            break
        acc += wgt
    start = (cur // 3) * 3
    chunk = words[start:start + 3]
    size = 84
    f = font(size)
    line_w = sum(d.textlength(w + " ", font=f) for w in chunk)
    while line_w > W - 120 and size > 40:   # shrink long chunks so they never leave the frame
        size -= 4
        f = font(size)
        line_w = sum(d.textlength(w + " ", font=f) for w in chunk)
    x = (W - line_w) / 2
    y = 1360
    for j, w in enumerate(chunk):
        c = col["accent"] if start + j == cur else col["text"]
        d.text((x, y), w, font=f, fill=c, stroke_width=8, stroke_fill=col["bg"], anchor="lm")
        x += d.textlength(w + " ", font=f)


# ---------------------------------------------------------------- public API
def make_renderer(brand, episode):
    col = {k: rgb(v) for k, v in brand["colors"].items()}
    series = episode.get("series", "")
    base = Image.new("RGB", (W, H), col["bg"])

    def render(scene, scene_t, speaking_frac, sec=0.0):
        img = base.copy()
        d = ImageDraw.Draw(img)
        vis = scene.get("visual", {})
        outro = vis.get("type") == "outro"
        if not outro:
            d.text((W // 2, 130), series, font=font(34), fill=col["accent"], anchor="mm")
            f = font(76)
            y = 250
            for line in _wrap(scene.get("on_screen", ""), f, W - 140, d):
                d.text((W // 2, y), line, font=f, fill=col["text"], anchor="mm")
                y += 92
        VISUALS[vis["type"]](img, d, vis, scene_t, col, brand, episode, sec)
        _draw_subtitle(d, scene["text"], scene_t, col, 1.0 - speaking_frac)
        if not outro:
            d.text((W // 2, 1560), brand["channel_name"].upper(), font=font(30), fill=col["muted"], anchor="mm")
        return img

    return render
