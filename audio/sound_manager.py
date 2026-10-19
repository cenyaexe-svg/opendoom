"""Sound playback via Panda3D: stereo panning and distance attenuation, as in Doom."""
from __future__ import annotations

import logging
import math

log = logging.getLogger("opendoom")
MAX_HEAR_DIST = 1200.0


class SoundManager:
    def __init__(self, loader, resources, cache_dir, listener):
        from audio.synth import ensure_sounds
        self._loader, self._res, self._listener = loader, resources, listener   # listener: an object with x, y, angle
        self._cache_dir = ensure_sounds(cache_dir)
        self._sfx: dict[str, object] = {}

    def _get(self, name: str):
        if name not in self._sfx:
            path = self._res.find("sounds", f"{name}.wav") or (self._cache_dir / f"{name}.wav")
            self._sfx[name] = self._loader.loadSfx(str(path)) if path.exists() else None
            if self._sfx[name] is None:
                log.warning("Missing sound '%s'", name)
        return self._sfx[name]

    def play(self, name: str, x: float | None = None, y: float | None = None) -> None:
        sfx = self._get(name)
        if sfx is None:
            return
        volume, pan = 1.0, 0.0
        if x is not None:
            dx, dy = x - self._listener.x, y - self._listener.y
            dist = math.hypot(dx, dy)
            if dist > MAX_HEAR_DIST:
                return
            volume = max(0.0, 1.0 - dist / MAX_HEAR_DIST) ** 1.5
            rel = math.atan2(dy, dx) - math.radians(self._listener.angle)
            pan = -math.sin(rel)                                    # positive sin means the source is to the left
        sfx.setVolume(volume)
        sfx.setBalance(max(-1.0, min(1.0, pan)))
        sfx.play()
