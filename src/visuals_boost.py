"""Side-by-side supercharger vs turbocharger (2D, Pillow, schematic).

  stage: intro (both dim) | super | turbo | diff (both lit, the two "drivers" outlined)
Left column: a belt from the engine spins the compressor. Right column: exhaust spins a turbine,
a shaft spins the compressor. Shapes and speeds are illustrative, not an engineering drawing.
"""
import math

from .common import font
from .visuals_jet import _mix, _ease
from .visuals_turbo import _flow, _pipe, _wheel

W, H = 1080, 1920
RW = 58                                    # wheel radius in this view

LIT = {
    "intro": (0.45, 0.45),
    "super": (1.0, 0.3),
    "turbo": (0.3, 1.0),
    "diff":  (1.0, 1.0),
}


def _engine(d, col, cx, k, sec):
    bg = col["bg"]
    x0, y0, x1, y1 = cx - 110, 560, cx + 110, 700
    d.rounded_rectangle([x0, y0, x1, y1], radius=16, fill=_mix(bg, col["muted"], 0.2 + 0.25 * k),
                        outline=_mix(bg, col["muted"], 0.4 + 0.5 * k), width=5)
    for c in range(3):
        flash = max(0.0, math.sin(sec * 5 + c * 2.1)) ** 4 * k
        d.rectangle([cx - 92 + c * 70, y0 + 22, cx - 52 + c * 70, y0 + 82], fill=_mix(bg, col["accent"], 0.08 + 0.85 * flash))
    d.text((cx, y1 - 22), "ENGINE", font=font(24), fill=_mix(bg, col["text"], 0.4 + 0.6 * k), anchor="mm")


def _supercharger(d, col, cx, k, sec, highlight):
    bg = col["bg"]
    wheel = (cx - 70, 920)
    pulley = (cx - 70, 735)
    air_in = [(20, 920), (wheel[0] - RW, 920)]
    air_out = [(wheel[0] + RW, 920), (cx + 70, 920), (cx + 70, 700)]
    _pipe(d, col, air_in, col["tech"], k)
    _pipe(d, col, air_out, col["tech"], k)
    _engine(d, col, cx, k, sec)

    # belt from the crankshaft pulley down to the compressor wheel
    belt_c = col["accent"] if highlight else _mix(bg, col["text"], 0.3 + 0.5 * k)
    for dx in (-24, 24):
        d.line([(pulley[0] + dx, pulley[1]), (wheel[0] + dx, wheel[1])], fill=belt_c, width=8 if highlight else 6)
    for i in range(8):
        y = pulley[1] + ((i / 8 + sec * 0.35 * k) % 1) * (wheel[1] - pulley[1])
        d.ellipse([pulley[0] - 24 - 4, y - 4, pulley[0] - 24 + 4, y + 4], fill=_mix(bg, col["accent"], 0.2 + 0.8 * k))
        d.ellipse([pulley[0] + 24 - 4, y - 4, pulley[0] + 24 + 4, y + 4], fill=_mix(bg, col["accent"], 0.2 + 0.8 * k))
    d.ellipse([pulley[0] - 24, pulley[1] - 24, pulley[0] + 24, pulley[1] + 24],
              fill=_mix(bg, col["muted"], 0.5 + 0.5 * k), outline=col["text"] if k > 0.9 else col["muted"], width=3)

    rot = 8.0 * sec * k
    _wheel(d, col, wheel, rot, col["tech"], k, radius=RW)
    _flow(d, col, air_in, 4, 0.2, sec, lambda s: col["tech"], k)
    _flow(d, col, air_out, 8, 0.2, sec, lambda s: _mix(col["tech"], col["text"], 0.55), k)

    d.text((cx, 525), "SUPERCHARGER", font=font(34), fill=_mix(bg, col["text"], 0.4 + 0.6 * k), anchor="mm")
    d.text((cx - 150, 830), "BELT", font=font(22), fill=_mix(bg, col["accent"], 0.35 + 0.65 * k), anchor="mm")
    d.text((90, 885), "AIR IN", font=font(22), fill=_mix(bg, col["tech"], 0.35 + 0.65 * k), anchor="mm")


