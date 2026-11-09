# 📦 AI-Powered E-Commerce Inventory Manager

A production-grade, full-stack inventory management and auditing platform featuring concurrency-safe pessimistic database locking, immutable audit logging, Celery background worker alerts, and a grounded AI assistant layer.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.14](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flask 3.0](https://img.shields.io/badge/Flask-3.0-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![React 19](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![Celery](https://img.shields.io/badge/Celery-5.4-37814A?logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)

---

## 🎥 Live Deployment & Preview
- **Live Frontend (Vercel):** [https://ai-inventory-manager.vercel.app](https://ai-inventory-manager.vercel.app) *(Update with your URL)*
- **API Documentation & Health (Render):** [https://inventory-backend-api.onrender.com/api/health](https://inventory-backend-api.onrender.com/api/health) *(Update with your URL)*
- **3-Minute Architecture Walkthrough:** [Watch Loom Technical Demo](https://www.loom.com) *(Update with your Loom URL)*

---

## ⚡ Architectural Highlights

1. **Concurrency-Safe Stock Mutations (`SELECT ... FOR UPDATE`):**
   - Implements pessimistic row-level locking inside PostgreSQL transactions to eliminate lost-update race conditions and prevent negative stock balances during high-concurrency checkout and restock spikes.
2. **Immutable, Append-Only Audit Ledger:**
   - Every stock adjustment creates a corresponding `StockHistory` record committed within the same database transaction.
   - User identity attribution is strictly derived from the cryptographically verified JWT payload (`g.current_user.username`) rather than untrusted request bodies, preventing identity spoofing.
3. **Grounded "Facts-First" AI Architecture:**
   - SQL aggregates are deterministically calculated by PostgreSQL before LLM evaluation, eliminating hallucinated stock metrics.
   - Natural-language search parses user prompts into allowlisted query filters (`ALLOWED_FILTERS`), preventing direct Text-to-SQL prompt injection vulnerabilities.
   - Implements a sandboxed, read-only tool-calling (function calling) registry for interactive administrative assistance.
4. **Decoupled Asynchronous Alerts:**
   - Uses Celery with a Redis message broker to dispatch automated low-stock warnings without blocking synchronous HTTP request/response threads.
   - Includes an in-memory deduplication cooldown cache to prevent notification fatigue.
5. **Modern Reactive Dashboard:**
   - Built with Vite, React, TanStack Query v5 (query caching, window-refocus synchronization, background invalidation), Tailwind CSS, Recharts analytics with safety threshold watermarks, and Sonner promise toast notifications.

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend REST API** | Python 3.14, Flask 3.0, Flask-SQLAlchemy, Flask-Migrate (Alembic), PyJWT, Werkzeug |
| **Frontend Client** | React 19, TypeScript, Vite, TanStack Query v5, Tailwind CSS, Lucide React, Recharts, Sonner |
| **Database & Cache** | PostgreSQL 16 (Relational Schema & Row-Locks), Redis 7 (Message Broker) |
| **Background Processing**| Celery 5.4 (Asynchronous task worker with automatic retry backoffs) |
| **Container & Proxy** | Docker, Docker Compose, Nginx (Alpine), Gunicorn WSGI Server |
| **Testing & Quality** | Pytest (38 automated unit, integration, and E2E lifecycle tests) |

---

## 📁 Repository Structure

```text
├── backend/
│   ├── app/
│   │   ├── api/               # Modular Flask Blueprints (products, categories, auth, ai)
│   │   ├── models/            # SQLAlchemy models (Product, Category, Supplier, StockHistory, User)
│   │   ├── services/          # Grounded AIService, tool registry, and mock adapters
│   │   ├── tasks/             # Celery asynchronous worker tasks (low-stock alerts)
│   │   ├── utils/             # JWT auth decorators (@token_required, @roles_required)
│   │   ├── celery_app.py      # Celery application factory wrapper
│   │   ├── config.py          # Environment configuration classes
│   │   └── extensions.py      # Decoupled database and migration handles
│   ├── migrations/            # Alembic schema version scripts
│   ├── tests/                 # Comprehensive Pytest suite (38 passing tests)
│   ├── Dockerfile             # Multi-stage production Python container
│   ├── requirements.txt       # Pinned production backend dependencies
│   ├── run.py                 # Development runner
│   └── wsgi.py                # Production Gunicorn entrypoint
├── frontend/
│   ├── src/
│   │   ├── components/        # Dialogs, charts, search bars, and AI Copilot drawer
│   │   ├── services/          # Strongly-typed fetch API client with auto auth headers
│   │   ├── App.tsx            # Main reactive inventory management dashboard
│   │   └── main.tsx           # QueryClientProvider and Sonner toaster setup
│   ├── nginx.conf             # Production Nginx reverse proxy configuration
│   ├── Dockerfile             # Multi-stage Vite build + Nginx Alpine runner
│   └── package.json           # Frontend dependencies and scripts
└── docker-compose.yml         # Unified 5-container orchestration service cluster
