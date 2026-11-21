"""Render the optional 3D loops with Blender (headless). Every scene is independent: if Blender is
missing, disabled, or a scene fails, that scene silently keeps its 2D animation.

  python -m src.render_3d              # uses BLENDER env var or 'blender' on PATH

Scenes (frames are cached in assets/<name>/ and reused by every episode):
  engine3d       blender/engine_cycle.py   four-stroke engine (frames/samples from config/brand.yml)
  intercooler3d  blender/intercooler.py    compressor -> intercooler -> engine loop (90 frames)
"""
import json
import os
import shutil
import subprocess
import traceback

from .common import ROOT, load_brand

# name, script, fixed frame count (None = use config/brand.yml blender.frames)
SCENES = [
    ("engine3d", "engine_cycle.py", None),
    ("intercooler3d", "intercooler.py", 90),
]


def render_scene(exe, cfg, name, script, frames):
    out = ROOT / "assets" / name
    n = int(frames or cfg.get("frames", 180))
    samples, engine = int(cfg.get("samples", 24)), cfg.get("engine", "CYCLES")
    want = {"frames": n, "samples": samples, "engine": engine}
    meta = out / "meta.json"
    if meta.exists() and json.loads(meta.read_text()) == want and len(list(out.glob("f_*.png"))) == n:
        print(f"[{name}] 3D frames already rendered.")
        return
    out.mkdir(parents=True, exist_ok=True)
    subprocess.run([exe, "-b", "-noaudio", "-P", str(ROOT / "blender" / script), "--",
                    str(out), str(n), str(samples), engine], check=True)
    if len(list(out.glob("f_*.png"))) != n:
        print(f"[{name}] Blender finished but frames are missing; keeping the 2D fallback.")
        return
    meta.write_text(json.dumps(want))
    print(f"[{name}] Rendered {n} frames")


def main():
    cfg = load_brand().get("blender", {})
    if not cfg.get("enabled", False):
        print("Blender disabled in config/brand.yml; using 2D animations.")
        return
    exe = os.environ.get("BLENDER") or shutil.which("blender")
    if not exe:
        print("Blender not found; using 2D animations.")
        return
    for name, script, frames in SCENES:
        try:
            render_scene(exe, cfg, name, script, frames)
        except Exception:                                   # one failing scene must not block the others
            print(f"[{name}] 3D render failed; using the 2D animation for it.")
            traceback.print_exc()


if __name__ == "__main__":
    main()
