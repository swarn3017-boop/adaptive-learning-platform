from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List

DEFAULT_PRIORITY_WEIGHTS = {
    'mastery': 0.28,
    'confidence': 0.35,
    'age': 0.2,
    'difficulty': 0.12,
    'trend': 0.05,
}


@dataclass
class TopicProgress:
    topic: str
    score: float
    last_review: datetime
    difficulty: float
    subject: str = ''
    tags: List[str] = field(default_factory=list)
    attempt_history: List[float] = field(default_factory=list)
    interval_days: int = 1
    repetitions: int = 0
    ease_factor: float = 2.5
    next_review: datetime = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'topic': self.topic,
            'score': self.score,
            'last_review': self.last_review.isoformat(),
            'difficulty': self.difficulty,
            'subject': self.subject,
            'tags': self.tags,
            'attempt_history': self.attempt_history,
            'interval_days': self.interval_days,
            'repetitions': self.repetitions,
            'ease_factor': self.ease_factor,
            'next_review': self.next_review.isoformat() if self.next_review else None,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'TopicProgress':
        next_review_value = data.get('next_review')
        return TopicProgress(
            topic=data['topic'],
            score=float(data['score']),
            last_review=datetime.fromisoformat(data['last_review']),
            difficulty=float(data['difficulty']),
            subject=str(data.get('subject', '') or ''),
            tags=[str(tag).strip() for tag in data.get('tags', []) if str(tag).strip()],
            attempt_history=[float(value) for value in data.get('attempt_history', [])],
            interval_days=int(data.get('interval_days', 1)),
            repetitions=int(data.get('repetitions', 0)),
            ease_factor=float(data.get('ease_factor', 2.5)),
            next_review=datetime.fromisoformat(next_review_value) if next_review_value else None,
        )


@dataclass
class LearningSystemState:
    weights: Dict[str, float] = field(default_factory=lambda: DEFAULT_PRIORITY_WEIGHTS.copy())
    recommendation_history: List[Dict[str, Any]] = field(default_factory=list)
    feedback_log: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'weights': self.weights,
            'recommendation_history': self.recommendation_history,
            'feedback_log': self.feedback_log,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'LearningSystemState':
        return LearningSystemState(
            weights={str(k): float(v) for k, v in data.get('weights', {}).items()},
            recommendation_history=list(data.get('recommendation_history', [])),
            feedback_log=list(data.get('feedback_log', [])),
        )


@dataclass
class LearnerProfile:
    name: str
    owner: str  # Username of the account that owns this profile
    created_at: datetime
    state: LearningSystemState = field(default_factory=LearningSystemState)
    topics: List[TopicProgress] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'owner': self.owner,
            'created_at': self.created_at.isoformat(),
            'state': self.state.to_dict(),
            'topics': [topic.to_dict() for topic in self.topics],
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'LearnerProfile':
        return LearnerProfile(
            name=str(data.get('name', 'default')),
            owner=str(data.get('owner', 'default')),  # Default to 'default' for backward compatibility
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
            state=LearningSystemState.from_dict(data.get('state', {})),
            topics=[TopicProgress.from_dict(entry) for entry in data.get('topics', [])],
        )


@dataclass
class UserAccount:
    username: str
    password_hash: str
    salt: str
    created_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            'username': self.username,
            'password_hash': self.password_hash,
            'salt': self.salt,
            'created_at': self.created_at.isoformat(),
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'UserAccount':
        return UserAccount(
            username=str(data['username']),
            password_hash=str(data['password_hash']),
            salt=str(data['salt']),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
        )
