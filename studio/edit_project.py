"""Build an organised Kdenlive editing folder for one episode, from what the pipeline already made.

  python -m src.run_episode 013 --tts piper --force --out out      (builds narration, subtitles, timeline)
  python -m studio.edit_project 013                  # uses out/013-<slug>/ and renders/013/
  python -m studio.edit_project 013 --run-dir D:\\cutaway\\out --music assets\\music\\theme.mp3

Creates edit/<id>-<slug>/ :
  01_video/      per-scene Blender renders encoded to MP4 (ffmpeg) + auto_build.mp4 (the pipeline's own cut)
  02_voice/      voice.wav (Piper, voice only) and mix.wav (voice + sound effects)
  03_sfx/        sfx_only.wav if you put one there (optional)
  04_music/      background music you choose (copied only when you pass --music)
  05_subtitles/  subtitles.srt (same timing as the burned-in subtitles)
  06_graphics/   put logos / lower thirds here
  07_exports/    final renders from Kdenlive
  00_project/    EDITING_GUIDE.md, MANIFEST.md, vertical.profile, assembly.mlt (rough cut, experimental)

Nothing is deleted or overwritten without --force. The Kdenlive project itself is made by you once from the
vertical profile (see guide) so every manual adjustment stays possible; if edit/templates/*.kdenlive exists it
is copied in as the starting project.
"""
import argparse
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from src.common import ROOT, load_brand, load_yaml
from src.run_episode import resolve_episode
from .paths import find_tool, tools_config

FOLDERS = ["00_project", "01_video", "02_voice", "03_sfx", "04_music", "05_subtitles", "06_graphics", "07_exports"]


def _copy(src, dst, force=False):
    src, dst = Path(src), Path(dst)
    if not src.exists():
        return False
    if dst.exists() and not force:
        return True
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def encode_sequence(ffmpeg, frames_dir, out_mp4, fps):
    """PNG sequence f_0001.png ... (Blender default) or f_000.png ... -> H.264 MP4."""
    pngs = sorted(Path(frames_dir).glob("f_*.png"))
    if not pngs:
        return False
    first = pngs[0].stem[2:]                                  # digits after 'f_'
    pattern = str(Path(frames_dir) / f"f_%0{len(first)}d.png")
    start = int(first)
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-framerate", str(fps), "-start_number", str(start),
                    "-i", pattern, "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                    "-pix_fmt", "yuv420p", str(out_mp4)], check=True)
    return True


def vertical_profile(brand):
    v = brand["video"]
    return (f"description={tools_config().get('edit', {}).get('profile_name', 'Cutaway Vertical')}\n"
            f"frame_rate_num={v['fps']}\nframe_rate_den=1\nwidth={v['width']}\nheight={v['height']}\n"
            f"progressive=1\nsample_aspect_num=1\nsample_aspect_den=1\n"
            f"display_aspect_num=9\ndisplay_aspect_den=16\ncolorspace=709\n")


