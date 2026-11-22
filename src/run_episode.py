"""Build one episode.

  python -m src.run_episode episodes/001-four-stroke-engine.yml --tts piper
  python -m src.run_episode episodes/001-four-stroke-engine.yml --tts stub     (silent test render)
  python -m src.run_episode ... --upload    (private YouTube upload, needs secrets)
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .common import ROOT, load_brand, load_yaml
from .tts import synthesize, join_narration
from .sfx import apply_voice_effect, mix, export_mp3
from .build_video import build

STATE = ROOT / "state" / "done.json"


def resolve_episode(arg):
    """Accept a path, or just an episode number/slug such as 1, 001 or four-stroke-engine."""
    for cand in (Path(arg), ROOT / arg, ROOT / "episodes" / arg, ROOT / "episodes" / f"{arg}.yml"):
        if cand.is_file():
            return cand
    files = sorted((ROOT / "episodes").glob("*.yml"))
    key = arg.split(":")[0].strip().lower()
    for f in files:
        ep = load_yaml(f)
        if (key.isdigit() and str(ep.get("id", "")).isdigit() and int(ep["id"]) == int(key)) \
                or key in (str(ep.get("id", "")).lower(), str(ep.get("slug", "")).lower()):
            return f
    names = ", ".join(f.name for f in files) or "none"
    raise SystemExit(f"Episode '{arg}' not found. Use a path like episodes/001-four-stroke-engine.yml "
                     f"or an episode number. Available: {names}")


def done_ids():
    return set(json.loads(STATE.read_text())) if STATE.exists() else set()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode")
    ap.add_argument("--tts", choices=["piper", "stub", "files"], default="piper")
    ap.add_argument("--audio-dir", help="with --tts files: folder of narration clips, one per scene")
    ap.add_argument("--out", default=str(ROOT / "out"))
    ap.add_argument("--upload", action="store_true")
    ap.add_argument("--force", action="store_true", help="skip the approval checks (testing only)")
    a = ap.parse_args()

    ep = load_yaml(resolve_episode(a.episode))
    brand = load_brand()

    if not a.force:
        if ep.get("status") != "approved":
            raise SystemExit(f"Episode {ep['id']} is '{ep.get('status')}', not 'approved'. Not building.")
        if ep.get("sources_status") != "VERIFIED":
            raise SystemExit("sources_status is not VERIFIED. Fact-check first.")
    if a.tts == "files" and not a.audio_dir:
        raise SystemExit("--tts files needs --audio-dir")
    if a.tts == "stub" and a.upload:
        raise SystemExit("Refusing to upload a stub (silent) render.")

    out = Path(a.out) / f"{ep['id']}-{ep['slug']}"
    out.mkdir(parents=True, exist_ok=True)
    pad = float(brand["video"]["pad_after_scene_sec"])

    scenes = synthesize(ep, brand, out / "audio", mode=a.tts, audio_dir=a.audio_dir)
    raw_wav, fx_wav, narration_wav = out / "voice_raw.wav", out / "voice_fx.wav", out / "narration.wav"
    join_narration(scenes, raw_wav, pad)
    apply_voice_effect(raw_wav, fx_wav, brand["voice"].get("effect", "none"))
    starts, acc = [], 0.0
    for _, _, dur in scenes:
        starts.append(acc)
        acc += dur
    mix(fx_wav, narration_wav, starts, ep, brand)          # voice + mechanical sound effects
    export_mp3(narration_wav, out / "narration.mp3")
    total = sum(d for _, _, d in scenes)
    print(f"Narration length: {total:.1f}s")
    if total > 59:
        print("WARNING: longer than ~59s; trim the script (target 25-50s).")

    # Extra exports for editing in Kdenlive (additive): scene timings and an SRT matching the burned-in subtitles
    from studio.subtitles import write_exports
    write_exports(ep, scenes, pad, out)

    mp4 = out / f"{ep['id']}-{ep['slug']}.mp4"
    build(ep, brand, scenes, narration_wav, mp4, pad)
    print("Built", mp4)

    if a.upload:
        from .upload_youtube import upload_private
        vid = upload_private(mp4, ep)
        print("Uploaded PRIVATE video id:", vid)
        ids = done_ids() | {ep["id"]}
        STATE.parent.mkdir(exist_ok=True)
        STATE.write_text(json.dumps(sorted(ids)))
        (out / "upload.json").write_text(json.dumps(
            {"id": ep["id"], "video_id": vid, "at": datetime.now(timezone.utc).isoformat()}))


if __name__ == "__main__":
    main()
