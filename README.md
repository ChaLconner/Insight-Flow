# Insight Flow

Insight Flow is a full-stack web application built with Next.js (frontend) and FastAPI (backend). This project provides a modern web interface with a powerful API backend for data processing and insights.

## Project Structure

```
insight-flow/
├── backend/                 # FastAPI backend
│   ├── database.py         # Database configuration
│   ├── main.py             # Main FastAPI application
│   ├── requirements.txt    # Python dependencies
│   ├── models/             # Data models
│   └── routers/            # API route handlers
└── frontend/               # Next.js frontend
    ├── app/                # Next.js app directory
    │   ├── globals.css     # Global styles
    │   ├── layout.tsx      # Root layout component
    │   └── page.tsx        # Home page component
    ├── public/             # Static assets
    ├── package.json        # Node.js dependencies
    └── README.md           # Frontend-specific documentation
```

## Technology Stack

### Frontend
- **Next.js 16.0.1** - React framework with App Router
- **React 19.2.0** - UI library
- **TypeScript** - Type-safe JavaScript
- **Tailwind CSS 4** - Utility-first CSS framework
- **ESLint** - Code linting

### Backend
- **FastAPI 0.104.1** - Modern, fast web framework for building APIs
- **Uvicorn** - ASGI server
- **SQLAlchemy 2.0.44** - SQL toolkit and ORM
- **Python Multipart** - For handling form data

## Getting Started

### Prerequisites
- Node.js (v18 or higher)
- Python (v3.8 or higher)
- npm or yarn

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd insight-flow
```

2. Install frontend dependencies:
```bash
cd frontend
npm install
```

3. Install backend dependencies:
```bash
cd ../backend
pip install -r requirements.txt
```

### Running the Application

1. Start the backend server:
```bash
cd backend
uvicorn main:app --reload
```
The API will be available at `http://localhost:8000`

2. Start the frontend development server:
```bash
cd frontend
npm run dev
```
The application will be available at `http://localhost:3000`

## API Documentation

Once the backend server is running, you can access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Development

### Frontend Development Commands
```bash
npm run dev      # Start development server
npm run build    # Build for production
npm run start    # Start production server
npm run lint     # Run ESLint
```

### Backend Development
The backend uses FastAPI with automatic reloading when code changes are made. The CORS middleware is configured to allow requests from `http://localhost:3000` (the frontend development server).

## Project Status

This project is currently in development. The frontend is a standard Next.js application with Tailwind CSS styling, and the backend provides a basic FastAPI setup with CORS middleware configured for frontend-backend communication.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.