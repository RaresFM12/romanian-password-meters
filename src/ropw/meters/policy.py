from ..normalize import nfc


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


def policy_score(password, strict=False):
    p = nfc(password)
    min_len = 12 if strict else 8
    need = 4 if strict else 3
    if len(p) < min_len:
        return 0
    return 4 if len(char_classes(p)) >= need else 0


class Policy:
    def __init__(self, strict=False):
        self.strict = strict
        self.name = "M-POLICY-STRICT" if strict else "M-POLICY"

    def score(self, password):
        return policy_score(password, self.strict)