def build_mlt(timeline, files, brand, music_gain=0.1):
    """A plain MLT XML rough cut (video + voice + sfx + music). Renders with melt; experimental."""
    fps = int(brand["video"]["fps"])
    mlt = ET.Element("mlt", {"LC_NUMERIC": "C"})
    ET.SubElement(mlt, "profile", {"description": "Cutaway Vertical", "width": str(brand["video"]["width"]),
                                   "height": str(brand["video"]["height"]), "progressive": "1",
                                   "sample_aspect_num": "1", "sample_aspect_den": "1",
                                   "display_aspect_num": "9", "display_aspect_den": "16",
                                   "frame_rate_num": str(fps), "frame_rate_den": "1", "colorspace": "709"})

    def producer(pid, path, gain=None):
        p = ET.SubElement(mlt, "producer", {"id": pid})
        ET.SubElement(p, "property", {"name": "resource"}).text = str(Path(path).resolve())
        if gain is not None:
            f = ET.SubElement(p, "filter", {"mlt_service": "volume"})
            ET.SubElement(f, "property", {"name": "gain"}).text = str(gain)
        return p

    video = ET.Element("playlist", {"id": "video"})
    scene_clips = files.get("scene_clips", {})
    if scene_clips:
        for i, sc in enumerate(timeline["scenes"]):
            frames = max(1, round(sc["duration"] * fps))
            clip = scene_clips.get(sc["id"])
            if clip:
                producer(f"v{i}", clip)
                ET.SubElement(video, "entry", {"producer": f"v{i}", "in": "0", "out": str(frames - 1)})
            else:
                ET.SubElement(video, "blank", {"length": str(frames)})
    elif files.get("auto_build"):
        producer("v0", files["auto_build"])
        ET.SubElement(video, "entry", {"producer": "v0", "in": "0",
                                       "out": str(round(timeline["total_seconds"] * fps) - 1)})
    tracks = [("video", video)]
    for pid, key, gain in (("voice", "voice", None), ("sfx", "sfx", None), ("music", "music", music_gain)):
        if files.get(key):
            producer(pid + "_p", files[key], gain)
            pl = ET.Element("playlist", {"id": pid})
            ET.SubElement(pl, "entry", {"producer": pid + "_p"})
            tracks.append((pid, pl))
    for _, pl in tracks:
        mlt.append(pl)
    tractor = ET.SubElement(mlt, "tractor", {"id": "cutaway"})
    mt = ET.SubElement(tractor, "multitrack")
    for pid, _ in tracks:
        ET.SubElement(mt, "track", {"producer": pid})
    for b in range(2, len(tracks)):                           # mix every audio track into the voice track
        ET.SubElement(tractor, "transition", {"mlt_service": "mix", "a_track": "1", "b_track": str(b),
                                              "always_active": "1", "sum": "1"})
    ET.indent(mlt)
    return ET.tostring(mlt, encoding="unicode", xml_declaration=False)


def guide_text(ep, tl, folder, profile_name):
    return f"""# Editing guide: episode {ep['id']} ({ep['slug']})

Folder: `{folder}`. Length from the script: {tl['total_seconds']:.1f} s. Everything stays editable by hand.

## One-time setup (Kdenlive)
1. Install Kdenlive (free): see docs/TOOLS.md. Nothing in this repo installs it for you.
2. File > New. In Project Settings choose *Custom* (or the profile named **{profile_name}** if you copied
   `00_project/vertical.profile` into Kdenlive's profiles folder): 1080 x 1920, 30 fps, progressive, 9:16.
3. Save it as a template: File > Save As `edit/templates/cutaway_vertical.kdenlive`. Next episodes copy it automatically.

## Each episode
1. Project Bin > Add Folder: pick `01_video`, `02_voice`, `03_sfx`, `04_music` (one click each).
2. Put the scene clips on V1 in order (names are `NN_<scene-id>.mp4`), the voice on A1, effects on A2, music on A3.
   Cut points are in `MANIFEST.md`. `auto_build.mp4` is the pipeline's own finished cut, handy as a reference.
3. Subtitles: Project > Subtitles > Import (or drop) `05_subtitles/subtitles.srt`. They match the timing of the burned-in ones.
   Keep only one of the two (the pipeline's cut already burns subtitles in; a clean Blender render does not).
4. Music: keep it 10 to 15 dB under the voice (about -20 dB). Audio ducking: add *Auto Fade* or lower the music clip by hand.
5. Render: Project > Render, preset MP4 (H.264 + AAC), 1080x1920, save into `07_exports/`.

## Low-RAM tips (8 GB PC)
Enable Proxy clips (Project Settings > Proxy), close Blender before editing, edit one scene at a time.

## Rough cut without opening Kdenlive (experimental)
`melt 00_project/assembly.mlt -consumer avformat:07_exports/rough.mp4 vcodec=libx264 acodec=aac`
(`melt.exe` is inside the Kdenlive install folder.) It has not been verified on a real PC yet; tell the maintainer if it fails.
"""


