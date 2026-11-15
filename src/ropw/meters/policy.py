from ..normalize import nfc

DEFAULT = {"normal": {"min_len": 8, "min_classes": 3},
           "strict": {"min_len": 12, "min_classes": 4}}


def char_classes(password):
    classes = set()
    for ch in password:
        if ch.isdigit():
            classes.add("digit")
        elif ch.isalpha():
            if ch.isupper():
                classes.add("upper")
            else:
                classes.add("lower")
        else:
            classes.add("symbol")
    return classes


def policy_score(password, strict=False, cfg=None):
    rules = (cfg or DEFAULT)["strict" if strict else "normal"]
    p = nfc(password)
    if len(p) < rules["min_len"]:
        return 0
    return 4 if len(char_classes(p)) >= rules["min_classes"] else 0


class Policy:
    def __init__(self, strict=False, cfg=None):
        self.strict = strict
        self.cfg = cfg
        self.name = "M-POLICY-STRICT" if strict else "M-POLICY"

    def score(self, password):
        return policy_score(password, self.strict, self.cfg)
