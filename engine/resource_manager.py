"""Resource file lookup with priorities: mods (highest priority first), then base assets."""
from __future__ import annotations

from pathlib import Path


class ResourceManager:
    def __init__(self, roots: list[Path]):
        self.roots = list(roots)          # from highest priority to lowest

    def find(self, subdir: str, filename: str) -> Path | None:
        for root in self.roots:
            p = root / subdir / filename
            if p.is_file():
                return p
        return None

    def list_names(self, subdir: str, suffix: str) -> set[str]:
        names: set[str] = set()
        for root in self.roots:
            d = root / subdir
            if d.is_dir():
                names |= {p.stem for p in d.glob(f"*{suffix}")}
        return names