def build_project(ep_arg, run_dir=None, renders=None, music=None, force=False, log=print):
    ep = load_yaml(resolve_episode(ep_arg))
    brand = load_brand()
    cfg = tools_config()
    name = f"{ep['id']}-{ep['slug']}"
    run = Path(run_dir) / name if run_dir else ROOT / "out" / name
    if not (run / "timeline.json").exists():
        raise SystemExit(f"No timeline.json in {run}. Build the episode first, for example:\n"
                         f"  python -m src.run_episode {ep['id']} --tts piper --force --out out")
    tl = json.loads((run / "timeline.json").read_text(encoding="utf-8"))
    base = ROOT / cfg.get("edit", {}).get("dir", "edit") / name
    for f in FOLDERS:
        (base / f).mkdir(parents=True, exist_ok=True)

    files = {}
    mp4 = run / f"{name}.mp4"
    if _copy(mp4, base / "01_video" / "auto_build.mp4", force):
        files["auto_build"] = base / "01_video" / "auto_build.mp4"
    if _copy(run / "voice_fx.wav", base / "02_voice" / "voice.wav", force):
        files["voice"] = base / "02_voice" / "voice.wav"
    _copy(run / "narration.wav", base / "02_voice" / "mix.wav", force)
    if _copy(run / "sfx_only.wav", base / "03_sfx" / "sfx_only.wav", force):
        files["sfx"] = base / "03_sfx" / "sfx_only.wav"
    _copy(run / "subtitles.srt", base / "05_subtitles" / "subtitles.srt", force)
    if music:
        if _copy(music, base / "04_music" / Path(music).name, force):
            files["music"] = base / "04_music" / Path(music).name

    ffmpeg = find_tool("ffmpeg")
    rdir = Path(renders) if renders else ROOT / cfg.get("render", {}).get("out_dir", "renders") / ep["id"]
    clips = {}
    if rdir.exists() and ffmpeg:
        for i, sc in enumerate(tl["scenes"], 1):
            for cand in (rdir / sc["id"], rdir / f"{i:02d}_{sc['id']}", rdir / f"scene_{i:02d}"):
                if cand.exists():
                    out_clip = base / "01_video" / f"{i:02d}_{sc['id']}.mp4"
                    if not out_clip.exists() or force:
                        if encode_sequence(ffmpeg, cand, out_clip, brand["video"]["fps"]):
                            log(f"  encoded {out_clip.name}")
                    if out_clip.exists():
                        clips[sc["id"]] = out_clip
                    break
    files["scene_clips"] = clips

    (base / "00_project" / "vertical.profile").write_text(vertical_profile(brand), encoding="utf-8")
    (base / "00_project" / "assembly.mlt").write_text(build_mlt(tl, files, brand), encoding="utf-8")
    prof = cfg.get("edit", {}).get("profile_name", "Cutaway Vertical")
    (base / "00_project" / "EDITING_GUIDE.md").write_text(guide_text(ep, tl, base, prof), encoding="utf-8")
    man = [f"# Manifest: {name}", "", "| # | Scene | Start (s) | Length (s) | Visual | Clip |", "|---|---|---|---|---|---|"]
    for i, sc in enumerate(tl["scenes"], 1):
        man.append(f"| {i} | {sc['id']} | {sc['start']:.2f} | {sc['duration']:.2f} | {sc['visual']} | "
                   f"{clips[sc['id']].name if sc['id'] in clips else '(none: auto_build only)'} |")
    (base / "00_project" / "MANIFEST.md").write_text("\n".join(man) + "\n", encoding="utf-8")
    tpl = sorted((ROOT / cfg.get("edit", {}).get("dir", "edit") / "templates").glob("*.kdenlive"))
    if tpl and not (base / f"{name}.kdenlive").exists():
        shutil.copy2(tpl[0], base / f"{name}.kdenlive")
        log(f"  started the project from template {tpl[0].name}")
    log(f"Edit folder ready: {base}")
    return base


def main(argv=None):
    ap = argparse.ArgumentParser(description="Create an organised Kdenlive editing folder")
    ap.add_argument("episode")
    ap.add_argument("--run-dir", help="folder that holds <id>-<slug>/ from run_episode (default: out/)")
    ap.add_argument("--renders", help="folder of per-scene PNG sequences (default: renders/<id>/)")
    ap.add_argument("--music", help="background music file to copy into 04_music")
    ap.add_argument("--force", action="store_true", help="overwrite files in the edit folder")
    a = ap.parse_args(argv)
    build_project(a.episode, a.run_dir, a.renders, a.music, a.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
