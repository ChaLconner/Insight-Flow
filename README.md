# Insight-Flow Development Setup

## Quick Start

### Backend Setup

1. **Start the backend server with proper host binding:**
   ```bash
   cd backend
   python start.py
   ```
   
   This will start the server on `http://0.0.0.0:8000` which makes it accessible from the frontend.

2. **Or start manually (alternative method):**
   ```bash
   cd backend
   python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

### Frontend Setup

1. **Start the frontend development server:**
   ```bash
   cd frontend
   npm run dev
   ```

## Troubleshooting Network Errors

If you encounter "Network Error" when fetching project tasks:

### Most Common Cause: Backend Server Binding

The backend server must bind to `0.0.0.0` instead of `127.0.0.1` to be accessible from the frontend.

**Check if backend is properly bound:**
```bash
netstat -an | findstr :8000
```

You should see:
```
TCP    0.0.0.0:8000           0.0.0.0:0              LISTENING
```

NOT:
```
TCP    127.0.0.1:8000         0.0.0.0:0              LISTENING
```

### Solution

Always start the backend using the provided `start.py` script or with the `--host 0.0.0.0` flag.

### Additional Checks

1. **Test API directly:** Open `http://localhost:8000/minimal-test` in your browser
2. **Check CORS configuration:** Ensure frontend origin is in the allowed origins list
3. **Verify authentication:** Check that JWT tokens are valid and not expired

## Environment Configuration

### Backend (.env)
```
HOST=0.0.0.0
PORT=8000
RELOAD=true
DATABASE_URL=your-database-url
SECRET_KEY=your-secret-key
```

### Frontend (.env.local)
```
NEXT_PUBLIC_API_URL=http://localhost:8000