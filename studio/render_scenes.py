"""Render an episode's Blender scenes one at a time (resumable, low-RAM friendly).

  python -m studio.render_scenes 013 --preview              # 25% size, quick check
  python -m studio.render_scenes 013 --final                # full 1080x1920 (slow on an i5: run overnight)
  python -m studio.render_scenes 013 --only catch --preview
  python -m studio.render_scenes 013 --list

The episode YAML says what to render:   render: {script: blender/aero/starship_catch.py}
and every scene with  visual: {type: render_clip, clip: <name>, seconds: N}  becomes renders/<id>/<name>/f_0001.png ...
Already rendered frames are skipped, so you can stop (Ctrl+C) and continue later. Runs ONE Blender at a time.
"""
import argparse
import subprocess
import sys

from src.common import ROOT, load_yaml
from src.run_episode import resolve_episode
from .paths import find_tool, tools_config


def plan(ep):
    script = (ep.get("render") or {}).get("script")
    clips = []
    for sc in ep.get("scenes", []):
        v = sc.get("visual", {})
        if v.get("type") == "render_clip" and v["clip"] not in [c[0] for c in clips]:
            clips.append((v["clip"], float(v.get("seconds", 0)) or None))
    return script, [c[0] for c in clips]


def command(blender, script, clip, out_dir, rcfg, final, hdri=None, frames=None):
    cmd = [blender, "-b", "-P", str(script), "--", clip, str(out_dir),
           "--scale", str(rcfg.get("final_scale", 100) if final else rcfg.get("preview_scale", 25)),
           "--samples", str(rcfg.get("samples", 32)), "--engine", rcfg.get("engine", "BLENDER_EEVEE_NEXT"),
           "--fps", str(rcfg.get("render_fps", 15))]
    if hdri:
        cmd += ["--hdri", str(hdri)]
    if frames:
        cmd += ["--frames", str(frames)]
    return cmd


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("episode")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--preview", action="store_true")
    g.add_argument("--final", action="store_true")
    ap.add_argument("--only", help="render just this clip")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--frames", type=int, help="limit frames (test)")
    a = ap.parse_args(argv)
    ep = load_yaml(resolve_episode(a.episode))
    script, clips = plan(ep)
    if a.list or not script:
        print(f"script: {script}\nclips: {', '.join(clips) or '(none)'}")
        return 0 if script else 1
    blender = find_tool("blender")
    if not blender:
        raise SystemExit("Blender not found. Install it (docs/TOOLS.md) or set paths.blender in config/tools.yml.")
    cfg = tools_config()
    rcfg = cfg.get("render", {})
    try:
        from .polyhaven import find_hdri
        hdri = find_hdri()
    except Exception:
        hdri = None
    # preview and final renders are kept apart so a quick preview never blocks a final render
    sub = "final" if a.final else "preview"
    for clip in clips:
        if a.only and clip != a.only:
            continue
        out = ROOT / rcfg.get("out_dir", "renders") / ep["id"] / clip
        if a.preview:
            out = ROOT / rcfg.get("out_dir", "renders") / f"{ep['id']}_preview" / clip
        print(f"== {clip} ({sub}) -> {out}")
        r = subprocess.run(command(blender, ROOT / script, clip, out, rcfg, a.final, hdri, a.frames))
        if r.returncode != 0:
            print(f"Blender failed on '{clip}' (exit {r.returncode}); continuing with the next scene.")
    print("Finished. Next: python -m studio.edit_project", ep["id"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
