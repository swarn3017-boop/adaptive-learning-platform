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
        
        # Migrate profiles lacking owner field to 'default' user for backward compatibility
        for profile in self.profiles:
            if not hasattr(profile, 'owner') or not profile.owner:
                profile.owner = 'default'
        
        if not self.profiles:
            legacy_topics = load_topics()
            legacy_state = load_state()
            self.profiles = [LearnerProfile(name='default', owner='default', created_at=datetime.now(), state=legacy_state, topics=legacy_topics)]
            self.save()

    def list_profiles(self, owner: Optional[str] = None) -> List[LearnerProfile]:
        """Return all profiles, optionally filtered by owner."""
        if owner is None:
            return self.profiles
        return [profile for profile in self.profiles if profile.owner == owner]

    def list_profiles_by_owner(self, owner: str) -> List[LearnerProfile]:
        """Return profiles owned by a specific user."""
        return [profile for profile in self.profiles if profile.owner == owner]

    def find_by_name(self, name: str, owner: Optional[str] = None) -> LearnerProfile:
        """Find a profile by name, optionally filtered by owner."""
        for profile in self.profiles:
            if profile.name == name and (owner is None or profile.owner == owner):
                return profile
        if owner:
            raise ValueError(f'Profile "{name}" not found for user "{owner}"')
        raise ValueError(f'Profile not found: {name}')

    def find_by_name_and_owner(self, name: str, owner: str) -> LearnerProfile:
        """Find a profile by name and owner (enforced)."""
        return self.find_by_name(name, owner=owner)

    def get_or_create(self, name: str, owner: str = 'default') -> LearnerProfile:
        """Get or create a profile with owner enforcement."""
        try:
            return self.find_by_name(name, owner=owner)
        except ValueError:
            profile = LearnerProfile(name=name, owner=owner, created_at=datetime.now())
            self.profiles.append(profile)
            self.save()
            return profile

    def add_profile(self, name: str, owner: str) -> LearnerProfile:
        """Add a new profile with ownership enforcement."""
        # Check if THIS USER already has a profile with this name
        if any(profile.name == name and profile.owner == owner for profile in self.profiles):
            raise ValueError(f'Profile "{name}" already exists for user "{owner}"')
        profile = LearnerProfile(name=name, owner=owner, created_at=datetime.now())
        self.profiles.append(profile)
        self.save()
        return profile

    def delete_profile(self, name: str, owner: Optional[str] = None) -> None:
        """Delete a profile, optionally verifying ownership."""
        if owner:
            # Verify ownership before deletion
            try:
                self.find_by_name_and_owner(name, owner)
            except ValueError:
                raise ValueError(f'Cannot delete profile: ownership verification failed')
        self.profiles = [profile for profile in self.profiles if not (profile.name == name and (owner is None or profile.owner == owner))]
        self.save()

    def save(self) -> None:
        save_profiles([profile.to_dict() for profile in self.profiles])
