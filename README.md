# Adaptive Learning Engine

A clean, modular portfolio project for a self-improving adaptive learning system written in pure Python.

## Description

This project models an adaptive study system that tracks topic performance, predicts priorities, and updates recommendation weights based on real feedback.

## Features

- Topic progress tracking with attempt history and spaced repetition scheduling
- Mastery, confidence, and trend analytics
- Priority-based recommendation engine with learning path recommendations
- Learner account management with secure login and per-user profiles
- Curriculum grouping by subject and review readiness dashboard
- Import/export and backup support for full dataset recovery
- JSON persistence for users, profiles, topics, and system state
- Browser-based UI, monitoring endpoints, and CLI workflow
- Docker-ready deployment for production environments

## System Architecture

- `core/`
  - `models.py`: dataclasses for topics and system state
  - `analytics.py`: mastery, confidence, and trend calculations
  - `decision.py`: scheduling and priority recommendation logic
  - `feedback.py`: feedback logging and weight adjustment
- `storage/`
  - `database.py`: JSON persistence helpers
  - `repository.py`: repository interfaces for topics and state
- `services/`
  - `learning_service.py`: central controller connecting all modules
- `utils/`
  - `math_utils.py`: shared helper functions
  - `security.py`: account and cookie signing helpers
- `main.py`: CLI entrypoint with data export/import and backup commands
- `config.py`: file paths and deployment settings
- `Dockerfile`: production build container
- `docker-compose.yml`: simple local deployment stack

## Feedback Loop

When a study session is logged, the system:

1. Records completed topic scores
2. Measures score improvement
3. Updates the feedback log
4. Adjusts recommendation weights slightly based on performance

This keeps recommendations adaptive and evidence-driven.

## Run the project

From the `adaptive-learning-engine` folder, run:

```bash
python main.py create-account --username alice --password secret
python main.py create-profile --name alice
python main.py add-topic --topic Algebra --score 70 --difficulty 0.5
python main.py recommend --limit 3
python main.py record-attempt --topic Algebra --score 82
python main.py study-session --recommended Algebra --completed Algebra:82
python main.py summary --profile alice
```

### Export, import, backup

```bash
python main.py export-data --output backup.json
python main.py import-data --input backup.json
python main.py backup-data
```

## Web Interface

Start the browser UI:

```bash
python main.py run-server --host localhost --port 8000
```

Then open `http://localhost:8000` in your browser.

The app also exposes lightweight monitoring endpoints:

- `http://localhost:8000/health`
- `http://localhost:8000/metrics`

## Environment configuration

The server can be configured with environment variables for deployment and security:

- `SERVER_HOST` — host to bind (default: `localhost`)
- `SERVER_PORT` — port to serve (default: `8000`)
- `DEBUG` — enable debug mode (`1` / `true` / `yes`)
- `APP_ENV` — environment name (`development` / `production`)
- `DATA_DIR` — custom storage directory for JSON files
- `WEB_AUTH_USER` and `WEB_AUTH_PASS` — optional Basic Auth credentials for the web UI
- `ALLOWED_HOSTS` — comma-separated allowed client hosts (default: `localhost,127.0.0.1,::1`)

## Docker Deployment

Build and run the container locally:

```bash
docker build -t adaptive-learning-engine .
docker run -p 8000:8000 -e APP_SECRET=replace-this-secret adaptive-learning-engine
```

Or use Docker Compose:

```bash
docker compose up --build
```

## Requirements

- Python 3.9+

No external libraries are required.
