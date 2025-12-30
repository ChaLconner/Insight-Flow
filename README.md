# 🌊 Insight-Flow

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/your-username/insight-flow)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests: Backend](https://img.shields.io/badge/tests--backend-passing-success.svg)](#testing--quality-assurance)
[![Tests: Frontend](https://img.shields.io/badge/tests--frontend-passing-success.svg)](#testing--quality-assurance)
[![Aesthetics](https://img.shields.io/badge/design-premium-ff69b4.svg)](#architecture)

**Insight-Flow** is a state-of-the-art, high-performance project management and team collaboration platform. Engineered for clarity, speed, and visual excellence, it bridges the gap between complex task management and intuitive user experience.

---

## Key Features

- 💎 **Premium Dashboard** — High-fidelity analytics with real-time progress tracking.
- 📋 **Advanced Task Management** — Intuitive project organization with flexible task workflows.
- 💳 **Stripe Subscription Suite** — Seamless plan management, tier-based limits, and secure billing.
- 🔐 **Enterprise-Grade Security** — Multi-provider OAuth (Google/GitHub), CSRF protection, and advanced rate limiting.
- ⚡ **Optimized Performance** — Lazy load optimizations, query caching, and HSL-tailored dark mode.
- 🐳 **Docker Ready** — Fully containerized for easy deployment and scalability.
- 🔔 **Intelligent Notifications** — Real-time event logging and user alerts via Email (SMTP).
- 📁 **Seamless File Handling** — Secure project asset management with Cloudinary integration.

## Architecture

Insight-Flow is built with a modern, decoupled architecture designed for scalability and maintainability.

### 🛠️ Tech Stack

| Layer        | Technology                                                                               |
| :----------- | :--------------------------------------------------------------------------------------- |
| **Frontend** | Next.js 16.0.8, Tailwind CSS 4.1.17, Zustand 4.5.4, React Query 5.90, Framer Motion 11.3 |
| **Backend**  | FastAPI 0.115.6, SQLAlchemy 2.0.44, Alembic 1.13, Pydantic v2.10                         |
| **Database** | PostgreSQL 15+, Redis 5.0 (Caching & Rate Limiting)                                      |
| **Payments** | Stripe 7.0 (Subscriptions, Webhooks, Downgrade Logic)                                    |
| **Auth**     | JWT (PyJWT 2.10), OAuth2 (Google & GitHub)                                               |
| **Testing**  | Pytest 7.4.3 (Backend), Vitest 4.0 & Playwright 1.57 (Frontend)                          |

---

## Getting Started

### Prerequisites

- **Node.js**: 20.x or higher
- **Python**: 3.11.x or higher
- **PostgreSQL**: 15.x or higher
- **Stripe Account**: (Required for billing features)
- **SMTP Server**: (Gmail or other provier for email notifications)

### Installation Guide

The project includes a root-level `package.json` to manage both environments simultaneously:

1. **Clone & Install**

   ```bash
   git clone https://github.com/your-username/insight-flow.git
   cd insight-flow
   npm install      # Install root dev dependencies
   cd frontend && npm install
   cd ../backend && pip install -r requirements.txt
   ```

2. **Environment Configuration**

   Copy the example environment files and update them with your credentials:

   ```bash
   # Backend
   cp backend/.env.example backend/.env

   # Frontend
   cp frontend/.env.example frontend/.env.local
   ```

   **Key Variables to Configure:**

   - `DATABASE_URL`: Your PostgreSQL connection string.
   - `STRIPE_SECRET_KEY` & `STRIPE_PUBLISHABLE_KEY`: From your Stripe Dashboard.
   - `CLOUDINARY_*`: For file uploads.
   - `GOOGLE_CLIENT_ID` / `GITHUB_CLIENT_ID`: For OAuth authentication.
   - `SMTP_*`: For email notifications (Required for production).

3. **Database Setup**

   Initialize the database schema:

   ```bash
   cd backend
   alembic upgrade head
   ```

4. **Launch Development Environment**

   From the project root:

   ```bash
   npm run dev
   ```

   - **Frontend**: `http://localhost:3000`
   - **Backend API**: `http://localhost:8000`

## 🚀 Deployment Guide

### Docker Production Setup

1.  **Prepare Environment**:
    Copy `.env.docker.example` to `.env.docker` and populate it with production secrets.

    ```bash
    cp .env.docker.example .env.docker
    # Edit .env.docker with real keys including SMTP credentials
    ```

2.  **Build and Run**:

    ```bash
    docker-compose up -d --build
    ```

3.  **Verify Services**:
    - Backend Health: `http://localhost:8000/health`
    - Frontend: `http://localhost:3000`

### Manual Deployment (Ubuntu/Linux)

For traditional VPS deployment:

1.  **Backend**:

    - Install Python 3.11+ and dependencies.
    - Set environment variables or use `.env`.
    - Run with Gunicorn/Uvicorn: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app`

2.  **Frontend**:
    - Build: `npm run build`
    - Serve with PM2 or Nginx.

## 🔧 Troubleshooting

### Common Issues

1.  **Database Connection Refused**

    - Ensure PostgreSQL is running.
    - Check `DATABASE_URL` in `.env`.
    - Verification: `pg_isready -h localhost -p 5432`

2.  **Email Sending Failed**

    - Verify `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, and `SMTP_PASSWORD`.
    - Note: Gmail requires an App Password, not your login password.
    - Check if `ENVIRONMENT` is set to `production`.

3.  **CORS Errors**

    - Check `CORS_ORIGINS` in `backend/.env`.
    - Ensure frontend URL is listed (e.g., `http://localhost:3000`).

4.  **Redis Connection**

    - If caching fails, ensure Redis is running or `REDIS_URL` is correct.
    - For development, comment out `REDIS_URL` to use in-memory cache.

---

## Testing & Quality Assurance

We maintain a zero-tolerance policy for test failures.

### Backend (pytest)

```bash
cd backend
pytest -rs -v
```

- ✅ **All Tests Passing**: 100% success rate on the latest run.
- ✅ **Security Focused**: Comprehensive CSRF and JWT validation testing.
- ✅ **Performance**: Integrated latency benchmarks.

### Frontend (Vitest & Playwright)

```bash
cd frontend
npm run test        # Unit tests
npm run test:e2e    # Integration tests
```

---

## API Documentation

The backend provides interactive documentation automatically:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Key API Endpoints

| Category      | Endpoints      | Description                                            |
| ------------- | -------------- | ------------------------------------------------------ |
| **Auth**      | `/auth/*`      | Login, register, OAuth (Google/GitHub), password reset |
| **Projects**  | `/projects/*`  | CRUD, member management, permissions                   |
| **Tasks**     | `/tasks/*`     | Task management with status/priority                   |
| **Payment**   | `/payment/*`   | Stripe integration, subscriptions, billing             |
| **Analytics** | `/analytics/*` | Project metrics and charts                             |

---

## Security

Insight-Flow implements enterprise-grade security:

| Feature              | Implementation                            |
| -------------------- | ----------------------------------------- |
| **Authentication**   | JWT with HttpOnly cookies, refresh tokens |
| **OAuth 2.0**        | Google & GitHub providers                 |
| **CSRF Protection**  | Double-submit cookie pattern              |
| **Rate Limiting**    | Per-user + IP-based (Redis in production) |
| **Audit Logging**    | Payment operations tracked                |
| **Input Validation** | Pydantic schemas                          |

---

## Project Structure

```text
insight-flow/
├── backend/
│   ├── models/           # SQLAlchemy 2.0 Data Models (15 models)
│   ├── routers/          # API Endpoints (13 routers)
│   ├── services/         # Async Business Logic Layer (23 services)
│   ├── schemas/          # Type-safe Validation (Pydantic)
│   ├── middleware/       # CSRF, rate limiting, caching
│   ├── security/         # Payment security, audit logging
│   ├── scripts/          # Database seeding & utility tools
│   └── tests/            # High-coverage test suite (80%+ target)
├── frontend/
│   ├── src/app/          # Next.js App Router (Layouts/Pages)
│   ├── src/components/   # Highly reusable UI components
│   ├── src/hooks/        # Custom React hooks (12 hooks)
│   └── src/stores/       # Zustand Global State Management
└── docker-compose.yml    # Containerized production Orchestration
```

---

## Contributing

We follow the **Conventional Commits** standard.

1. Fork the repo.
2. Create your branch (`git checkout -b feature/aesthetics`).
3. Commit your changes (`git commit -m 'feat: add glassmorphism to charts'`).
4. Push to the branch (`git push origin feature/aesthetics`).
5. Open a Pull Request.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

Developed with excellence by the **Insight-Flow Team**
