"""Shared helpers: config loading, fonts, colour parsing."""
from pathlib import Path
import yaml
from PIL import ImageFont

ROOT = Path(__file__).resolve().parent.parent


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_brand():
    return load_yaml(ROOT / "config" / "brand.yml")


def rgb(hex_str):
    h = hex_str.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


_FONT_CANDIDATES = [
    ROOT / "assets" / "fonts" / "Montserrat-Bold.ttf",
    Path("/usr/share/fonts/truetype/montserrat/Montserrat-Bold.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
]


def font(size):
    for p in _FONT_CANDIDATES:
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()
