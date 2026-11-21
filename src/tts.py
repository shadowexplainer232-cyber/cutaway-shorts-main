"""Narration: one WAV per scene (Piper), then joined into narration.wav / narration.mp3.

--tts stub writes silent audio of a plausible length so the video pipeline can be tested
without a voice engine. Never publish a stub render.
"""
import subprocess
import sys
import wave
from pathlib import Path

from .common import ROOT


def _wav_seconds(path):
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / w.getframerate()


def _ensure_voice(voice_name, data_dir):
    onnx = data_dir / f"{voice_name}.onnx"
    if onnx.exists():
        return
    data_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [sys.executable, "-m", "piper.download_voices", voice_name, "--data-dir", str(data_dir)],
        check=True,
    )


def _piper(text, out_wav, voice_name, data_dir, length_scale):
    cmd = [
        sys.executable, "-m", "piper",
        "-m", voice_name,
        "--data-dir", str(data_dir),
        "--length-scale", str(length_scale),
        "-f", str(out_wav),
        "--", text,
    ]
    subprocess.run(cmd, check=True)


def _stub(text, out_wav, length_scale=1.0):
    # Piper ryan-high speaks roughly 3.2 words/second at length_scale 1.0 (measured from a real run)
    seconds = max(1.5, len(text.split()) / (3.2 / length_scale))
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
         "-i", "anullsrc=r=22050:cl=mono", "-t", f"{seconds:.2f}", "-c:a", "pcm_s16le", str(out_wav)],
        check=True,
    )


def _from_file(scene, index, audio_dir, out_wav):
    """Use a recorded/generated clip for this scene: <NN>*.ext or <scene id>*.ext (mp3, wav, m4a, ogg, aac)."""
    audio_dir = Path(audio_dir)
    exts = {".mp3", ".wav", ".m4a", ".ogg", ".aac", ".flac"}
    for f in sorted(audio_dir.iterdir()):
        stem = f.stem.lower()
        if f.suffix.lower() in exts and (stem.startswith(f"{index + 1:02d}") or stem.startswith(scene["id"].lower())):
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(f), "-ac", "1", "-ar", "22050",
                            "-c:a", "pcm_s16le", str(out_wav)], check=True)
            return
    raise SystemExit(f"No audio clip for scene {index + 1} ('{scene['id']}') in {audio_dir}. "
                     f"Name it {index + 1:02d}.mp3 (or .wav/.m4a) or {scene['id']}.mp3")


def synthesize(episode, brand, workdir, mode="piper", audio_dir=None):
    """Returns list of (scene, wav_path, duration_seconds_including_pad)."""
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    voice = brand["voice"]
    data_dir = ROOT / voice.get("data_dir", "voices")
    if mode == "piper":
        _ensure_voice(voice["name"], data_dir)

    pad = float(brand["video"]["pad_after_scene_sec"])
    length_scale = float(episode.get("length_scale", voice.get("length_scale", 1.0)))
    results = []
    for i, scene in enumerate(episode["scenes"]):
        wav = workdir / f"scene_{i:02d}_{scene['id']}.wav"
        if mode == "piper":
            _piper(scene["text"], wav, voice["name"], data_dir, length_scale)
        elif mode == "files":
            _from_file(scene, i, audio_dir, wav)
        else:
            _stub(scene["text"], wav, length_scale)
        results.append((scene, wav, _wav_seconds(wav) + float(scene.get("pause_after", pad))))
    return results


def join_narration(results, out_wav, pad):
    """Concatenate scene WAVs; each scene is followed by silence so its slot equals its duration
    (the scene's own `pause_after` if set, otherwise the default pad)."""
    params = None
    chunks = []
    for _, wav, _dur in results:
        with wave.open(str(wav), "rb") as w:
            if params is None:
                params = w.getparams()
            chunks.append(w.readframes(w.getnframes()))
    frame_bytes = params.sampwidth * params.nchannels
    with wave.open(str(out_wav), "wb") as out:
        out.setparams(params)
        for (_, _, dur), c in zip(results, chunks):
            silent_frames = max(0, round(dur * params.framerate) - len(c) // frame_bytes)
            out.writeframes(c + b"\x00" * (silent_frames * frame_bytes))
