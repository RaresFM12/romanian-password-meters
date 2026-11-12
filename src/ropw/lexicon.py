import csv
from pathlib import Path
from .config import REPO_ROOT


class SeedList:
    def __init__(self, name, items):
        self.name = name
        self.items = list(items)

    @classmethod
    def load(cls, path, name=None):
        path = Path(path)
        if not path.is_absolute():
            path = REPO_ROOT / path
        rows = []
        with open(path, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f, delimiter="\t"):
                rows.append((int(r["rank"]), r["item"]))
        rows.sort()
        return cls(name or path.stem, [item for rank, item in rows])

    @classmethod
    def from_items(cls, name, items):
        return cls(name, list(items))

    @property
    def size(self):
        return len(self.items)

    def usable_bands(self, band_defs):
        bands = []
        for lo, hi in band_defs:
            if lo > self.size:
                break
            bands.append((lo, min(hi, self.size)))
        return bands

    def sample(self, rng, band):
        lo, hi = band
        rank = int(rng.integers(lo, hi + 1))
        return self.items[rank - 1], rank

    def filter(self, predicate):
        return SeedList(self.name, [w for w in self.items if predicate(w)])
