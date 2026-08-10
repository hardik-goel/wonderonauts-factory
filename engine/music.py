"""
Procedural music + sound effects, synthesized from math with numpy.

Nothing here is sampled, downloaded or derived from existing recordings: every
waveform is generated from oscillators and noise, so the audio is copyright
clean by construction and free forever.

Public API used by factory.py:

    render_bgm(path, duration, seed=7)  -> cheerful bed, exactly `duration` long
    render_sfx(name, path)              -> whoosh | pop | sparkle | success
    render_sting(path)                  -> the 2.5s channel audio logo

Everything is deterministic: same seed + same duration = bit-identical WAV.

CLI:
    python3 -m engine.music --demo out/    # 10s samples + peak levels
"""

from __future__ import annotations

import math
import os
import wave

import numpy as np

SR = 44100
PEAK = 0.72          # target peak level for every rendered asset
BPM = 112.0
BEAT = 60.0 / BPM
BAR = BEAT * 4

# I - V - vi - IV in C major, as semitone offsets from C
PROGRESSION = [
    (0, [0, 4, 7]),     # C
    (7, [7, 11, 14]),   # G
    (9, [9, 12, 16]),   # Am
    (5, [5, 9, 12]),    # F
]

# C major pentatonic, two octaves up from C4
PENTATONIC = [0, 2, 4, 7, 9, 12, 14, 16, 19, 21]


# --------------------------------------------------------------------------
# Primitives
# --------------------------------------------------------------------------

def hz(semitones_from_c4: float) -> float:
    """C4 = 261.63 Hz."""
    return 261.6255653 * (2.0 ** (semitones_from_c4 / 12.0))


def _t(n: int) -> np.ndarray:
    return np.arange(n, dtype=np.float64) / SR


def env_adsr(n: int, a=0.01, d=0.12, s=0.6, r=0.25) -> np.ndarray:
    """Attack/decay/sustain/release envelope of exactly n samples."""
    a_n = max(1, int(a * SR))
    d_n = max(1, int(d * SR))
    r_n = max(1, int(r * SR))
    s_n = max(0, n - a_n - d_n - r_n)
    parts = [
        np.linspace(0.0, 1.0, a_n),
        np.linspace(1.0, s, d_n),
        np.full(s_n, s),
        np.linspace(s, 0.0, r_n),
    ]
    out = np.concatenate(parts)
    return out[:n] if len(out) >= n else np.pad(out, (0, n - len(out)))


def env_perc(n: int, decay: float = 6.0) -> np.ndarray:
    """Plucked/percussive exponential decay."""
    return np.exp(-decay * _t(n))


def bell(freq: float, dur: float, amp: float = 0.5, decay: float = 3.2,
         detune: float = 0.0) -> np.ndarray:
    """Soft marimba/bell tone: sine + gentle 2nd/3rd partials."""
    n = int(dur * SR)
    t = _t(n)
    f = freq * (1.0 + detune)
    w = (np.sin(2 * np.pi * f * t)
         + 0.34 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-5.0 * t)
         + 0.14 * np.sin(2 * np.pi * f * 3.01 * t) * np.exp(-8.0 * t))
    # a touch of vibrato keeps it from sounding sterile
    w += 0.06 * np.sin(2 * np.pi * f * t + 3.0 * np.sin(2 * np.pi * 5.2 * t))
    return amp * w * env_perc(n, decay)


def pad(freqs, dur: float, amp: float = 0.16) -> np.ndarray:
    """Warm sustained chord bed."""
    n = int(dur * SR)
    t = _t(n)
    w = np.zeros(n)
    for i, f in enumerate(freqs):
        w += np.sin(2 * np.pi * f * t + i * 0.7)
        w += 0.18 * np.sin(2 * np.pi * f * 0.5 * t)   # sub for body
    w /= max(1, len(freqs))
    return amp * w * env_adsr(n, a=0.35, d=0.4, s=0.85, r=0.55)


def bass(freq: float, dur: float, amp: float = 0.35) -> np.ndarray:
    """Round sine bass with a soft click on the attack."""
    n = int(dur * SR)
    t = _t(n)
    w = np.sin(2 * np.pi * freq * t) + 0.22 * np.sin(2 * np.pi * freq * 2 * t)
    return amp * w * env_perc(n, decay=3.4)


def noise(n: int, rng: np.random.Generator) -> np.ndarray:
    return rng.uniform(-1.0, 1.0, n)


