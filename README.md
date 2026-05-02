# Competitor Intelligence Platform

<div align="center">

**Full-stack data monitoring & analytics platform for cloud service competitive intelligence**

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red)](https://www.sqlalchemy.org/)
[![Vue](https://img.shields.io/badge/Vue-3.x-4FC08D)](https://vuejs.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

</div>

---

## Overview

A real-time competitive intelligence platform that automates cloud vendor monitoring. The system continuously collects public competitor data (pricing, reviews, product changes), runs Chinese NLP analysis, detects anomalies, and presents findings through an interactive dashboard.

**Core loop:** Collect → Detect → Analyze → Alert, fully automated.

---

## Architecture

```
Frontend (Vue 3 + Chart.js, CDN)     ←→     11 Router Modules (60+ endpoints)
                                                    ↕
API Gateway (slowapi rate-limit, CORS, JWT auth)    ←   WebSocket realtime push
                                                    ↕
Service Layer (14 services, injectable db sessions)  ←   APScheduler cron jobs
                                                    ↕
Data Pipeline (fetch → checksum diff → persist → alert)
                                                    ↕
SQLAlchemy 2.0 ORM (12 tables) + SQLite (swappable to PostgreSQL)
```

### Data Model (12 tables, all with foreign-key relationships)

```
competitors ──┬── price_history        (time-series pricing)
              ├── user_reviews          (sentiment-scored reviews)
              ├── changes               (detected content diffs)
              ├── monitoring_snapshots  (content checksums)
              ├── monitoring_logs       (collection audit trail)
              ├── analysis_reports      (auto-generated reports)
              ├── alert_rules           (per-competitor alert config)
              ├── alert_history         (triggered alert log)
              ├── scraper_configs       (per-target collection settings)
              ├── scrape_results        (structured collection output)
              └── monitoring_schedules  (cron-based collection jobs)
```

---

## Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Database | SQLite, ORM-swappable | Zero-config for dev/demo; change connection string for PostgreSQL in production |
| Frontend | Vue 3 CDN, no build step | View-source friendly; zero build-tool friction for demo |
| ORM pattern | `_session()` context manager + injected db | Test with in-memory SQLite; production uses file-based; same code path |
| Async bridge | ThreadPoolExecutor wrapping sync services | SQLAlchemy 2.0 sync ORM + FastAPI async endpoints coexist cleanly |
| Scraper resilience | 3-level fallback (Playwright → httpx+BS4 → offline fixture) | Survives target website changes without data gaps |
| NLP | jieba TF-IDF from real user reviews | Extracts top 20 keywords per competitor; pure Python, no extra runtime |
| Anomaly detection | Z-score on price time-series | Flags data points >2σ from rolling mean |
| Scheduling | APScheduler with adaptive frequency | Adjusts collection interval based on change velocity per competitor |

---

## Quick Start

```bash
# Requirements: Python 3.11+
git clone <repo-url> && cd competitor-watch
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Start (demo mode — no external dependencies needed)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Open:
#   http://localhost:8000/v3              — Overview dashboard
#   http://localhost:8000/product/v2      — Competitor detail (4 analysis tabs)
#   http://localhost:8000/alerts          — Alert center
#   http://localhost:8000/docs            — Swagger API docs
```

### Docker

```bash
docker compose up
```

---

## Feature Map

### Dashboard
- Multi-competitor overview with real-time price/latest change/sentiment cards
- Market distribution pie chart, activity trend line
- Latest changes timeline with severity indicators (P0/P1/P2)
- WebSocket live data push with auto-reconnect

### Competitor Detail (4 tabs)
- **Overview:** Price trend, sentiment pie, sentiment trend, monitoring frequency bar chart, 5-dimension radar chart
- **Price:** Historical price chart, cross-competitor comparison bar chart, 7-day linear price prediction
- **Reviews:** Sentiment distribution, real-user review list with sentiment labels, TF-IDF keyword bar chart
- **Analytics:** Trend with anomaly bands (mean ±10%), anomaly table with Z-score, correlation matrix placeholder

### Alert Center
- P0/P1/P2 severity classification
- Configurable per-competitor alert rules (price threshold, review sentiment drop, update frequency anomaly)
- Alert timeline with acknowledge/silence actions

### Data Pipeline
- Playwright headless browser scraper with stealth mode (random UA, Chinese locale)
- httpx+BeautifulSoup lightweight fallback
- Offline fixture cache for demo reliability
- Content checksum comparison → only persist actual changes
- Alert rule evaluation on change detection

---

## API Summary

| Group | Endpoint | Description |
|-------|----------|-------------|
| Competitors | `GET/POST /api/competitors` | List, create competitors |
| | `GET/PUT/DELETE /api/competitors/{id}` | Detail, update, delete |
| | `GET /api/competitors/matrix` | Cross-competitor comparison matrix |
| | `GET /api/competitors/posture` | 5-dimension scoring |
| Prices | `GET /api/v1/prices/history` | Price time-series with statistics |
| | `GET /api/v1/prices/compare` | Multi-competitor price comparison |
| | `GET /api/v1/prices/predict` | 7-30 day linear prediction |
| Reviews | `GET /api/v1/reviews` | Paginated review list |
| | `GET /api/v1/reviews/sentiment` | Sentiment distribution summary |
| | `GET /api/v1/reviews/sentiment/trend` | Daily sentiment trend |
| Analytics | `GET /api/product/{id}/keywords` | TF-IDF keyword extraction |
| | `GET /api/analytics/correlation-matrix` | Cross-competitor correlation |
| Alerts | `GET/PATCH /api/alerts` | Alert list and status update |
| | `GET /api/alerts/stats` | Alert statistics |
| Diff | `GET /api/diff/changes` | Detected changes with old/new values |
| Realtime | `WS /ws/realtime` | Live price, review, and log push |

Full Swagger docs at `/docs` when running.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Web framework | FastAPI 0.115+ (async endpoints, auto OpenAPI) |
| ORM | SQLAlchemy 2.0 (DeclarativeBase, session context manager) |
| Validation | Pydantic 2.5+ / pydantic-settings |
| Auth | PyJWT + passlib[bcrypt] |
| Rate limiting | slowapi (per-IP, configurable) |
| Scheduling | APScheduler 3.10+ (adaptive frequency) |
| NLP | jieba 0.42+ (Chinese segmentation + TF-IDF) |
| Scraping | Playwright (headless Chromium) + httpx + BeautifulSoup4 |
| Frontend | Vue 3 (CDN) + Chart.js 4.x |
| Real-time | WebSocket (FastAPI native) |
| Notifications | Apprise (multi-channel) |
| Deployment | Docker + docker-compose |
| CI | GitHub Actions: ruff lint + pytest + coverage |

---

## Project Structure

```
competitor-watch/
├── app/
│   ├── main.py                    # FastAPI app, middleware, lifecycle events
│   ├── core/                      # config, database, models (12 tables), auth, executor
│   ├── routers/                   # 11 route modules
│   ├── services/                  # 14 service modules (incl. data pipeline, scraper engine)
│   ├── models/                    # Pydantic request/response schemas
│   └── tests/                     # pytest + in-memory SQLite
├── dashboard/
│   ├── templates/                 # Vue 3 HTML pages
│   └── static/                    # JS, CSS, Chart.js composables
├── config/                        # Notification rules, fixture data
├── data/fixtures/                 # Offline scraper cache (150+ products per competitor)
├── alembic/                       # DB migration scripts
├── offline/                       # Self-contained demo HTML (no server needed)
├── .github/workflows/             # CI: lint + test + coverage
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## Testing

```bash
# Run all tests (uses in-memory SQLite, no external dependencies)
pytest app/tests/ -v --tb=short

# With coverage
pytest app/tests/ -v --cov=app --cov-report=term-missing
```

Tests cover: competitors CRUD, price history API, reviews sentiment API, auth flow, WebSocket connection, alert evaluation logic.

---

## License

MIT
