import random
from datetime import datetime, timedelta, timezone


def get_seeded_rng(seed: int = 42):
    return random.Random(seed)


def random_id(prefix: str, rng: random.Random) -> str:
    return f"{prefix}_{rng.randint(1000, 99999)}"


def rand_amount(rng: random.Random) -> int:
    base = rng.choice([499, 999, 1499, 1999, 2499, 3499, 4999, 9999, 14999, 19999, 29999])
    return base


def rand_amount_minor(rng: random.Random) -> int:
    return rand_amount(rng) * 100
