"""Procedural sound synthesis (WAV 22050 Hz, mono). Custom sounds: sounds/<name>.wav in assets or in a mod."""
from __future__ import annotations

import math
import random
import struct
import wave
from pathlib import Path

RATE = 22050


def _write(path: Path, samples: list[float]) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1.0, min(1.0, s)) * 30000)) for s in samples))


def _noise_burst(dur, decay, low=0.0, seed=1):
    r, out, lp = random.Random(seed), [], 0.0
    for i in range(int(dur * RATE)):
        t = i / RATE
        lp = lp * low + (r.random() * 2 - 1) * (1 - low)
        out.append(lp * math.exp(-t * decay) + 0.5 * math.sin(2 * math.pi * 70 * t) * math.exp(-t * decay * 0.7))
    return out


def _growl(freq, dur, wobble=20.0, drop=0.4, seed=1):
    r, out, ph = random.Random(seed), [], 0.0
    for i in range(int(dur * RATE)):
        t = i / RATE
        f = freq * (1 - drop * t / dur) * (1 + 0.15 * math.sin(2 * math.pi * wobble * t))
        ph += f / RATE
        saw = 2 * (ph % 1.0) - 1
        out.append((0.6 * saw + 0.25 * (r.random() * 2 - 1)) * min(1.0, t * 40) * (1 - t / dur) ** 0.7)
    return out


def _sweep(f0, f1, dur, vol=0.7):
    out, ph = [], 0.0
    for i in range(int(dur * RATE)):
        t = i / dur / RATE
        ph += (f0 + (f1 - f0) * t) / RATE
        out.append(vol * math.sin(2 * math.pi * ph) * (1 - t))
    return out


def _beeps(freqs, each=0.07):
    out = []
    for f in freqs:
        out += [0.5 * math.sin(2 * math.pi * f * i / RATE) * (1 - i / (each * RATE)) for i in range(int(each * RATE))]
    return out


SOUNDS = {
    "pistol": lambda: _noise_burst(0.22, 18, 0.4, 1),
    "shotgun": lambda: _noise_burst(0.5, 9, 0.6, 2),
    "punch": lambda: _noise_burst(0.12, 30, 0.9, 3),
    "claw": lambda: _noise_burst(0.15, 25, 0.5, 4),
    "plasma": lambda: _sweep(1800, 300, 0.18),
    "fireball": lambda: _sweep(300, 900, 0.3, 0.5),
    "explosion": lambda: _noise_burst(0.5, 7, 0.85, 5),
    "door_open": lambda: _growl(60, 0.7, 6, 0.2, 6),
    "door_close": lambda: _growl(70, 0.6, 6, 0.3, 7),
    "lift_move": lambda: _growl(45, 0.9, 4, 0.0, 8),
    "pickup": lambda: _beeps([880, 1320], 0.06),
    "weapon_pickup": lambda: _beeps([523, 659, 784, 1046], 0.07),
    "secret": lambda: _beeps([660, 880, 1100], 0.09),
    "noway": lambda: _growl(110, 0.2, 10, 0.3, 9),
    "zombie_sight": lambda: _growl(130, 0.5, 14, 0.2, 10),
    "zombie_pain": lambda: _growl(160, 0.25, 25, 0.3, 11),
    "zombie_death": lambda: _growl(150, 0.7, 12, 0.7, 12),
    "imp_sight": lambda: _growl(220, 0.6, 18, 0.5, 13),
    "imp_pain": lambda: _growl(260, 0.3, 30, 0.4, 14),
    "imp_death": lambda: _growl(240, 0.9, 16, 0.8, 15),
    "player_pain": lambda: _growl(180, 0.25, 20, 0.5, 16),
    "player_death": lambda: _growl(200, 0.9, 10, 0.9, 17),
}


def ensure_sounds(cache_dir: Path) -> Path:
    """Creates the missing WAV files in cache_dir (on first launch, ~1-2 s)."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    for name, gen in SOUNDS.items():
        p = cache_dir / f"{name}.wav"
        if not p.exists():
            _write(p, gen())
    return cache_dir
