#!/bin/bash
# KSERC DSS MVP Startup Script for macOS

set -e  # Exit on any error

echo "🚀 Starting KSERC Decision Support System MVP on macOS..."

# Check Python installation
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    echo "Please install Python 3: https://www.python.org/downloads/"
    exit 1
fi

# Check Node.js installation
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is required but not installed."
    echo "Please install Node.js: https://nodejs.org/"
    exit 1
fi

# Create clean virtual environment if it doesn't exist
if [ ! -d "venv-mvp" ]; then
    echo "📦 Creating clean Python virtual environment..."
    python3 -m venv venv-mvp
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv-mvp/bin/activate

# Install Python dependencies
echo "📚 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Start backend
echo "🔧 Starting backend..."
cd backend
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 5

# Test backend health
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Backend started successfully!"
else
    echo "❌ Backend failed to start"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

# Install Node.js dependencies
echo "📚 Installing Node.js dependencies..."
cd ../frontend
npm install

# Start frontend
echo "🎨 Starting frontend..."
npm run dev &
FRONTEND_PID=$!

# Wait for frontend to start
echo "⏳ Waiting for frontend to start..."
sleep 3

echo ""
echo "🎉 MVP started successfully!"
echo ""
echo "📱 Access Points:"
echo "   Frontend: http://localhost:5173"
echo "   Backend:  http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "🛑 Press Ctrl+C to stop all services"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "👋 All services stopped. Goodbye!"
    exit 0
}

# Set up trap to catch Ctrl+C
trap cleanup INT

# Wait for user to stop
wait
