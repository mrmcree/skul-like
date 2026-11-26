"""Re-master the weapon and impact SFX so they sound like steel, not hiss.

Usage (from the project root):
    python tools/master_sfx.py

The CC0 recordings in assets/sfx (see LICENSE-sfx.txt) are mostly airy whooshes with
little low end. Each recipe below keeps the recording and layers synthesized parts on top,
lined up with the recording's loudest moment:
  - blade ring: inharmonic metallic partials with a slight downward glide (the "shing")
  - whump: a short low sine sweep that gives the swing weight
  - crack: a band-passed noise burst (the blade biting in)
  - body: a saturated low sine drop (the impact thud)
then soft-clips and normalizes to a common loudness.

Originals are copied once to assets/raw/sfx_originals/ and always re-mastered from there,
so running this again never stacks layers twice.
"""

from __future__ import annotations

import shutil
import wave
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy import signal

ROOT = Path(__file__).resolve().parent.parent
SFX = ROOT / "assets" / "sfx"
ORIGINALS = ROOT / "assets" / "raw" / "sfx_originals"
RATE = 44100
TARGET_RMS_DB = -14.0     # loudness of the busy part of each sound
PEAK_DB = -1.0


# --- io --------------------------------------------------------------------------

def load(name: str) -> np.ndarray:
    src = ORIGINALS / f"{name}.wav"
    if not src.exists():
        ORIGINALS.mkdir(parents=True, exist_ok=True)
        shutil.copy(SFX / f"{name}.wav", src)
    with wave.open(str(src)) as w:
        if w.getframerate() != RATE or w.getsampwidth() != 2:
            raise ValueError(f"{name}: expected 16-bit {RATE} Hz")
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64)
        if w.getnchannels() > 1:
            data = data.reshape(-1, w.getnchannels()).mean(axis=1)
    return data / 32768.0


