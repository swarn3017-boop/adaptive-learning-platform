import math
from datetime import datetime
from typing import Dict, List, Optional
from core.models import DEFAULT_PRIORITY_WEIGHTS, TopicProgress
from core.analytics import calculate_mastery, calculate_confidence, calculate_weighted_trend
from utils.math_utils import clamp

MIN_REVIEW_DAYS = 2
MAX_REVIEW_DAYS = 21


def review_decay_factor(days_since_review: int, interval: int) -> float:
    if interval <= 0:
        return 0.0
    return round(clamp(math.exp(-days_since_review / interval), 0.0, 1.0), 3)


def adaptive_review_interval(progress: TopicProgress) -> int:
    mastery = calculate_mastery(progress)
    confidence = calculate_confidence(progress)
    base_support = mastery * 0.65 + confidence * 0.35
    base_interval = MIN_REVIEW_DAYS + base_support * (MAX_REVIEW_DAYS - MIN_REVIEW_DAYS)
    difficulty_adjustment = 1.0 - clamp(progress.difficulty, 0.0, 1.0) * 0.18
    interval = int(round(base_interval * difficulty_adjustment))
    return int(clamp(interval, MIN_REVIEW_DAYS, MAX_REVIEW_DAYS))


def calculate_priority(progress: TopicProgress, weights: Optional[Dict[str, float]] = None) -> float:
    active_weights = weights or DEFAULT_PRIORITY_WEIGHTS

    mastery = calculate_mastery(progress)
    confidence = calculate_confidence(progress)
    trend = calculate_weighted_trend(progress)

    days_since_review = (datetime.now() - progress.last_review).days
    review_gap = adaptive_review_interval(progress)
    urgency = clamp(days_since_review / review_gap, 0.0, 1.0)
    decline_bonus = max(-trend, 0.0)
    difficulty = clamp(progress.difficulty, 0.0, 1.0)

    raw_priority = (
        (1.0 - mastery) * active_weights['mastery']
        + (1.0 - confidence) * active_weights['confidence']
        + urgency * active_weights['age']
        + difficulty * active_weights['difficulty']
        + decline_bonus * active_weights['trend']
    )
    return round(clamp(raw_priority, 0.0, 1.0), 3)


def suggest_next_topics(progress_list: List[TopicProgress], limit: int = 3, weights: Optional[Dict[str, float]] = None) -> List[str]:
    ranked = [(topic.topic, calculate_priority(topic, weights)) for topic in progress_list]
    ranked.sort(key=lambda item: item[1], reverse=True)
    return [topic for topic, _ in ranked[:limit]]


def needs_review(progress: TopicProgress) -> bool:
    if progress.next_review:
        return datetime.now() >= progress.next_review
    days_since_review = (datetime.now() - progress.last_review).days
    return days_since_review >= adaptive_review_interval(progress)


def generate_learning_path(progress_list: List[TopicProgress], limit: int = 10, weights: Optional[Dict[str, float]] = None) -> List[str]:
    prioritized = sorted(
        progress_list,
        key=lambda progress: (
            needs_review(progress),
            calculate_priority(progress, weights),
            progress.score,
            progress.difficulty,
        ),
        reverse=True,
    )
    return [topic.topic for topic in prioritized[:limit]]
