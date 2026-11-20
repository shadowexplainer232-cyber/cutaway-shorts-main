"""Procedural mechanical sound effects (numpy only, no downloads, no licensing issues)
plus an optional robot-voice filter and the final mix.
"""
import shutil
import subprocess
import wave

import numpy as np

_RNG = np.random.default_rng(7)


def _t(sr, dur):
    return np.arange(int(sr * dur)) / sr


def _norm(x, peak=0.8):
    m = float(np.max(np.abs(x))) or 1.0
    return x / m * peak


def _lp(x, k):
    return np.convolve(x, np.ones(k) / k, mode="same")


# ----------------------------------------------------------------- effects
def valve_click(sr):
    t = _t(sr, 0.12)
    n = _RNG.standard_normal(t.size)
    return _norm(0.6 * n * np.exp(-t * 220) + np.sin(2 * np.pi * 1900 * t) * np.exp(-t * 150))


def whoosh(sr, dur=0.8, box=10):
    t = _t(sr, dur)
    u = t / dur
    return _norm(_lp(_RNG.standard_normal(t.size), box) * np.sin(np.pi * u) ** 2)


def intake_whoosh(sr):
    return whoosh(sr, 0.9, 8)


def compress(sr):
    t = _t(sr, 0.9)
    u = t / 0.9
    f = 110 + 210 * u
    ph = 2 * np.pi * np.cumsum(f) / sr
    tone = np.sin(ph) + 0.5 * np.sin(2 * ph)
    return _norm(tone * (u ** 1.5) * (1 - 0.9 * u ** 8))


def spark_zap(sr):
    t = _t(sr, 0.2)
    n = np.diff(_RNG.standard_normal(t.size + 1))  # crude high-pass
    return _norm(n * np.exp(-t * 60) + 0.7 * np.sin(2 * np.pi * 3200 * t) * np.exp(-t * 90))


def thump(sr):
    t = _t(sr, 0.5)
    f = 38 + 92 * np.exp(-t * 12)
    ph = 2 * np.pi * np.cumsum(f) / sr
    body = np.sin(ph) * np.exp(-t * 7)
    grit = _lp(_RNG.standard_normal(t.size), 6) * np.exp(-t * 18) * 0.3
    return _norm(body + grit, 0.95)


def exhaust_puff(sr):
    t = _t(sr, 0.7)
    u = t / 0.7
    env = np.minimum(u * 12, 1) * (1 - u) ** 1.5
    return _norm(_lp(_RNG.standard_normal(t.size), 16) * env)


def ding(sr):
    t = _t(sr, 1.4)
    x = sum(a * np.sin(2 * np.pi * f * t) for f, a in ((880, 1.0), (1320, 0.5), (1760, 0.25)))
    return _norm(x * np.exp(-t * 3.5))


LIB = {
    "valve_click": valve_click, "whoosh": whoosh, "intake_whoosh": intake_whoosh,
    "compress": compress, "spark_zap": spark_zap, "thump": thump,
    "exhaust_puff": exhaust_puff, "ding": ding,
}


def hum_bed(sr, dur):
    """Quiet low engine idle under the whole video."""
    t = _t(sr, dur)
    x = np.sin(2 * np.pi * 48 * t) * (0.6 + 0.4 * np.sin(2 * np.pi * 12 * t)) + 0.3 * np.sin(2 * np.pi * 96 * t)
    fade = np.minimum(1, np.minimum(t / 0.6, (dur - t) / 0.6))
    return _norm(x) * np.clip(fade, 0, 1)


# ----------------------------------------------------------------- voice effect
ROBOT = "afftfilt=real='hypot(re,im)*sin(0)':imag='hypot(re,im)*cos(0)':win_size=512:overlap=0.75"


def apply_voice_effect(in_wav, out_wav, effect):
    if effect in (None, "", "none"):
        shutil.copyfile(in_wav, out_wav)
        return
    if effect != "robot":
        raise SystemExit(f"Unknown voice.effect '{effect}' (use none or robot)")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(in_wav), "-af", ROBOT,
                    "-c:a", "pcm_s16le", str(out_wav)], check=True)


# ----------------------------------------------------------------- mix
def mix(voice_wav, out_wav, scene_starts, episode, brand):
    """scene_starts: list of start seconds, one per scene, in order."""
    with wave.open(str(voice_wav), "rb") as w:
        sr, ch, width = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    if width != 2 or ch != 1:
        raise SystemExit("Expected 16-bit mono narration")
    voice = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0
    out = voice.copy()

    cfg = brand.get("sfx", {})
    if cfg.get("enabled", True):
        vol = float(cfg.get("volume", 0.5))
        out += float(cfg.get("hum_volume", 0.06)) * hum_bed(sr, out.size / sr)
        for scene, start in zip(episode["scenes"], scene_starts):
            for ev in scene.get("sfx", []):
                fx = LIB[ev["name"]](sr) * vol * float(ev.get("gain", 1.0))
                s = int((start + float(ev.get("at", 0.0))) * sr)
                e = min(out.size, s + fx.size)
                if s < out.size:
                    out[s:e] += fx[: e - s]
    peak = float(np.max(np.abs(out))) or 1.0
    if peak > 0.95:
        out = out / peak * 0.95
    with wave.open(str(out_wav), "wb") as o:
        o.setnchannels(1)
        o.setsampwidth(2)
        o.setframerate(sr)
        o.writeframes((out * 32767).astype(np.int16).tobytes())


def export_mp3(wav, mp3):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav),
                    "-codec:a", "libmp3lame", "-qscale:a", "2", str(mp3)], check=True)
