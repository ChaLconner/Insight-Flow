# Insight Flow

Insight Flow is a comprehensive full-stack web application that combines a modern React-based frontend with a powerful Python backend. This project provides an intuitive interface for data visualization, task management, and insights generation with real-time updates and responsive design.

## 🚀 Features

- **Modern UI/UX**: Clean, responsive interface built with Next.js and Tailwind CSS
- **Real-time Updates**: Live data synchronization between frontend and backend
- **Task Management**: Complete CRUD operations for task tracking and management
- **Data Visualization**: Interactive charts and visual representations of data
- **RESTful API**: Well-documented API endpoints built with FastAPI
- **Type Safety**: Full TypeScript implementation for both frontend and backend
- **Responsive Design**: Mobile-first approach that works on all devices

## 📁 Project Structure

```
insight-flow/
├── backend/                 # FastAPI backend application
│   ├── database.py         # Database configuration and connection
│   ├── main.py             # Main FastAPI application entry point
│   ├── requirements.txt    # Python dependencies
│   ├── models/             # SQLAlchemy data models
│   │   └── __init__.py     # Models initialization
│   └── routers/            # API route handlers
│       └── __init__.py     # Router initialization
├── frontend/               # Next.js frontend application
│   ├── app/                # Next.js App Router directory
│   │   ├── globals.css     # Global CSS styles
│   │   ├── layout.tsx      # Root layout component
│   │   └── page.tsx        # Home page component
│   ├── public/             # Static assets and public files
│   │   ├── file.svg        # SVG icons
│   │   ├── globe.svg       # SVG icons
│   │   ├── next.svg        # Next.js logo
│   │   ├── vercel.svg      # Vercel logo
│   │   └── window.svg      # SVG icons
│   ├── services/           # API service layer
│   │   └── api.ts          # API client implementation
│   ├── store/              # State management
│   │   └── taskStore.ts    # Task state management
│   ├── package.json        # Node.js dependencies
│   ├── tsconfig.json       # TypeScript configuration
│   ├── tailwind.config.js  # Tailwind CSS configuration
│   ├── next.config.ts      # Next.js configuration
│   ├── eslint.config.mjs   # ESLint configuration
│   ├── postcss.config.mjs  # PostCSS configuration
│   └── README.md           # Frontend-specific documentation
├── .gitignore              # Git ignore file
├── README.md               # Project documentation
├── package.json            # Root package.json
└── package-lock.json       # npm lock file
```

## 🛠 Technology Stack

### Frontend
- **Next.js 16.0.1** - React framework with App Router for modern web development
- **React 19.2.0** - Latest version of React for building user interfaces
- **TypeScript** - Type-safe JavaScript for better code quality and developer experience
- **Tailwind CSS 4** - Utility-first CSS framework for rapid UI development
- **ESLint** - Code linting and formatting for consistent code style

### Backend
- **FastAPI 0.104.1** - Modern, fast web framework for building APIs with Python
- **Uvicorn** - ASGI server for running FastAPI applications
- **SQLAlchemy 2.0.44** - SQL toolkit and ORM for database operations
- **Python Multipart** - For handling form data and file uploads

## 🚀 Getting Started

### Prerequisites
- **Node.js** (v18 or higher)
- **Python** (v3.8 or higher)
- **npm** or **yarn** for package management
- **Git** for version control

### Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd insight-flow
```

2. **Install frontend dependencies:**
```bash
cd frontend
npm install
```

3. **Install backend dependencies:**
```bash
cd ../backend
pip install -r requirements.txt
```

### Running the Application

1. **Start the backend server:**
```bash
cd backend
uvicorn main:app --reload
```
The API will be available at `http://localhost:8000`

2. **Start the frontend development server:**
```bash
cd frontend
npm run dev
```
The application will be available at `http://localhost:3000`

## 📚 API Documentation

Once the backend server is running, you can access the interactive API documentation at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 🛠 Development

### Frontend Development Commands
```bash
npm run dev      # Start development server with hot reload
npm run build    # Build for production
npm run start    # Start production server
npm run lint     # Run ESLint for code quality checks
```

### Backend Development
The backend uses FastAPI with automatic reloading when code changes are made. The CORS middleware is configured to allow requests from `http://localhost:3000` (the frontend development server).

### Database Setup
The backend uses SQLAlchemy for database operations. Configure your database connection in the `backend/database.py` file.

## 📊 Project Architecture

### Frontend Architecture
- **App Router**: Utilizes Next.js 13+ App Router for better routing and layouts
- **Component-Based**: Modular components for reusability and maintainability
- **State Management**: Centralized state management using Zustand
- **API Layer**: Separated API service layer for clean data fetching

### Backend Architecture
- **FastAPI**: Modern async web framework with automatic API documentation
- **SQLAlchemy**: ORM for database operations with model-based approach
- **Router Pattern**: Modular router structure for organized API endpoints
- **CORS Configuration**: Properly configured for frontend-backend communication

## 🔄 Development Workflow

1. **Feature Development**: Create feature branches from `main`
2. **Code Review**: All changes require pull request review
3. **Testing**: Ensure both frontend and backend tests pass
4. **Documentation**: Update documentation for new features
5. **Deployment**: Automated deployment after merge to main

## 📈 Project Status

This project is currently in active development. The frontend provides a modern Next.js application with Tailwind CSS styling, and the backend offers a robust FastAPI setup with proper CORS middleware configuration for seamless frontend-backend communication.

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Commit your changes** (`git commit -m 'Add some amazing feature'`)
4. **Push to the branch** (`git push origin feature/amazing-feature`)
5. **Open a Pull Request** with a detailed description of changes

### Code Style Guidelines
- Follow ESLint configuration for frontend code
- Use PEP 8 for Python backend code
- Write meaningful commit messages
- Add tests for new features
- Update documentation as needed

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:
- Create an issue in the GitHub repository
- Check the API documentation at `http://localhost:8000/docs`
- Review the frontend documentation in `frontend/README.md`

---

**Built with ❤️ using modern web technologies**