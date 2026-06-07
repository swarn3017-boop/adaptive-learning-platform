import json
from pathlib import Path
from typing import Any, Dict, List
from core.models import LearningSystemState, TopicProgress
import config


def ensure_data_dir() -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)


def save_json(path: Path, data: Any) -> None:
    ensure_data_dir()
    with path.open('w', encoding='utf-8') as handle:
        json.dump(data, handle, indent=2)


def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open('r', encoding='utf-8') as handle:
        return json.load(handle)


def save_state(state: LearningSystemState) -> None:
    save_json(config.STATE_FILE, state.to_dict())


def load_state() -> LearningSystemState:
    raw = load_json(config.STATE_FILE)
    if raw is None:
        return LearningSystemState()
    return LearningSystemState.from_dict(raw)


def save_profiles(profiles: List[Dict[str, Any]]) -> None:
    save_json(config.PROFILES_FILE, profiles)


def load_profiles() -> List[Dict[str, Any]]:
    raw = load_json(config.PROFILES_FILE)
    if raw is None:
        return []
    return list(raw)


def save_users(users: List[Dict[str, Any]]) -> None:
    save_json(config.USERS_FILE, users)


def load_users() -> List[Dict[str, Any]]:
    raw = load_json(config.USERS_FILE)
    if raw is None:
        return []
    return list(raw)


def save_topics(topics: List[TopicProgress]) -> None:
    save_json(config.TOPICS_FILE, [topic.to_dict() for topic in topics])


def load_topics() -> List[TopicProgress]:
    raw = load_json(config.TOPICS_FILE)
    if raw is None:
        return []
    return [TopicProgress.from_dict(entry) for entry in raw]


def backup_data(destination: Path) -> None:
    ensure_data_dir()
    destination.parent.mkdir(parents=True, exist_ok=True)
    files_to_backup = [config.USERS_FILE, config.PROFILES_FILE, config.TOPICS_FILE, config.STATE_FILE]
    archive = {}
    for file_path in files_to_backup:
        archive[file_path.name] = load_json(file_path)
    with destination.open('w', encoding='utf-8') as handle:
        json.dump(archive, handle, indent=2)
