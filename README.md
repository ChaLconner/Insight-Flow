# 🌊 Insight-Flow

[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests: Backend](https://img.shields.io/badge/tests--backend-passing-success.svg)](#verify)
[![Tests: Frontend](https://img.shields.io/badge/tests--frontend-passing-success.svg)](#verify)

**Insight-Flow** is a premium project management platform engineered for speed, security, and visual excellence. It combines a Staff-level architecture with an inclusive, accessible user experience.

---

## ✨ Why Insight-Flow?

- **💎 Premium UX**: Glassmorphism aesthetic, responsive Framer Motion animations, and WCAG AA accessibility.
- **🛡️ Enterprise Security**: **Argon2id** hashing, HIBP breach detection, and Role-Based Access Control (RBAC).
- **⚡ High Performance**: Optimized with **Redis** caching, optimistic UI updates, and request performance metrics.

---

## 🛠️ Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Frontend** | Next.js 16, Tailwind CSS 4, Zustand, React Query |
| **Backend** | FastAPI, SQLAlchemy 2.0, Pydantic v2, Argon2-cffi |
| **Infrastructure** | PostgreSQL 15, Redis 7, Docker Compose |
| **QA** | Playwright (E2E), Vitest, Pytest |

---

## 🚀 Quick Start

### Prerequisites
- Node.js 20+
- Python 3.12+
- Docker Desktop with WSL 2 (Optional; required for the bundled PostgreSQL and Redis services)

### Installation

1. **Clone & install JavaScript dependencies**
   ```bash
   git clone https://github.com/your-username/insight-flow.git
   cd insight-flow
   npm ci
   cd frontend
   npm ci
   cd ..
   ```
   `npm ci` uses the committed lockfiles and prevents dependency drift.
   On Windows, stop any running `npm run dev` or Next.js process before rerunning
   `npm ci`; native packages such as `lightningcss` can be locked while the server runs.

2. **Create an isolated Python environment**
   ```bash
   python --version
   python -m venv backend/.venv
   ```

   PowerShell:
   ```powershell
   .\backend\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   python -m pip install -r backend\requirements.txt
   python -m pip check
   ```

   macOS/Linux:
   ```bash
   source backend/.venv/bin/activate
   python -m pip install --upgrade pip
   python -m pip install -r backend/requirements.txt
   python -m pip check
   ```
   Keep this environment activated when running `npm run dev`. If PowerShell blocks
   activation, run installation commands with `backend\.venv\Scripts\python.exe`
   and allow scripts for current process only:
   `Set-ExecutionPolicy -Scope Process Bypass`.

3. **Configure environment**
   PowerShell:
   ```powershell
   if (-not (Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
   if (-not (Test-Path frontend/.env.local)) { Copy-Item frontend/.env.example frontend/.env.local }
   ```

   macOS/Linux:
   ```bash
   [ -f backend/.env ] || cp backend/.env.example backend/.env
   [ -f frontend/.env.local ] || cp frontend/.env.example frontend/.env.local
   ```
   *Update `backend/.env` with your `DATABASE_URL`.*

4. **Run development server**
   ```bash
   # Root directory
   npm run dev
   ```
   - Frontend: `http://localhost:3000`
   - Backend Docs: `http://localhost:8000/docs`

---

## 🐳 Docker Deployment

For a production-ready setup with database and caching included:

On Windows, Docker Desktop requires WSL 2. Run this in an elevated PowerShell,
restart Windows, then install and start Docker Desktop:

```powershell
wsl.exe --install --no-distribution
winget install --id Docker.DockerDesktop --exact --accept-source-agreements --accept-package-agreements
```

Verify host prerequisites before starting services:

```powershell
wsl --status
docker version
docker compose version
```

Replace every `CHANGE_THIS`, `replace-with`, and example credential in
`.env.docker.example` with local values. Use Stripe test keys for local work.
Never commit `.env.docker`.

```bash
cp .env.docker.example .env.docker
docker compose --env-file .env.docker config --quiet
docker compose --env-file .env.docker up -d --build
```

PowerShell copy command:

```powershell
Copy-Item .env.docker.example .env.docker
docker compose --env-file .env.docker config --quiet
docker compose --env-file .env.docker up -d --build
```

The `migrate` service initializes a fresh local database. For an existing
database, take a backup, change to `backend`, and run
`python -m alembic upgrade head` only after confirming `DATABASE_URL` points to
the intended target; this changes schema.

---

## ✅ Verification

Run these checks from repository root after installation:

```bash
# Frontend quality, tests, and production build
cd frontend
npm run type-check
npm run lint:check
npm run test:coverage
npm run build
cd ..

# Backend quality and tests
cd backend
python -m ruff check .
python -m ruff format --check .
python -m pytest --cov=. --cov-fail-under=85 -q
python -X utf8 scripts/validate_migrations.py
python -m alembic upgrade head --sql
cd ..
```

End-to-end tests require running PostgreSQL and Redis. Install the Playwright
browser once with `cd frontend; npx playwright install chromium`, then run
`npm run test:e2e`.

---

## 📂 Project Structure

```text
insight-flow/
├── backend/          # FastAPI App (Clean Architecture)
│   ├── models/       # SQLAlchemy Data Models
│   ├── routers/      # API Endpoints
│   ├── services/     # Business Logic & Security
│   └── tests/        # Pytest Suite
├── frontend/         # Next.js App
│   ├── src/app/      # App Router
│   ├── src/components/# Reusable UI
│   └── e2e/          # Playwright Tests
└── docker-compose.yml
```

---

## 🤝 Contributing

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/amazing-feature`).
3. Commit changes (`git commit -m 'feat: add amazing feature'`).
4. Push to the branch (`git push origin feature/amazing-feature`).
5. Open a Pull Request.

---

## License

Distributed under the MIT License. See `LICENSE` for more information.
