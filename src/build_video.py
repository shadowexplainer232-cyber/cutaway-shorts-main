"""Render all frames to FFmpeg and produce the final 1080x1920 H.264/AAC MP4."""
import subprocess
from pathlib import Path

from .visuals import make_renderer, W, H


def build(episode, brand, scene_audio, narration_wav, out_mp4, pad):
    """scene_audio: list of (scene, wav, duration_incl_pad)."""
    fps = int(brand["video"]["fps"])
    renderer = make_renderer(brand, episode)

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
        "-i", str(narration_wav),
    ]
    music = brand.get("music", {}).get("file")
    if music:
        mp = Path(__file__).resolve().parent.parent / "assets" / "music" / music
        vol = brand["music"].get("volume", 0.08)
        cmd += ["-stream_loop", "-1", "-i", str(mp),
                "-filter_complex", f"[2:a]volume={vol}[m];[1:a][m]amix=inputs=2:duration=first[a]",
                "-map", "0:v", "-map", "[a]"]
    else:
        cmd += ["-map", "0:v", "-map", "1:a"]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out_mp4)]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for scene, _wav, dur in scene_audio:
            frames = max(1, round(dur * fps))
            speaking = (dur - pad) / dur
            for n in range(frames):
                img = renderer(scene, n / frames, speaking)
                proc.stdin.write(img.tobytes())
    finally:
        proc.stdin.close()
        proc.wait()
    if proc.returncode != 0:
        raise RuntimeError("ffmpeg failed")
