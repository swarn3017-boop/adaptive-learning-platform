from datetime import datetime
from typing import Dict, List
from core.models import LearningSystemState, TopicProgress
from utils.math_utils import clamp


def evaluate_performance_impact(before_score: float, after_score: float) -> float:
    return after_score - before_score


def normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    total = sum(weights.values())
    if total <= 0:
        return {key: 0.0 for key in weights}
    return {key: max(value / total, 0.0) for key, value in weights.items()}


def update_weights_from_feedback(state: LearningSystemState, improvement: float) -> None:
    adjustment = min(abs(improvement) / 200.0, 0.01)
    if improvement > 0:
        state.weights['mastery'] = clamp(state.weights['mastery'] + adjustment, 0.0, 1.0)
        state.weights['confidence'] = clamp(state.weights['confidence'] + adjustment, 0.0, 1.0)
        state.weights['trend'] = clamp(state.weights['trend'] - adjustment * 0.2, 0.0, 1.0)
    else:
        state.weights['trend'] = clamp(state.weights['trend'] + adjustment * 0.2, 0.0, 1.0)
        state.weights['age'] = clamp(state.weights['age'] + adjustment * 0.1, 0.0, 1.0)
    state.weights = normalize_weights(state.weights)


def record_recommendation(state: LearningSystemState, recommended_topics: List[str]) -> None:
    # Save recommended topics so the system can learn from feedback later.
    state.recommendation_history.append({
        'timestamp': datetime.now().isoformat(),
        'recommended_topics': recommended_topics,
    })


def log_study_session(
    state: LearningSystemState,
    recommended_topics: List[str],
    completed_topics: List[TopicProgress],
    before_scores: Dict[str, float],
) -> None:
    improvements = []
    for topic in completed_topics:
        if topic.topic in before_scores:
            improvements.append(evaluate_performance_impact(before_scores[topic.topic], topic.score))

    average_improvement = sum(improvements) / len(improvements) if improvements else 0.0
    state.feedback_log.append({
        'timestamp': datetime.now().isoformat(),
        'recommended_topics': recommended_topics,
        'completed_topics': [topic.topic for topic in completed_topics],
        'average_improvement': round(average_improvement, 3),
        'success': average_improvement > 0.0,
    })
    update_weights_from_feedback(state, average_improvement)
