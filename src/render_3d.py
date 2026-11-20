"""Render the 3D engine loop with Blender (headless). Falls back silently to the 2D animation
if Blender is not installed. Frames are cached in assets/engine3d/ and reused by every episode.

  python -m src.render_3d              # uses BLENDER env var or 'blender' on PATH
"""
import json
import os
import shutil
import subprocess
import sys

from .common import ROOT, load_brand

OUT = ROOT / "assets" / "engine3d"


def main():
    cfg = load_brand().get("blender", {})
    if not cfg.get("enabled", False):
        print("Blender disabled in config/brand.yml; using 2D animation.")
        return
    exe = os.environ.get("BLENDER") or shutil.which("blender")
    if not exe:
        print("Blender not found; using 2D animation.")
        return
    n, samples, engine = int(cfg.get("frames", 180)), int(cfg.get("samples", 24)), cfg.get("engine", "CYCLES")
    meta = OUT / "meta.json"
    want = {"frames": n, "samples": samples, "engine": engine}
    if meta.exists() and json.loads(meta.read_text()) == want and len(list(OUT.glob("f_*.png"))) == n:
        print("3D frames already rendered.")
        return
    OUT.mkdir(parents=True, exist_ok=True)
    script = ROOT / "blender" / "engine_cycle.py"
    subprocess.run([exe, "-b", "-noaudio", "-P", str(script), "--", str(OUT), str(n), str(samples), engine],
                   check=True)
    if len(list(OUT.glob("f_*.png"))) != n:
        sys.exit("Blender finished but frames are missing; keeping 2D fallback (no meta.json written).")
    meta.write_text(json.dumps(want))
    print("Rendered", n, "frames")


if __name__ == "__main__":
    main()