def lowpass(x: np.ndarray, cutoff) -> np.ndarray:
    """One-pole lowpass; cutoff may be a scalar or a per-sample array (Hz)."""
    c = np.asarray(cutoff, dtype=np.float64)
    if c.ndim == 0:
        c = np.full(len(x), float(c))
    alpha = 1.0 - np.exp(-2.0 * np.pi * np.clip(c, 20.0, SR / 2.2) / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += alpha[i] * (x[i] - acc)
        y[i] = acc
    return y


def mix_at(buf: np.ndarray, part: np.ndarray, start: float, gain: float = 1.0):
    """Add `part` into `buf` at time `start` (seconds), clipped to the buffer."""
    i = int(start * SR)
    if i >= len(buf) or i + len(part) <= 0:
        return
    j = min(len(buf), i + len(part))
    buf[max(0, i):j] += part[max(0, -i):j - i] * gain


def normalize(x: np.ndarray, peak: float = PEAK) -> np.ndarray:
    m = float(np.max(np.abs(x))) if len(x) else 0.0
    return x * (peak / m) if m > 1e-9 else x


def fade(x: np.ndarray, fade_in: float = 0.0, fade_out: float = 0.0) -> np.ndarray:
    y = x.copy()
    n_in, n_out = int(fade_in * SR), int(fade_out * SR)
    if n_in > 0:
        y[:n_in] *= np.linspace(0.0, 1.0, min(n_in, len(y)))[:len(y)]
    if n_out > 0 and n_out < len(y):
        y[-n_out:] *= np.linspace(1.0, 0.0, n_out)
    return y


def write_wav(path: str, x: np.ndarray, stereo: bool = True) -> str:
    """16-bit PCM WAV at 44.1 kHz."""
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
    x = np.clip(x, -1.0, 1.0)
    pcm = (x * 32767.0).astype("<i2")
    if stereo:
        pcm = np.repeat(pcm[:, None], 2, axis=1).reshape(-1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2 if stereo else 1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return path


# --------------------------------------------------------------------------
# Background music
# --------------------------------------------------------------------------

def render_bgm(path: str, duration: float, seed: int = 7, peak: float = PEAK) -> str:
    """Cheerful pentatonic bed over I-V-vi-IV, exactly `duration` seconds.

    `seed` gives each episode its own melody while staying reproducible.
    """
    duration = max(2.0, float(duration))
    n = int(duration * SR)
    buf = np.zeros(n + int(2 * SR))
    rng = np.random.default_rng(seed)

    n_bars = int(math.ceil(duration / BAR)) + 1
    step = 0                      # index into PENTATONIC, random-walked
    # one shaker hit, reused every off-beat (the filter is the expensive part)
    sh_n = int(0.06 * SR)
    shaker = lowpass(noise(sh_n, rng), 9000.0) * env_perc(sh_n, 60.0) * 0.10
    for b in range(n_bars):
        t0 = b * BAR
        root, chord = PROGRESSION[b % len(PROGRESSION)]

        # pad chord for the whole bar (one octave up)
        mix_at(buf, pad([hz(s) for s in chord], BAR * 0.98, amp=0.15), t0)

        # bass on beats 1 and 3, plus a walking note on the 'and' of 4
        mix_at(buf, bass(hz(root - 24), BEAT * 1.6, amp=0.34), t0)
        mix_at(buf, bass(hz(root - 24), BEAT * 1.2, amp=0.24), t0 + BEAT * 2)
        if b % 4 == 3:
            mix_at(buf, bass(hz(root - 22), BEAT * 0.5, amp=0.20), t0 + BEAT * 3.5)

        # melody: eighth notes, chord tone on every downbeat, random walk between
        for k in range(8):
            if rng.random() < (0.10 if k % 2 else 0.02):
                continue                                  # breathing space
            if k % 4 == 0:
                # land on a chord tone, preferring one near where the line is
                cand = [i for i, s in enumerate(PENTATONIC)
                        if (s - root) % 12 in (0, 4, 7, 9)] or [0]
                near = sorted(cand, key=lambda i: abs(i - step))[:3]
                step = int(near[rng.integers(0, len(near))])
                note = PENTATONIC[step]
            else:
                step = int(np.clip(step + rng.integers(-2, 3), 0, len(PENTATONIC) - 1))
                note = PENTATONIC[step]
            dur = BEAT * (0.9 if k % 2 == 0 else 0.55)
            amp = 0.30 if k % 2 == 0 else 0.20
            mix_at(buf, bell(hz(note + 12), dur, amp=amp, decay=4.2), t0 + k * BEAT / 2)

        # shaker on the off-beats keeps the pulse without a drum kit
        for k in range(4):
            mix_at(buf, shaker, t0 + k * BEAT + BEAT * 0.5,
                   gain=1.0 if k % 2 else 0.72)

    out = normalize(buf[:n], peak)
    out = fade(out, fade_in=0.6, fade_out=0.0)
    return write_wav(path, out)


# --------------------------------------------------------------------------
# Sound effects
# --------------------------------------------------------------------------

def _sfx_whoosh(rng) -> np.ndarray:
    n = int(0.55 * SR)
    t = _t(n)
    sweep = 400 + 5200 * np.sin(np.pi * np.clip(t / 0.55, 0, 1)) ** 1.5
    w = lowpass(noise(n, rng), sweep)
    env = np.sin(np.pi * np.clip(t / 0.55, 0, 1)) ** 1.4
    return w * env


def _sfx_pop(rng) -> np.ndarray:
    n = int(0.22 * SR)
    t = _t(n)
    f = 880 * np.exp(-9.0 * t) + 190
    ph = 2 * np.pi * np.cumsum(f) / SR
    w = np.sin(ph) * env_perc(n, 22.0)
    w += 0.25 * lowpass(noise(n, rng), 2600.0) * env_perc(n, 70.0)
    return w


def _sfx_sparkle(rng) -> np.ndarray:
    n = int(1.0 * SR)
    out = np.zeros(n)
    notes = [12, 16, 19, 24, 26, 28, 31]
    for i, s in enumerate(notes):
        mix_at(out, bell(hz(s + 12), 0.5, amp=0.55 - i * 0.045, decay=9.0),
               i * 0.062)
    shimmer = lowpass(noise(int(0.5 * SR), rng), 11000.0) * env_perc(int(0.5 * SR), 9.0)
    mix_at(out, shimmer * 0.12, 0.02)
    return out


def _sfx_success(rng) -> np.ndarray:
    n = int(1.2 * SR)
    out = np.zeros(n)
    for i, s in enumerate([0, 4, 7, 12]):
        mix_at(out, bell(hz(s + 12), 0.85, amp=0.6, decay=4.0), i * 0.115)
    mix_at(out, pad([hz(0), hz(4), hz(7)], 0.9, amp=0.20), 0.30)
    return out


SFX = {
    "whoosh": _sfx_whoosh,
    "pop": _sfx_pop,
    "sparkle": _sfx_sparkle,
    "success": _sfx_success,
}


def render_sfx(name: str, path: str, seed: int = 1, peak: float = PEAK) -> str:
    """Render one of: whoosh, pop, sparkle, success."""
    fn = SFX.get(name)
    if fn is None:
        raise ValueError(f"unknown sfx {name!r}; have {sorted(SFX)}")
    rng = np.random.default_rng(seed)
    x = normalize(fn(rng), peak)
    return write_wav(path, fade(x, 0.004, 0.05))


# --------------------------------------------------------------------------
# Channel sting (audio logo) -- identical in every episode, on purpose
# --------------------------------------------------------------------------

def render_sting(path: str, peak: float = PEAK) -> str:
    """~2.5s four-note rising motif: the Wonder-o-nauts audio logo."""
    n = int(2.5 * SR)
    out = np.zeros(n)
    for i, s in enumerate([0, 4, 7, 12]):         # C E G C -- rising, hopeful
        mix_at(out, bell(hz(s + 12), 1.1, amp=0.62, decay=3.0), i * 0.26)
    mix_at(out, bell(hz(19 + 12), 1.6, amp=0.5, decay=2.2), 1.04)   # G on top
    mix_at(out, pad([hz(0), hz(4), hz(7), hz(12)], 1.9, amp=0.22), 0.42)
    mix_at(out, bass(hz(-24), 1.4, amp=0.30), 0.0)
    x = normalize(out, peak)
    return write_wav(path, fade(x, 0.005, 0.35))


# --------------------------------------------------------------------------
# CLI demo
# --------------------------------------------------------------------------

def _demo(out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    made = [render_bgm(os.path.join(out_dir, "bgm_demo.wav"), 10.0, seed=7),
            render_sting(os.path.join(out_dir, "sting.wav"))]
    made += [render_sfx(k, os.path.join(out_dir, f"sfx_{k}.wav")) for k in SFX]
    for p in made:
        with wave.open(p, "rb") as w:
            frames = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")
            pk = float(np.max(np.abs(frames))) / 32767.0
            secs = w.getnframes() / w.getframerate()
        print(f"  {os.path.basename(p):<18} {secs:5.2f}s  peak {pk:.3f}")


if __name__ == "__main__":
    import sys

    args = sys.argv[1:]
    target = args[args.index("--demo") + 1] if "--demo" in args and len(args) > 1 else "."
    _demo(target)
