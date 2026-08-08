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
- Docker (Optional)

### Installation

1. **Clone & Install**
   ```bash
   git clone https://github.com/your-username/insight-flow.git
   cd insight-flow
   npm install && cd frontend && npm install
   cd ../backend && pip install -r requirements.txt
   ```

2. **Configure Environment**
   Copy example files:
   ```bash
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env.local
   ```
   *Update `backend/.env` with your `DATABASE_URL`.*

3. **Run Development Server**
   ```bash
   # Root directory
   npm run dev
   ```
   - Frontend: `http://localhost:3000`
   - Backend Docs: `http://localhost:8000/docs`

---

## � Docker Deployment

For a production-ready setup with database and caching included:

```bash
cp .env.docker.example .env.docker
docker compose --env-file .env.docker up -d --build
```

---

## ✅ Verification

We maintain a zero-tolerance policy for test failures.

```bash
# Backend (Security & Logic)
cd backend && pytest

# Frontend (E2E & Accessibility)
cd frontend && npm run test:e2e
```

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
