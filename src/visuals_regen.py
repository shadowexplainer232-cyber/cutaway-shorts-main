"""Hybrid braking: normal brakes make heat, regenerative braking charges the battery (schematic).

  stage: drive | heat | generator | battery | both | switch
Layout: wheel (left) - motor/generator (middle) - battery (right). Orange dots = motion/energy
moving; blue dots = electricity. Illustrative, not an engineering drawing.
"""
import math
import random

from .common import font
from .visuals_jet import _mix, _ease
from .visuals_turbo import _flow, _pipe

W, H = 1080, 1920
WHEEL = (190, 850)
MOTOR = (360, 770, 620, 930)
BATT = (830, 735, 960, 965)
MECH = [(290, 850), (360, 850)]
ELEC = [(620, 850), (830, 850)]


def _wheel(d, col, rot, disc_heat=0.0, k=1.0):
    bg = col["bg"]
    x, y = WHEEL
    d.ellipse([x - 112, y - 112, x + 112, y + 112], fill=_mix(bg, col["text"], 0.20 * k + 0.10))
    d.ellipse([x - 100, y - 100, x + 100, y + 100], fill=_mix(bg, col["muted"], 0.45 * k + 0.15))
    heat = _mix(_mix(bg, col["muted"], 0.6), (230, 70, 40), disc_heat)
    d.ellipse([x - 62, y - 62, x + 62, y + 62], fill=heat, outline=_mix(bg, col["text"], 0.6 * k + 0.2), width=4)
    for j in range(5):
        a = rot + 2 * math.pi * j / 5
        d.line([(x, y), (x + 92 * math.cos(a), y + 92 * math.sin(a))], fill=_mix(bg, col["text"], 0.5 * k + 0.2), width=7)
    d.ellipse([x - 14, y - 14, x + 14, y + 14], fill=col["text"])


