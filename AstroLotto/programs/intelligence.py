# Program/utilities/intelligence.py (fixed imports, optional RF baseline)
from __future__ import annotations
from typing import List, Tuple
import random
from datetime import datetime
from collections import deque, Counter

import numpy as np

try:
    from sklearn.ensemble import RandomForestClassifier  # optional
except Exception:
    RandomForestClassifier = None  # type: ignore

def _prepare_features(draws: List[List[int]], num_range: int, n_history: int = 50):
    features, labels = [], []
    last_occurrence = {n: -1 for n in range(1, num_range + 1)}
    freq_queue = deque()
    running_count = Counter()
    short_window = 10

    for idx in range(len(draws) - 1):
        current_draw = set(draws[idx])
        running_count.update(current_draw)
        freq_queue.append(current_draw)
        if len(freq_queue) > n_history:
            running_count.subtract(freq_queue.popleft())
        recent_draws = draws[max(0, idx - short_window): idx]
        short_counter = Counter()
        for d in recent_draws:
            short_counter.update(d)
        next_draw = set(draws[idx + 1])
        for n in range(1, num_range + 1):
            features.append([
                running_count[n],
                short_counter[n],
                idx - last_occurrence[n] if last_occurrence[n] != -1 else n_history + 5
            ])
            labels.append(1 if n in next_draw else 0)
        for n in current_draw:
            last_occurrence[n] = idx
    return np.array(features, dtype=float), np.array(labels, dtype=int)

def predict_rf(draws: List[List[int]], num_range: int, k: int, n_history: int = 50) -> List[int]:
    """Return k numbers using a simple RF classifier probability ranking.
    If sklearn is unavailable or data is insufficient, falls back to random sample.
    """
    if RandomForestClassifier is None:
        return sorted(random.sample(range(1, num_range + 1), k))
    X, y = _prepare_features(draws, num_range, n_history)
    if len(np.unique(y)) < 2:
        return sorted(random.sample(range(1, num_range + 1), k))
    clf = RandomForestClassifier(n_estimators=200, max_depth=None, random_state=random.randint(0, 999999), n_jobs=-1)
    clf.fit(X, y)

    last_occurrence = {n: -1 for n in range(1, num_range + 1)}
    for idx, draw in enumerate(draws[-n_history:]):
        for n in draw:
            last_occurrence[n] = idx
    long_counter = Counter()
    for d in draws[-n_history:]:
        long_counter.update(d)
    short_counter = Counter()
    for d in draws[-10:]:
        short_counter.update(d)
    feats = []
    for n in range(1, num_range + 1):
        feats.append([
            long_counter[n],
            short_counter[n],
            (len(draws) - 1 - last_occurrence[n]) if last_occurrence[n] != -1 else n_history + 5
        ])
    probs = clf.predict_proba(np.array(feats, dtype=float))[:, 1]
    pairs = list(zip(range(1, num_range + 1), probs))
    pairs.sort(key=lambda x: (-x[1], x[0]))
    return sorted([num for num, _ in pairs[:k]])
