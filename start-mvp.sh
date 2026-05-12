#!/bin/bash
# KSERC DSS MVP Startup Script

echo "🚀 Starting KSERC Decision Support System MVP..."

# Check if Docker is available
if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
    echo "📦 Using Docker Compose..."
    docker-compose up --build
else
    echo "🐍 Docker not found, starting locally..."
    
    # Start backend
    echo "🔧 Starting backend..."
    cd backend
    python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
    
    # Wait for backend to start
    sleep 3
    
    # Start frontend
    echo "🎨 Starting frontend..."
    cd ../frontend
    npm install
    npm run dev &
    FRONTEND_PID=$!
    
    echo "✅ MVP started!"
    echo "📊 Backend: http://localhost:8000"
    echo "🖥️  Frontend: http://localhost:5173"
    echo "📚 API Docs: http://localhost:8000/docs"
    
    # Wait for user to stop
    read -p "Press Enter to stop..."
    
    # Cleanup
    kill $BACKEND_PID $FRONTEND_PID
fi
