import hashlib
import inspect
from collections import Counter


def test_hash_signature():
    for name in sorted(hashlib.algorithms_guaranteed):
        algo = getattr(hashlib, name)
        assert hasattr(algo(), 'digest_size')
        try:
            params = list(inspect.signature(algo).parameters.values())
        except ValueError:
            continue

        kinds = Counter(x.kind for x in params)
        assert kinds[inspect.Parameter.KEYWORD_ONLY] == len(params) - 1, (name, algo, params)
