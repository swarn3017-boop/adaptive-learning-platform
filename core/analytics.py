import math
from typing import List
from core.models import TopicProgress
from utils.math_utils import clamp


def normalize_score(raw_score: float, max_score: float = 100.0) -> float:
    if max_score <= 0:
        raise ValueError('max_score must be positive')
    return clamp(raw_score / max_score, 0.0, 1.0)


def calculate_confidence(progress: TopicProgress) -> float:
    history = progress.attempt_history
    attempts = len(history)
    if attempts == 0:
        return 0.0

    average = sum(history) / attempts
    variance = sum((score - average) ** 2 for score in history) / attempts
    consistency = 1.0 - clamp(math.sqrt(variance) / 50.0, 0.0, 1.0)
    confidence = min(attempts / 10.0, 1.0) * consistency
    return round(clamp(confidence, 0.0, 1.0), 3)


def calculate_weighted_trend(progress: TopicProgress, lookback: int = 5) -> float:
    history = progress.attempt_history
    if len(history) < 2:
        return 0.0

    recent = history[-lookback:]
    deltas = [recent[i] - recent[i - 1] for i in range(1, len(recent))]
    weights = list(range(1, len(deltas) + 1))
    weighted_delta = sum(delta * weight for delta, weight in zip(deltas, weights)) / sum(weights)
    return clamp(weighted_delta / 100.0, -0.05, 0.05)


def calculate_mastery(progress: TopicProgress) -> float:
    normalized = normalize_score(progress.score)
    difficulty_factor = 1.0 - clamp(progress.difficulty, 0.0, 1.0) * 0.2
    trend_adjustment = 1.0 + calculate_weighted_trend(progress)
    return round(normalized * difficulty_factor * trend_adjustment, 3)
