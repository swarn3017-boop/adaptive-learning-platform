import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv('DATA_DIR', BASE_DIR / 'data'))
TOPICS_FILE = DATA_DIR / 'topics.json'
STATE_FILE = DATA_DIR / 'system_state.json'
PROFILES_FILE = DATA_DIR / 'profiles.json'
USERS_FILE = DATA_DIR / 'users.json'
BACKUP_DIR = DATA_DIR / 'backups'

DEFAULT_HOST = os.getenv('SERVER_HOST', 'localhost')
DEFAULT_PORT = int(os.getenv('SERVER_PORT', '8000'))
DEBUG = os.getenv('DEBUG', '0').lower() in ('1', 'true', 'yes')
APP_ENV = os.getenv('APP_ENV', 'development')
WEB_AUTH_USER = os.getenv('WEB_AUTH_USER', '')
WEB_AUTH_PASS = os.getenv('WEB_AUTH_PASS', '')
ALLOWED_HOSTS = [host.strip() for host in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,::1').split(',') if host.strip()]
APP_SECRET = os.getenv('APP_SECRET', 'secret-key')