def _turbocharger(d, col, cx, k, sec, highlight):
    bg = col["bg"]
    comp, turb = (cx - 70, 920), (cx + 80, 920)
    air_in = [(cx - 250, 920), (comp[0] - RW, 920)]
    air_out = [(comp[0], 920 - RW), (comp[0], 700)]
    exh = [(cx + 110, 620), (cx + 190, 620), (cx + 190, 800), (turb[0], 920 - RW)]
    _pipe(d, col, air_in, col["tech"], k)
    _pipe(d, col, air_out, col["tech"], k)
    _pipe(d, col, exh, col["accent"], k)
    if highlight:
        d.line(exh, fill=col["accent"], width=48, joint="curve")
        _pipe(d, col, exh, col["accent"], 1.0)
    _engine(d, col, cx, k, sec)

    d.rectangle([comp[0] + RW, 910, turb[0] - RW, 930], fill=_mix(bg, col["text"], 0.25 + 0.5 * k))
    rot = 8.0 * sec * k
    _wheel(d, col, comp, rot, col["tech"], k, radius=RW)
    _wheel(d, col, turb, rot, col["accent"], k, radius=RW)
    _flow(d, col, air_in, 4, 0.2, sec, lambda s: col["tech"], k)
    _flow(d, col, air_out, 6, 0.2, sec, lambda s: _mix(col["tech"], col["text"], 0.55), k)
    _flow(d, col, exh, 10, 0.2, sec, lambda s: col["accent"] if s < 0.7 else _mix(col["accent"], col["muted"], 0.6), k)

    d.text((cx, 525), "TURBOCHARGER", font=font(34), fill=_mix(bg, col["text"], 0.4 + 0.6 * k), anchor="mm")
    d.text((cx + 175, 715), "EXHAUST", font=font(22), fill=_mix(bg, col["accent"], 0.35 + 0.65 * k), anchor="mm")
    d.text((cx - 190, 885), "AIR IN", font=font(22), fill=_mix(bg, col["tech"], 0.35 + 0.65 * k), anchor="mm")


def draw_boost_compare(img, d, vis, scene_t, col, brand, ep, sec=0.0):
    bg = col["bg"]
    stage = vis.get("stage", "diff")
    kl, kr = LIT.get(stage, LIT["diff"])
    highlight = stage == "diff"
    _supercharger(d, col, 270, kl, sec, highlight)
    _turbocharger(d, col, 810, kr, sec, highlight)
    d.line([(540, 520), (540, 1110)], fill=_mix(bg, col["muted"], 0.5), width=3)

    def verdict(cx, lines, k, color):
        if k < 0.9:
            return
        for i, (text, c) in enumerate(lines):
            a = _ease((sec - 0.8 - 0.7 * i) * 3)
            d.text((cx, 1040 + i * 44), text, font=font(28), fill=_mix(bg, col[c], a), anchor="mm")

    if stage in ("super", "diff"):
        verdict(270, [("INSTANT RESPONSE", "tech"), ("USES ENGINE POWER", "muted")], kl, col["tech"])
    if stage in ("turbo", "diff"):
        verdict(810, [("A MOMENT TO SPIN UP", "accent"), ("USES LITTLE ENGINE POWER", "muted")], kr, col["accent"])

    if vis.get("callout"):
        a = _ease(sec * 3.0)
        size = 42
        while d.textlength(vis["callout"], font=font(size)) > W - 100 and size > 26:
            size -= 2
        d.text((W // 2, 1200), vis["callout"], font=font(size), fill=_mix(bg, col["accent"], a), anchor="mm")
    d.text((W // 2, 1252), "Simplified animation", font=font(24), fill=col["muted"], anchor="mm")
