from random import Random

from mock_logs.models import PlaceholderValues


FIRST_NAMES = ("alex", "sam", "jordan", "priya", "chen", "maria", "tomas", "aisha", "liam", "noor")
LAST_NAMES = ("smith", "patel", "nguyen", "garcia", "okafor", "kowalski", "tanaka", "silva", "brown", "haddad")


def random_placeholder_values(rng: Random) -> PlaceholderValues:
    return PlaceholderValues(
        order_id=f"ORD-{rng.randint(100000, 999999)}",
        trace_id=f"{rng.getrandbits(64):016x}",
        customer_email=f"{rng.choice(FIRST_NAMES)}.{rng.choice(LAST_NAMES)}@example.com",
        latency_ms=rng.randint(20, 2500),
    )
