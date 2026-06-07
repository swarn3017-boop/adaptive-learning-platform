from datetime import datetime, timedelta
from typing import Dict, List, Optional
from core.analytics import calculate_mastery, calculate_confidence
from core.decision import (
    adaptive_review_interval,
    calculate_priority,
    generate_learning_path,
    needs_review,
    suggest_next_topics,
)
from core.feedback import log_study_session, record_recommendation
from core.models import LearningSystemState, TopicProgress, DEFAULT_PRIORITY_WEIGHTS, LearnerProfile, UserAccount
from storage.repository import AccountRepository, ProfileRepository
from storage.database import backup_data
from utils.security import generate_salt, hash_password, verify_password
import config
import json
from pathlib import Path


class LearningService:
    def __init__(self, profile_name: str = 'default') -> None:
        self.profile_repo = ProfileRepository()
        self.account_repo = AccountRepository()
        self.active_profile = self.profile_repo.get_or_create(profile_name)
        self.state = self.active_profile.state

    def _persist_topic(self, topic: TopicProgress) -> None:
        for index, existing in enumerate(self.active_profile.topics):
            if existing.topic == topic.topic:
                self.active_profile.topics[index] = topic
                self.profile_repo.save()
                return
        self.active_profile.topics.append(topic)
        self.profile_repo.save()

    def _copy_topic(
        self,
        topic: TopicProgress,
        score: Optional[float] = None,
        last_review: Optional[datetime] = None,
        attempt_history: Optional[List[float]] = None,
        next_review: Optional[datetime] = None,
        interval_days: Optional[int] = None,
        repetitions: Optional[int] = None,
        ease_factor: Optional[float] = None,
    ) -> TopicProgress:
        return TopicProgress(
            topic=topic.topic,
            score=topic.score if score is None else score,
            last_review=topic.last_review if last_review is None else last_review,
            difficulty=topic.difficulty,
            subject=topic.subject,
            tags=topic.tags.copy(),
            attempt_history=topic.attempt_history.copy() if attempt_history is None else attempt_history,
            interval_days=topic.interval_days if interval_days is None else interval_days,
            repetitions=topic.repetitions if repetitions is None else repetitions,
            ease_factor=topic.ease_factor if ease_factor is None else ease_factor,
            next_review=topic.next_review if next_review is None else next_review,
        )

    def _schedule_review(self, topic: TopicProgress, score: float) -> TopicProgress:
        quality = 5 if score >= 90 else 4 if score >= 75 else 3 if score >= 60 else 2 if score >= 50 else 1
        repetitions = topic.repetitions
        ease = topic.ease_factor

        if quality >= 3:
            repetitions = repetitions + 1 if repetitions > 0 else 1
            if repetitions == 1:
                interval = 1
            elif repetitions == 2:
                interval = 6
            else:
                interval = max(1, round(topic.interval_days * ease))
            ease = max(1.3, ease + (0.1 - (5 - quality) * 0.08))
        else:
            repetitions = 1
            interval = 1
            ease = max(1.3, ease - 0.2)

        next_review = datetime.now() + timedelta(days=interval)
        return self._copy_topic(
            topic,
            interval_days=interval,
            repetitions=repetitions,
            ease_factor=ease,
            next_review=next_review,
        )

    def add_topic(self, topic_name: str, score: float, difficulty: float, tags: List[str] = None, subject: str = '') -> TopicProgress:
        new_topic = TopicProgress(
            topic=topic_name,
            score=score,
            last_review=datetime.now(),
            difficulty=difficulty,
            subject=subject,
            tags=[tag.strip() for tag in tags] if tags else [],
            attempt_history=[score],
            interval_days=1,
            repetitions=1,
            ease_factor=2.5,
            next_review=datetime.now() + timedelta(days=1),
        )
        self._persist_topic(new_topic)
        return new_topic

    def get_topics(self) -> List[TopicProgress]:
        return self.active_profile.topics

    def find_topic(self, topic_name: str) -> TopicProgress:
        for topic in self.active_profile.topics:
            if topic.topic == topic_name:
                return topic
        raise ValueError(f'Topic not found: {topic_name}')

    def record_attempt(self, topic_name: str, new_score: float) -> TopicProgress:
        topic = self.find_topic(topic_name)
        updated_history = topic.attempt_history.copy()
        updated_history.append(new_score)
        updated_topic = self._copy_topic(topic, score=new_score, attempt_history=updated_history, last_review=datetime.now())
        updated_topic = self._schedule_review(updated_topic, new_score)
        self._persist_topic(updated_topic)
        return updated_topic

    def mark_reviewed(self, topic_name: str) -> TopicProgress:
        topic = self.find_topic(topic_name)
        updated_topic = self._copy_topic(topic, last_review=datetime.now())
        self._persist_topic(updated_topic)
        return updated_topic

    def recommend_topics(self, limit: int = 3) -> List[str]:
        topics = self.get_topics()
        recommended = suggest_next_topics(topics, limit, self.state.weights)
        record_recommendation(self.state, recommended)
        self.profile_repo.save()
        return recommended

    def get_progress_summary(self) -> Dict[str, float]:
        return {topic.topic: calculate_mastery(topic) for topic in self.get_topics()}

    def get_topic_confidence(self, topic_name: str) -> float:
        topic = self.find_topic(topic_name)
        return calculate_confidence(topic)

    def get_topic_review_interval(self, topic_name: str) -> int:
        topic = self.find_topic(topic_name)
        return adaptive_review_interval(topic)

    def is_review_due(self, topic_name: str) -> bool:
        topic = self.find_topic(topic_name)
        return needs_review(topic)

    def preview_recommendations(self, limit: int = 5) -> List[str]:
        return suggest_next_topics(self.get_topics(), limit, self.state.weights)

    def generate_learning_path(self, limit: int = 10) -> List[str]:
        return generate_learning_path(self.get_topics(), limit, self.state.weights)

    def get_due_topics(self) -> List[TopicProgress]:
        return [topic for topic in self.get_topics() if needs_review(topic)]

    def run_study_session(self, recommended_topics: List[str], completed_scores: Dict[str, float]) -> None:
        before_scores: Dict[str, float] = {}
        completed_topics: List[TopicProgress] = []

        for topic_name, score in completed_scores.items():
            topic = self.find_topic(topic_name)
            before_scores[topic_name] = topic.score
            updated_topic = self.record_attempt(topic_name, score)
            completed_topics.append(updated_topic)

        log_study_session(self.state, recommended_topics, completed_topics, before_scores)
        self.profile_repo.save()

    def clear_history(self) -> None:
        self.state.recommendation_history = []
        self.state.feedback_log = []
        self.state.weights = DEFAULT_PRIORITY_WEIGHTS.copy()
        self.active_profile.topics = []
        self.profile_repo.save()

    def export_history_csv(self) -> str:
        """Return a CSV string containing recommendation and feedback history suitable for Excel."""
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)
        # Header
        writer.writerow(['entry_type', 'timestamp', 'recommended_topics', 'completed_topics', 'average_improvement', 'success'])

        for rec in self.state.recommendation_history:
            writer.writerow([
                'recommendation',
                rec.get('timestamp', ''),
                ';'.join(rec.get('recommended_topics', [])) if rec.get('recommended_topics') else '',
                '',
                '',
                '',
            ])

        for fb in self.state.feedback_log:
            writer.writerow([
                'feedback',
                fb.get('timestamp', ''),
                ';'.join(fb.get('recommended_topics', [])) if fb.get('recommended_topics') else '',
                ';'.join(fb.get('completed_topics', [])) if fb.get('completed_topics') else '',
                fb.get('average_improvement', ''),
                fb.get('success', ''),
            ])

        return output.getvalue()

    def export_all_data(self) -> str:
        payload = {
            'users': [account.to_dict() for account in self.account_repo.list_accounts()],
            'profiles': [profile.to_dict() for profile in self.profile_repo.list_profiles()],
        }
        return json.dumps(payload, indent=2)

    def import_all_data(self, payload: str) -> None:
        data = json.loads(payload)
        if 'users' in data:
            self.account_repo.accounts = [UserAccount.from_dict(entry) for entry in data['users']]
            self.account_repo.save()
        if 'profiles' in data:
            self.profile_repo.profiles = [LearnerProfile.from_dict(entry) for entry in data['profiles']]
            self.profile_repo.save()

    def create_backup(self) -> Path:
        config.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        destination = Path(config.BACKUP_DIR) / f'backup-{datetime.now().strftime("%Y%m%d-%H%M%S")}.json'
        backup_data(destination)
        return destination

    def reset_weights_to_defaults(self) -> None:
        """Reset the system weight profile to the built-in defaults and persist."""
        self.state.weights = DEFAULT_PRIORITY_WEIGHTS.copy()
        self.profile_repo.save()

    def zero_out_weights(self) -> None:
        """Set all weights to zero and persist."""
        self.state.weights = {k: 0.0 for k in self.state.weights.keys()}
        self.profile_repo.save()

    def list_profiles(self) -> List[str]:
        return [profile.name for profile in self.profile_repo.list_profiles()]

    def create_profile(self, name: str) -> LearnerProfile:
        profile = self.profile_repo.add_profile(name)
        self.select_profile(name)
        return profile

    def select_profile(self, name: str) -> LearnerProfile:
        profile = self.profile_repo.get_or_create(name)
        self.active_profile = profile
        self.state = profile.state
        return profile

    def authenticate_user(self, username: str, password: str) -> bool:
        try:
            account = self.account_repo.find_by_username(username)
            return verify_password(password, account.salt, account.password_hash)
        except ValueError:
            return False

    def create_account(self, username: str, password: str) -> UserAccount:
        if any(account.username == username for account in self.account_repo.list_accounts()):
            raise ValueError(f'Account already exists: {username}')
        salt = generate_salt()
        password_hash = hash_password(password, salt)
        account = UserAccount(username=username, password_hash=password_hash, salt=salt, created_at=datetime.now())
        self.account_repo.add_account(account)
        self.profile_repo.get_or_create(username)
        return account

    def list_accounts(self) -> List[str]:
        return [account.username for account in self.account_repo.list_accounts()]

    def get_dashboard_data(self) -> Dict[str, str]:
        topics = self.get_topics()
        due = self.get_due_topics()
        weak = sorted(topics, key=lambda topic: topic.score)[:5]
        subjects = {}
        for topic in topics:
            subjects.setdefault(topic.subject or 'General', []).append(topic)
        return {
            'active_profile': self.active_profile.name,
            'topic_count': str(len(topics)),
            'due_count': str(len(due)),
            'weak_topics': ', '.join([topic.topic for topic in weak]) if weak else 'None',
            'subject_breakdown': ', '.join(f'{subject}({len(entries)})' for subject, entries in subjects.items()),
            'next_learning_path': ', '.join(self.generate_learning_path(5)),
        }
