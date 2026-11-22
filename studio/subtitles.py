"""Timeline + SRT export that matches the burned-in subtitles in src/visuals.py.

The burned-in subtitles show 3-word chunks, timed by character weight (len(word)+2) across the
speaking part of each scene. The SRT uses exactly the same rule, so a Kdenlive subtitle track lines up
with the video the pipeline builds.
"""
import json
from pathlib import Path


def timeline(ep, scenes, pad):
    """scenes: [(scene_dict, wav_path, duration_incl_pause)] as returned by src.tts.synthesize."""
    out, t = [], 0.0
    for scene, _wav, dur in scenes:
        pause = float(scene.get("pause_after", pad))
        out.append({"id": scene["id"], "start": round(t, 3), "duration": round(dur, 3),
                    "speaking": round(max(0.0, dur - pause), 3), "text": scene["text"],
                    "on_screen": scene.get("on_screen", ""), "visual": scene.get("visual", {}).get("type", ""),
                    "sfx": [s.get("name") for s in scene.get("sfx", []) or []]})
        t += dur
    return {"episode": ep["id"], "slug": ep["slug"], "total_seconds": round(t, 3), "scenes": out}


def chunk_times(scene_entry, per_chunk=3):
    """[(start_sec, end_sec, text)] for one scene, same weighting as the renderer."""
    words = scene_entry["text"].split()
    if not words:
        return []
    weights = [len(w) + 2 for w in words]
    total = float(sum(weights))
    start0, speaking = scene_entry["start"], scene_entry["speaking"]
    chunks = []
    for i in range(0, len(words), per_chunk):
        before = sum(weights[:i])
        after = sum(weights[:i + per_chunk])
        chunks.append((start0 + speaking * before / total, start0 + speaking * min(after, total) / total,
                       " ".join(words[i:i + per_chunk])))
    return chunks


def _ts(sec):
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def to_srt(tl):
    lines, n = [], 1
    for entry in tl["scenes"]:
        for a, b, text in chunk_times(entry):
            lines += [str(n), f"{_ts(a)} --> {_ts(b)}", text, ""]
            n += 1
    return "\n".join(lines)


def write_exports(ep, scenes, pad, out_dir):
    """Write timeline.json and subtitles.srt next to the episode's narration."""
    out_dir = Path(out_dir)
    tl = timeline(ep, scenes, pad)
    (out_dir / "timeline.json").write_text(json.dumps(tl, indent=2), encoding="utf-8")
    (out_dir / "subtitles.srt").write_text(to_srt(tl), encoding="utf-8")
    return tl
