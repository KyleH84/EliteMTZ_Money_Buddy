
import random
from datetime import datetime

def get_cosmic_entropy() -> int:
    return int(datetime.now().timestamp())

def is_weird_news_day() -> bool:
    return random.choice([True, False, False])

def is_crypto_volatile() -> bool:
    return random.choice([True, False])

def is_full_moon(moon_phase: float) -> bool:
    return 0.95 <= moon_phase <= 1.0

def apply_cosmic_chaos(numbers, retrograde, alignment_score, moon_phase):
    if retrograde or alignment_score > 75 or is_weird_news_day():
        numbers = random.sample(numbers, len(numbers))
    if is_full_moon(moon_phase) or is_crypto_volatile():
        midpoint = max(numbers)//2
        numbers = sorted([n for n in numbers if n <= midpoint])
    return numbers