def save(name: str, sig: np.ndarray) -> None:
    pcm = (np.clip(sig, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(str(SFX / f"{name}.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())


# --- layers ----------------------------------------------------------------------

def _t(duration: float) -> np.ndarray:
    return np.arange(int(duration * RATE)) / RATE


def blade_ring(duration: float, base_hz: float, glide: float = 0.03) -> np.ndarray:
    """Metallic 'shing': inharmonic partials, higher ones decay faster, pitch glides down."""
    t = _t(duration)
    out = np.zeros_like(t)
    for ratio, gain, decay in [(1.0, 1.0, 0.18), (1.47, 0.7, 0.14), (2.09, 0.5, 0.10),
                               (2.76, 0.35, 0.07), (3.41, 0.25, 0.05)]:
        freq = base_hz * ratio * (1.0 - glide * t / duration)
        phase = 2 * np.pi * np.cumsum(freq) / RATE
        out += gain * np.sin(phase) * np.exp(-t / (decay * duration / 0.3))
    attack = np.clip(t / 0.003, 0, 1)
    return out * attack / np.abs(out).max()


def whump(duration: float, start_hz: float, end_hz: float) -> np.ndarray:
    """Low sweep that gives a swing weight."""
    t = _t(duration)
    freq = start_hz * (end_hz / start_hz) ** (t / duration)
    phase = 2 * np.pi * np.cumsum(freq) / RATE
    env = np.sin(np.pi * np.clip(t / duration, 0, 1)) ** 2
    return np.sin(phase) * env


def crack(duration: float, low_hz: float, high_hz: float, seed: int) -> np.ndarray:
    """Band-passed noise burst: the blade biting in."""
    rng = np.random.default_rng(seed)
    t = _t(duration)
    sos = signal.butter(4, [low_hz, high_hz], btype="band", fs=RATE, output="sos")
    burst = signal.sosfilt(sos, rng.uniform(-1, 1, len(t)))
    env = np.exp(-t / (duration / 5)) * np.clip(t / 0.0008, 0, 1)
    burst *= env
    return burst / np.abs(burst).max()


def body(duration: float, start_hz: float, end_hz: float, drive: float = 2.5) -> np.ndarray:
    """Saturated low sine drop: the thud of an impact."""
    t = _t(duration)
    freq = start_hz * (end_hz / start_hz) ** (t / duration)
    phase = 2 * np.pi * np.cumsum(freq) / RATE
    # Fast decay: a punch, not a drone (long low sines read as humming).
    env = np.exp(-t / (duration / 6.0)) * np.clip(t / 0.002, 0, 1)
    return np.tanh(np.sin(phase) * env * drive) / np.tanh(drive)


# --- mixing ----------------------------------------------------------------------

def peak_index(sig: np.ndarray) -> int:
    """Loudest moment of a recording (smoothed envelope), where layers should land."""
    env = np.convolve(np.abs(sig), np.ones(441) / 441, mode="same")
    return int(env.argmax())


def place(base: np.ndarray, layer: np.ndarray, at: int, gain: float) -> np.ndarray:
    end = at + len(layer)
    out = np.pad(base, (0, max(0, end - len(base))))
    out[at:end] += layer * gain
    return out


def master(sig: np.ndarray) -> np.ndarray:
    """Soft-clip for glue, normalize the busy part to TARGET_RMS_DB, cap the peak, fade out."""
    sig = sig - sig.mean()
    sig = np.tanh(sig * 1.6) / np.tanh(1.6)
    env = np.abs(sig)
    busy = env[env > env.max() * 0.1]
    rms = np.sqrt((busy ** 2).mean()) if len(busy) else 1.0
    sig *= 10 ** (TARGET_RMS_DB / 20) / rms
    peak = np.abs(sig).max()
    if peak > 10 ** (PEAK_DB / 20):
        sig *= 10 ** (PEAK_DB / 20) / peak
    fade = min(len(sig), int(0.02 * RATE))
    sig[-fade:] *= np.linspace(1, 0, fade)
    return sig


@dataclass
class Recipe:
    source: str
    layers: list[tuple[np.ndarray, float, float]] = field(default_factory=list)
    # (layer, gain, offset in seconds from the recording's peak; negative = before)

    def render(self) -> np.ndarray:
        base = load(self.source)
        peak = peak_index(base)
        out = base.copy()
        for layer, gain, offset in self.layers:
            out = place(out, layer, max(0, peak + int(offset * RATE)), gain)
        return master(out)


def recipes() -> dict[str, Recipe]:
    # Every added layer is a short burst (≤ ~0.15 s, fast decay). Longer tonal layers
    # (ring tails, low sine thuds, rumble) read as humming/droning — keep them out.
    return {
        # Light horizontal cut: a quick, quiet glint of steel and a touch of weight.
        "katana_slash_1": Recipe("katana_slash_1", [
            (blade_ring(0.15, 3200), 0.12, -0.01), (whump(0.07, 150, 80), 0.30, -0.03)]),
        # Rising cut: brighter glint.
        "katana_slash_2": Recipe("katana_slash_2", [
            (blade_ring(0.15, 3700, glide=0.015), 0.12, -0.01), (whump(0.07, 170, 90), 0.30, -0.03)]),
        # Heavy thrust: slightly longer, lower glint and more weight.
        "katana_thrust": Recipe("katana_thrust", [
            (blade_ring(0.20, 2700), 0.14, -0.02), (whump(0.09, 130, 65), 0.45, -0.04)]),
        # Blade hits: the crack carries the cut; a short punch underneath; barely any ring.
        "hit_light": Recipe("hit_light", [
            (crack(0.045, 1800, 5200, 1), 0.60, -0.005), (body(0.07, 170, 70, drive=1.6), 0.55, 0.0),
            (blade_ring(0.08, 4000), 0.08, 0.0)]),
        "hit_heavy": Recipe("hit_heavy", [
            (crack(0.06, 1300, 4800, 2), 0.75, -0.005), (body(0.10, 140, 55, drive=1.8), 0.70, 0.0),
            (blade_ring(0.10, 3000), 0.08, 0.0)]),
        # The spear hitting the player: crack + short punch, no ring.
        "spear_hit": Recipe("spear_hit", [
            (crack(0.05, 1400, 4200, 4), 0.55, -0.005), (body(0.08, 150, 60, drive=1.6), 0.55, 0.0)]),
    }


def describe(sig: np.ndarray) -> str:
    spec = np.abs(np.fft.rfft(sig))
    freqs = np.fft.rfftfreq(len(sig), 1 / RATE)
    low = spec[freqs < 300].sum() / spec.sum()
    high = spec[freqs > 4000].sum() / spec.sum()
    return f"{len(sig) / RATE:.2f}s low<300Hz={low:.2f} high>4kHz={high:.2f}"


def main() -> None:
    for name, recipe in recipes().items():
        out = recipe.render()
        save(name, out)
        print(f"{name:16s} {describe(out)}")
    # swing_light / swing_heavy are aliases of the slash sounds (see LICENSE-sfx.txt).
    shutil.copy(SFX / "katana_slash_1.wav", SFX / "swing_light.wav")
    shutil.copy(SFX / "katana_thrust.wav", SFX / "swing_heavy.wav")


if __name__ == "__main__":
    main()
