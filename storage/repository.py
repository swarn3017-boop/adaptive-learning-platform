from datetime import datetime
from typing import List, Optional
from core.models import TopicProgress, LearningSystemState, LearnerProfile, UserAccount
from storage.database import (
    load_state,
    save_state,
    load_topics,
    save_topics,
    load_profiles,
    save_profiles,
    load_users,
    save_users,
)


class TopicRepository:
    def __init__(self) -> None:
        self.topics: List[TopicProgress] = load_topics()

    def list_topics(self) -> List[TopicProgress]:
        return self.topics

    def save(self) -> None:
        save_topics(self.topics)

    def add(self, topic: TopicProgress) -> None:
        self.topics.append(topic)
        self.save()

    def update(self, updated_topic: TopicProgress) -> None:
        for index, topic in enumerate(self.topics):
            if topic.topic == updated_topic.topic:
                self.topics[index] = updated_topic
                self.save()
                return
        self.add(updated_topic)

    def find_by_name(self, name: str) -> TopicProgress:
        for topic in self.topics:
            if topic.topic == name:
                return topic
        raise ValueError(f'Topic not found: {name}')


class SystemStateRepository:
    def __init__(self) -> None:
        self.state: LearningSystemState = load_state()

    def save(self) -> None:
        save_state(self.state)


class AccountRepository:
    def __init__(self) -> None:
        self.accounts: List[UserAccount] = [UserAccount.from_dict(entry) for entry in load_users()]

    def list_accounts(self) -> List[UserAccount]:
        return self.accounts

    def find_by_username(self, username: str) -> UserAccount:
        for account in self.accounts:
            if account.username == username:
                return account
        raise ValueError(f'Account not found: {username}')

    def add_account(self, account: UserAccount) -> None:
        if any(existing.username == account.username for existing in self.accounts):
            raise ValueError(f'Account already exists: {account.username}')
        self.accounts.append(account)
        self.save()

    def save(self) -> None:
        save_users([account.to_dict() for account in self.accounts])


class ProfileRepository:
    def __init__(self) -> None:
        self.profiles: List[LearnerProfile] = [LearnerProfile.from_dict(entry) for entry in load_profiles()]
        if not self.profiles:
            legacy_topics = load_topics()
            legacy_state = load_state()
            self.profiles = [LearnerProfile(name='default', created_at=datetime.now(), state=legacy_state, topics=legacy_topics)]
            self.save()

    def list_profiles(self) -> List[LearnerProfile]:
        return self.profiles

    def find_by_name(self, name: str) -> LearnerProfile:
        for profile in self.profiles:
            if profile.name == name:
                return profile
        raise ValueError(f'Profile not found: {name}')

    def get_or_create(self, name: str) -> LearnerProfile:
        try:
            return self.find_by_name(name)
        except ValueError:
            profile = LearnerProfile(name=name, created_at=datetime.now())
            self.profiles.append(profile)
            self.save()
            return profile

    def add_profile(self, name: str) -> LearnerProfile:
        if any(profile.name == name for profile in self.profiles):
            raise ValueError(f'Profile already exists: {name}')
        profile = LearnerProfile(name=name, created_at=datetime.now())
        self.profiles.append(profile)
        self.save()
        return profile

    def delete_profile(self, name: str) -> None:
        self.profiles = [profile for profile in self.profiles if profile.name != name]
        self.save()

    def save(self) -> None:
        save_profiles([profile.to_dict() for profile in self.profiles])
