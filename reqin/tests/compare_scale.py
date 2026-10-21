"""A stress input for the comparison engine: many *different* requirements built from a word list in which a few words are very common and most are rare, the way real specifications are.

    PYTHONPATH=src:tests python3 compare_scale.py [N ...]        prints, for each N, the seconds taken and what the engine counted

The worst case for finding near misses is not a large dataset of copies (`reqin make-datasets --only F9` is that, and is quick because equal wordings collapse) but one where many words occur in
nearly `max_posting` wordings. This makes that. It is made up, with no real requirement in it, and what it shows is how long the engine takes, not how well it compares.
"""
from __future__ import annotations

import random
import sys
import time

WORDS = 2500
VERBS = ["start", "stop", "report", "store", "send", "open", "close", "reset", "apply", "record", "verify", "display", "enable", "disable", "log", "reject", "accept", "monitor"]
UNITS = [("s", 1), ("ms", 100), ("kg", 40), ("V", 30), ("kPa", 200), ("Hz", 60), ("%", 100)]


def make(n: int, seed: int = 5) -> list[dict]:
    from reqin.normalise import normalise_text
    rng = random.Random(seed)
    weights = [1.0 / (i + 1) for i in range(WORDS)]               # Zipf: word 0 is in nearly everything, word 2000 in almost nothing
    vocab = [f"w{i}" for i in range(WORDS)]
    out, seen = [], set()
    while len(out) < n:
        subj = " ".join(rng.choices(vocab, weights, k=rng.randint(1, 2)))
        pred = " ".join(rng.choices(vocab, weights, k=rng.randint(1, 3)))
        text = f"The {subj} shall {rng.choice(VERBS)} the {pred}"
        if rng.random() < 0.4:
            u, top = rng.choice(UNITS)
            text += f" within {rng.randint(1, top)} {u}"
        if rng.random() < 0.2:
            text += f" when the {rng.choices(vocab, weights, k=1)[0]} is {rng.choice(['low', 'high', 'open', 'closed'])}"
        text += "."
        if text in seen:
            continue
        seen.add(text)
        i = len(out)
        out.append({"mid": f"m{i:06d}", "uid": f"S-{i:06d}", "uid_synthetic": False, "text": text, "norm_text": normalise_text(text), "fields": {}, "parent_mid": None})
    return out


def main(argv: list[str]) -> int:
    from reqin.compare import compare
    for n in [int(a) for a in argv] or [2000, 8000, 25000]:
        rows = make(n)
        t = time.time()
        res = compare(rows)
        c = res.summary["counts"]
        print(f"{n:>6} requirements: {time.time() - t:6.1f} s  clusters {c['clusters']:>5}  pairs {sum(c['pairs'].values()):>6}  too-common words {res.summary['limits']['tokens_too_common_to_find_pairs']:>4}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
