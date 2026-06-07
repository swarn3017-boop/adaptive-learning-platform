import argparse

import config
from services.learning_service import LearningService
from services.web_server import run_web_server


def parse_completed_scores(score_pairs: str):
    completed = {}
    if not score_pairs:
        return completed
    for pair in score_pairs.split(','):
        if ':' not in pair:
            continue
        name, value = pair.split(':', 1)
        try:
            completed[name.strip()] = float(value.strip())
        except ValueError:
            continue
    return completed


def run_add_topic(service: LearningService, args) -> None:
    topic = service.add_topic(args.topic, args.score, args.difficulty)
    print(f'Added topic: {topic.topic}')


def run_record_attempt(service: LearningService, args) -> None:
    topic = service.record_attempt(args.topic, args.score)
    service.mark_reviewed(args.topic)
    print(f'Recorded attempt for {topic.topic}. New score: {topic.score}')


def run_recommend(service: LearningService, args) -> None:
    topics = service.recommend_topics(args.limit)
    print('Recommended topics:')
    for name in topics:
        print(f'- {name}')


def run_study_session(service: LearningService, args) -> None:
    recommended = [item.strip() for item in args.recommended.split(',') if item.strip()]
    completed = parse_completed_scores(args.completed)

    # Input flows through recommendation and feedback stages
    service.run_study_session(recommended, completed)
    print('Study session logged.')


def run_summary(service: LearningService, args) -> None:
    summary = service.get_progress_summary()
    print('Progress summary:')
    for topic, score in summary.items():
        print(f'- {topic}: mastery={score}')


def run_state(service: LearningService, args) -> None:
    state = service.state
    print('System weights:')
    for key, value in state.weights.items():
        print(f'- {key}: {value}')
    print(f'Logged recommendations: {len(state.recommendation_history)}')
    print(f'Feedback entries: {len(state.feedback_log)}')


def run_create_account(service: LearningService, args) -> None:
    service.create_account(args.username, args.password)
    print(f'Created account: {args.username}')


def run_list_accounts(service: LearningService, args) -> None:
    for username in service.list_accounts():
        print(f'- {username}')


def run_export_data(service: LearningService, args) -> None:
    payload = service.export_all_data()
    with open(args.output, 'w', encoding='utf-8') as handle:
        handle.write(payload)
    print(f'Exported data to {args.output}')


def run_import_data(service: LearningService, args) -> None:
    with open(args.input, 'r', encoding='utf-8') as handle:
        payload = handle.read()
    service.import_all_data(payload)
    print(f'Imported data from {args.input}')


def run_backup_data(service: LearningService, args) -> None:
    destination = service.create_backup()
    print(f'Created backup at {destination}')


def main() -> None:
    parser = argparse.ArgumentParser(description='Adaptive Learning Engine CLI')
    parser.add_argument('--profile', default='default', help='Profile name to use')
    parser.add_argument('--username', default='default', help='Username for access control (required for protected operations)')
    subparsers = parser.add_subparsers(dest='command')

    add_parser = subparsers.add_parser('add-topic', help='Add a new learning topic')
    add_parser.add_argument('--topic', required=True)
    add_parser.add_argument('--score', required=True, type=float)
    add_parser.add_argument('--difficulty', required=True, type=float)

    attempt_parser = subparsers.add_parser('record-attempt', help='Record an attempt score for a topic')
    attempt_parser.add_argument('--topic', required=True)
    attempt_parser.add_argument('--score', required=True, type=float)

    recommend_parser = subparsers.add_parser('recommend', help='Get topic recommendations')
    recommend_parser.add_argument('--limit', type=int, default=3)

    session_parser = subparsers.add_parser('study-session', help='Log a study session')
    session_parser.add_argument('--recommended', required=True)
    session_parser.add_argument('--completed', required=True)

    subparsers.add_parser('summary', help='View mastery summary')
    subparsers.add_parser('state', help='View current system state')
    profile_parser = subparsers.add_parser('create-profile', help='Create a new profile')
    profile_parser.add_argument('--name', required=True, help='New profile name')
    subparsers.add_parser('list-profiles', help='List all learner profiles')
    account_parser = subparsers.add_parser('create-account', help='Create a new user account')
    account_parser.add_argument('--username', required=True)
    account_parser.add_argument('--password', required=True)
    subparsers.add_parser('list-accounts', help='List all user accounts')
    export_parser = subparsers.add_parser('export-data', help='Export full system data to JSON')
    export_parser.add_argument('--output', required=True, help='Output JSON file path')
    import_parser = subparsers.add_parser('import-data', help='Import full system data from JSON')
    import_parser.add_argument('--input', required=True, help='Input JSON file path')
    backup_parser = subparsers.add_parser('backup-data', help='Create a timestamped backup of storage')
    server_parser = subparsers.add_parser('run-server', help='Run the browser-based interface')
    server_parser.add_argument('--host', default=config.DEFAULT_HOST)
    server_parser.add_argument('--port', type=int, default=config.DEFAULT_PORT)

    args = parser.parse_args()

    if args.command == 'run-server':
        run_web_server(args.host, args.port)
        return

    # Load persisted state and topic data at startup with user context
    service = LearningService(profile_name=args.profile, username=args.username)

    if args.command == 'add-topic':
        run_add_topic(service, args)
    elif args.command == 'record-attempt':
        run_record_attempt(service, args)
    elif args.command == 'recommend':
        run_recommend(service, args)
    elif args.command == 'study-session':
        run_study_session(service, args)
    elif args.command == 'summary':
        run_summary(service, args)
    elif args.command == 'state':
        run_state(service, args)
    elif args.command == 'create-profile':
        profile = service.create_profile(args.name)
        print(f'Created profile: {profile.name}')
    elif args.command == 'list-profiles':
        for name in service.list_profiles():
            print(f'- {name}')
    elif args.command == 'create-account':
        run_create_account(service, args)
    elif args.command == 'list-accounts':
        run_list_accounts(service, args)
    elif args.command == 'export-data':
        run_export_data(service, args)
    elif args.command == 'import-data':
        run_import_data(service, args)
    elif args.command == 'backup-data':
        run_backup_data(service, args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