def _motor(d, col, k, label_color):
    bg = col["bg"]
    x0, y0, x1, y1 = MOTOR
    d.rounded_rectangle([x0, y0, x1, y1], radius=20, fill=_mix(bg, col["tech"], 0.10 + 0.25 * k),
                        outline=_mix(bg, col["tech"], 0.35 + 0.65 * k), width=6)
    d.text(((x0 + x1) // 2, 850), "M / G", font=font(44), fill=_mix(bg, label_color, 0.4 + 0.6 * k), anchor="mm")


def _battery(d, col, level, k):
    bg = col["bg"]
    x0, y0, x1, y1 = BATT
    d.rounded_rectangle([x0 + 35, y0 - 22, x1 - 35, y0], radius=6, fill=_mix(bg, col["muted"], 0.6))
    d.rounded_rectangle([x0, y0, x1, y1], radius=16, outline=_mix(bg, col["text"], 0.35 + 0.6 * k), width=6)
    h = (y1 - y0 - 24) * level
    if h > 4:
        d.rounded_rectangle([x0 + 12, y1 - 12 - h, x1 - 12, y1 - 12], radius=8,
                            fill=_mix(bg, col["accent"], 0.5 + 0.5 * k))
    d.text(((x0 + x1) // 2, y0 - 50), f"{int(level * 100)}%", font=font(28), fill=_mix(bg, col["text"], 0.5 + 0.5 * k), anchor="mm")


def draw_regen(img, d, vis, scene_t, col, brand, ep, sec=0.0):
    stage = vis.get("stage", "drive")
    bg = col["bg"]
    mode = "brake"
    kw, km, kb = 1.0, 1.0, 1.0                 # how lit wheel / motor / battery are
    heat = 0.0
    level = 0.55
    title = ""
    if stage == "drive":
        mode, title = "drive", "DRIVING: BATTERY → MOTOR → WHEEL"
        level = 0.55
    elif stage == "switch":                     # hook: drive for a moment, then brake
        mode = "drive" if sec < 2.2 else "brake"
        title = "DRIVING..." if sec < 2.2 else "BRAKING: THE FLOW REVERSES"
        level = 0.55 + (0.12 * _ease((sec - 2.4) / 3.0) if sec > 2.4 else 0)
    elif stage == "heat":
        title = "NORMAL BRAKES: MOTION BECOMES HEAT"
        km, kb = 0.25, 0.25
        heat = _ease(sec / 2.5)
    elif stage == "generator":
        title = "THE MOTOR WORKS AS A GENERATOR"
        kw, kb = 0.5, 0.5
    elif stage == "battery":
        title = "THE BATTERY CHARGES"
        kw = 0.5
        level = 0.40 + 0.40 * _ease(sec / 4.0)
    elif stage == "both":
        title = "FRICTION BRAKES ARE STILL THERE"
        level = 0.7

    rot = 7.0 * sec * (1.0 if mode == "drive" else max(0.35, 1.0 - 0.08 * sec))
    _pipe(d, col, MECH, col["accent"], 1.0 if stage != "heat" else 0.2)
    _pipe(d, col, ELEC, col["tech"], kb if stage != "heat" else 0.2)
    _wheel(d, col, rot, heat, kw)
    _motor(d, col, km, col["tech"])
    _battery(d, col, level, kb)

    if stage != "heat":
        mech, elec = (MECH, ELEC) if mode == "drive" else (MECH[::-1], ELEC[::-1])
        # in braking, motion flows wheel -> motor -> battery: lists run from wheel side to battery side
        if mode == "brake":
            mech, elec = MECH, ELEC
        else:
            mech, elec = MECH[::-1], ELEC[::-1]
        _flow(d, col, mech, 3, 0.25, sec, lambda s: col["accent"], kw if stage != "generator" else 1.0)
        _flow(d, col, elec, 6, 0.25, sec, lambda s: col["tech"], kb if stage != "generator" else 1.0)
    else:
        rnd = random.Random(3)
        for i in range(10):                                  # heat rising off the brake disc
            s = (i / 10 + sec * 0.4) % 1.0
            x = WHEEL[0] - 70 + rnd.uniform(0, 140) + 10 * math.sin(sec * 3 + i)
            y = WHEEL[1] - 110 - s * 170
            d.line([(x - 9, y), (x, y - 14), (x + 9, y)], fill=_mix(bg, (240, 90, 50), 0.9 * (1 - s)), width=4)
        d.text((WHEEL[0], WHEEL[1] - 330), "HEAT: WASTED", font=font(30),
               fill=_mix(bg, (240, 110, 60), _ease((sec - 0.6) * 2)), anchor="mm")

    if stage == "both":
        a = _ease(sec * 1.5)
        x, y = WHEEL
        d.rounded_rectangle([x + 70, y - 52, x + 108, y + 52], radius=6, fill=_mix(bg, col["accent"], a))
        d.rounded_rectangle([x - 108, y - 52, x - 70, y + 52], radius=6, fill=_mix(bg, col["accent"], a))
        d.text((540, 1100), "HARD STOP? FRICTION BRAKES TAKE OVER", font=font(30),
               fill=_mix(bg, col["accent"], _ease((sec - 1.2) * 2)), anchor="mm")

    d.text((WHEEL[0], 1010), "WHEEL", font=font(26), fill=col["text"], anchor="mm")
    d.text((490, 1010), "MOTOR / GENERATOR", font=font(26), fill=col["text"], anchor="mm")
    d.text((895, 1010), "BATTERY", font=font(26), fill=col["text"], anchor="mm")
    if title:
        d.text((W // 2, 600), title, font=font(32), fill=_mix(bg, col["accent"], _ease(sec * 2)), anchor="mm")

    if vis.get("callout"):
        a = _ease(sec * 3.0)
        size = 42
        while d.textlength(vis["callout"], font=font(size)) > W - 100 and size > 26:
            size -= 2
        d.text((W // 2, 1200), vis["callout"], font=font(size), fill=_mix(bg, col["accent"], a), anchor="mm")
    d.text((W // 2, 1252), "Simplified animation", font=font(24), fill=col["muted"], anchor="mm")
