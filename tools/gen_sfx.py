"""Synthesize the game's placeholder sound effects as 16-bit mono WAV files.

Usage (from the project root):
    python tools/gen_sfx.py

Writes to assets/sfx/. Uses only the Python standard library, so the sounds are
reproducible: tweak a recipe below and re-run to regenerate.
"""

from __future__ import annotations

import math
import random
import struct
import wave
from pathlib import Path
from typing import Callable

RATE = 44100
OUT_DIR = Path(__file__).resolve().parent.parent / "assets" / "sfx"

Signal = list[float]


# --- building blocks ----------------------------------------------------------

def samples(duration: float) -> range:
    return range(int(duration * RATE))


def noise(duration: float, seed: int) -> Signal:
    rng = random.Random(seed)
    return [rng.uniform(-1.0, 1.0) for _ in samples(duration)]


def envelope(sig: Signal, attack: float, decay_power: float) -> Signal:
    """Linear attack, then (1 - t)^decay_power fall-off to the end."""
    n = len(sig)
    attack_n = max(1, int(attack * RATE))
    out = []
    for i, s in enumerate(sig):
        if i < attack_n:
            gain = i / attack_n
        else:
            gain = (1.0 - (i - attack_n) / max(1, n - attack_n)) ** decay_power
        out.append(s * gain)
    return out


def lowpass_sweep(sig: Signal, start_hz: float, end_hz: float) -> Signal:
    """One-pole low-pass whose cutoff glides from start_hz to end_hz."""
    out, y, n = [], 0.0, len(sig)
    for i, s in enumerate(sig):
        cutoff = start_hz + (end_hz - start_hz) * i / max(1, n - 1)
        alpha = 1.0 - math.exp(-2.0 * math.pi * cutoff / RATE)
        y += alpha * (s - y)
        out.append(y)
    return out


def highpass(sig: Signal, hz: float) -> Signal:
    low = lowpass_sweep(sig, hz, hz)
    return [s - l for s, l in zip(sig, low)]


def sine_sweep(duration: float, start_hz: float, end_hz: float, curve: float = 2.0) -> Signal:
    """Sine whose pitch falls/rises from start_hz to end_hz (exponential-ish)."""
    out, phase, n = [], 0.0, int(duration * RATE)
    for i in range(n):
        t = (i / max(1, n - 1)) ** (1.0 / curve)
        hz = start_hz + (end_hz - start_hz) * t
        phase += 2.0 * math.pi * hz / RATE
        out.append(math.sin(phase))
    return out


def ring(duration: float, partials: list[tuple[float, float]], decay: float) -> Signal:
    """Metallic ring: inharmonic sine partials (hz, gain) with exponential decay."""
    return [
        sum(g * math.sin(2 * math.pi * hz * i / RATE) for hz, g in partials)
        * math.exp(-i / RATE / decay)
        for i in samples(duration)
    ]


def mix(*layers: tuple[Signal, float]) -> Signal:
    length = max(len(sig) for sig, _ in layers)
    out = [0.0] * length
    for sig, gain in layers:
        for i, s in enumerate(sig):
            out[i] += s * gain
    return out


def saturate(sig: Signal, drive: float) -> Signal:
    return [math.tanh(s * drive) for s in sig]


def normalize(sig: Signal, peak: float = 0.85) -> Signal:
    top = max(abs(s) for s in sig) or 1.0
    return [s / top * peak for s in sig]


# --- recipes ------------------------------------------------------------------

def swing(duration: float, start_hz: float, end_hz: float, seed: int) -> Signal:
    whoosh = lowpass_sweep(highpass(noise(duration, seed), 400), start_hz, end_hz)
    return envelope(whoosh, attack=0.025, decay_power=2.0)


def swing_light() -> Signal:
    blade = ring(0.25, [(2350, 0.5), (3720, 0.3), (5480, 0.2)], decay=0.05)
    return mix((swing(0.16, 5200, 1400, 1), 1.0), (blade, 0.12))


def swing_heavy() -> Signal:
    blade = ring(0.35, [(1650, 0.5), (2890, 0.3), (4410, 0.2)], decay=0.08)
    return mix((swing(0.26, 3800, 700, 2), 1.0), (blade, 0.15))


def hit(duration: float, thump_from: float, thump_to: float, crunch: float, seed: int) -> Signal:
    thump = envelope(sine_sweep(duration, thump_from, thump_to), 0.002, 2.5)
    crack = envelope(lowpass_sweep(noise(duration * 0.5, seed), 7000, 1200), 0.001, 3.0)
    slice_ = envelope(highpass(noise(0.03, seed + 1), 3000), 0.0005, 1.5)
    return saturate(mix((thump, 1.0), (crack, crunch), (slice_, 0.5)), 2.2)


def hit_light() -> Signal:
    return hit(0.12, 220, 70, 0.7, 3)


def hit_heavy() -> Signal:
    body = hit(0.30, 160, 38, 1.0, 4)
    tail = envelope(lowpass_sweep(noise(0.30, 5), 1800, 200), 0.005, 1.5)
    return mix((body, 1.0), (tail, 0.35))


def jump() -> Signal:
    return envelope(mix((sine_sweep(0.10, 260, 620, 1.0), 0.8),
                        (swing(0.10, 3000, 6000, 6), 0.25)), 0.004, 2.0)


def land() -> Signal:
    thud = envelope(sine_sweep(0.08, 140, 55), 0.002, 2.0)
    scuff = envelope(lowpass_sweep(noise(0.07, 7), 2500, 400), 0.002, 2.0)
    return mix((thud, 0.9), (scuff, 0.5))


def dash() -> Signal:
    return swing(0.14, 6500, 2200, 8)


def dummy_break() -> Signal:
    crunch = envelope(lowpass_sweep(noise(0.35, 9), 4000, 300), 0.002, 1.2)
    drop = envelope(sine_sweep(0.35, 300, 60, 1.5), 0.002, 1.5)
    return saturate(mix((crunch, 0.8), (drop, 0.6)), 1.8)


RECIPES: dict[str, Callable[[], Signal]] = {
    "swing_light": swing_light,
    "swing_heavy": swing_heavy,
    "hit_light": hit_light,
    "hit_heavy": hit_heavy,
    "jump": jump,
    "land": land,
    "dash": dash,
    "break": dummy_break,
}


def write_wav(path: Path, sig: Signal) -> None:
    frames = b"".join(struct.pack("<h", int(max(-1.0, min(1.0, s)) * 32767)) for s in sig)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        wav.writeframes(frames)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, recipe in RECIPES.items():
        sig = normalize(recipe())
        write_wav(OUT_DIR / f"{name}.wav", sig)
        print(f"wrote {name}.wav ({len(sig) / RATE:.2f}s)")


if __name__ == "__main__":
    main()
