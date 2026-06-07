# Adaptive Learning Platform

## Overview

Adaptive Learning Platform is a personalized study recommendation system designed to help learners identify what they should study next.

The platform tracks topic performance, analyzes learning trends, calculates mastery and confidence scores, and generates adaptive recommendations based on a student's progress.

The goal of the project is to explore how data-driven learning systems can improve study efficiency by prioritizing weak or forgotten topics instead of relying on static study schedules.

---

## Live Demo

Demo: https://adaptive-learning-platform-vkeg.onrender.com/

---

## Features

### Learning Analytics

* Topic progress tracking
* Mastery score calculation
* Confidence score calculation
* Trend analysis from historical performance
* Adaptive review scheduling
* Priority-based topic recommendations
* Learning path generation

### User Management

* User registration
* User authentication
* Secure password hashing using PBKDF2
* Session-based login system

### Study Tracking

* Attempt history storage
* Study session logging
* Feedback tracking
* Progress summaries

### Data Management

* CSV export
* JSON export
* Data import support
* Automated backups

### Web Application

* Browser-based interface
* Dashboard page
* Recommendation page
* Progress summary page
* Curriculum overview
* Dark mode support

### Deployment

* Dockerized application
* Render deployment support
* Health monitoring endpoints
* Configurable environment variables

---

## Recommendation Engine

The recommendation engine evaluates topics using multiple learning factors:

1. Mastery Score

   * Measures understanding of a topic based on performance.

2. Confidence Score

   * Estimates confidence using score consistency and attempt history.

3. Trend Analysis

   * Detects improvement or decline over recent attempts.

4. Review Scheduling

   * Dynamically adjusts review intervals based on topic performance.

5. Priority Scoring

   * Combines mastery, confidence, trend, difficulty, and review age to determine what should be studied next.

Topics with the highest priority are recommended first.

---

## Tech Stack

Backend:

* Python

Data Storage:

* JSON-based persistence

Security:

* PBKDF2 password hashing
* Session authentication

Deployment:

* Docker
* Render

Version Control:

* Git
* GitHub

---

## Project Structure

adaptive-learning-platform/

├── core/

├── services/

├── storage/

├── utils/

├── tests/

├── data/

├── Dockerfile

├── docker-compose.yml

├── requirements.txt

└── main.py

---

## Future Improvements

* AI-generated study recommendations
* Advanced spaced repetition algorithms
* Analytics dashboards and visualizations
* Performance forecasting
* Multi-device synchronization
* Database integration

---

## Motivation

I built this project to explore how software can personalize education and make learning more efficient.

Instead of treating every topic equally, the platform attempts to identify where a learner should focus attention next based on performance data and study history.

The project combines software engineering, learning analytics, recommendation systems, and web application development.

---

## Author

Swarn

GitHub:
https://github.com/swarn3017-boop

Project Repository:
https://github.com/swarn3017-boop/adaptive-learning-platform
