from pathlib import Path
from ..config import REPO_ROOT
from ..normalize import nfc

DEFAULT_BLOCKLIST = REPO_ROOT / "data/lexicon/meter/common.txt"
EXPECTED_COUNT = 49233


class Block:
    name = "M-BLOCK"

    def __init__(self, path=DEFAULT_BLOCKLIST, check_count=True):
        path = Path(path)
        self.blocklist = set()
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")
                if line:
                    self.blocklist.add(line.lower())
        if check_count and len(self.blocklist) != EXPECTED_COUNT:
            raise ValueError("blocklist has " + str(len(self.blocklist))
                             + " entries, expected " + str(EXPECTED_COUNT))

    def score(self, password):
        return 0 if nfc(password).lower() in self.blocklist else 4
