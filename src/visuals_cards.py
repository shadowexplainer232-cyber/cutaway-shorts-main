"""Text cards for endings: a bonus fact, a question for viewers, a takeaway.

  visual: {type: fact_card, label: "ONE MORE THING",
           lines: ["SOME ENGINES USE BOTH", "SUPERCHARGER AT LOW SPEED"],
           colors: [accent, text], sub: "optional small line"}

Lines appear one at a time (about one second apart) so the viewer has time to read each one.
"""
from .common import font
from .visuals_jet import _mix, _ease

W, H = 1080, 1920


def _wrap(d, text, f, max_w):
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if d.textlength(trial, font=f) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_fact_card(img, d, vis, scene_t, col, brand, ep, sec=0.0):
    bg = col["bg"]
    label = vis.get("label", "")
    if label:
        f = font(34)
        w = d.textlength(label, font=f) + 90
        a = _ease(sec * 4)
        d.rounded_rectangle([W / 2 - w / 2, 560, W / 2 + w / 2, 624], radius=32, fill=_mix(bg, col["accent"], a))
        d.text((W // 2, 592), label, font=f, fill=_mix(col["accent"], bg, a), anchor="mm")

    colors = vis.get("colors", [])
    y = 760
    for i, line in enumerate(vis.get("lines", [])):
        key = colors[i] if i < len(colors) else ("accent" if i == 0 else "text")
        a = _ease((sec - (0.5 + 1.0 * i)) * 3)
        f = font(66)
        for part in _wrap(d, line, f, W - 140):
            d.text((W // 2, y), part, font=f, fill=_mix(bg, col[key], a), anchor="mm")
            y += 88
        y += 34
    if vis.get("sub"):
        a = _ease((sec - (0.5 + 1.0 * len(vis.get("lines", [])))) * 3)
        d.text((W // 2, y + 20), vis["sub"], font=font(34), fill=_mix(bg, col["muted"], a), anchor="mm")
