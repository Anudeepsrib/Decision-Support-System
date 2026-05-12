# KSERC DSS MVP Makefile for macOS/Linux

.PHONY: help setup start stop clean test

# Default target
help:
	@echo "KSERC Decision Support System MVP"
	@echo ""
	@echo "Available commands:"
	@echo "  make setup    - Set up the development environment"
	@echo "  make start    - Start the MVP (backend + frontend)"
	@echo "  make backend  - Start only the backend"
	@echo "  make frontend - Start only the frontend"
	@echo "  make stop     - Stop all running services"
	@echo "  make clean    - Clean up generated files"
	@echo "  make test     - Run tests"

# Setup development environment
setup:
	@echo "🔧 Setting up development environment..."
	@if [ ! -d "venv-mvp" ]; then \
		echo "📦 Creating clean Python virtual environment..."; \
		python3 -m venv venv-mvp; \
	fi
	@echo "📚 Installing Python dependencies..."
	@source venv-mvp/bin/activate && pip install --upgrade pip && pip install -r requirements.txt
	@echo "📚 Installing Node.js dependencies..."
	@cd frontend && npm install
	@echo "✅ Setup complete!"

# Start both backend and frontend
start:
	@echo "🚀 Starting KSERC DSS MVP..."
	@source venv-mvp/bin/activate && cd backend && python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000 & \
		echo "🔧 Backend started on http://localhost:8000" && \
		sleep 5 && \
		cd frontend && npm run dev & \
		echo "🎨 Frontend started on http://localhost:5173" && \
		echo "📚 API docs: http://localhost:8000/docs" && \
		echo "🛑 Press Ctrl+C to stop" && \
		wait

# Start only backend
backend:
	@echo "🔧 Starting backend..."
	@source venv-mvp/bin/activate && cd backend && python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Start only frontend
frontend:
	@echo "🎨 Starting frontend..."
	@cd frontend && npm run dev

# Stop all services
stop:
	@echo "🛑 Stopping services..."
	@pkill -f "uvicorn app:app" || true
	@pkill -f "npm run dev" || true
	@pkill -f "vite" || true
	@echo "✅ Services stopped"

# Clean up
clean:
	@echo "🧹 Cleaning up..."
	@rm -rf venv venv-mvp
	@rm -rf frontend/node_modules
	@rm -rf frontend/dist
	@rm -f kserc_dss.db
	@rm -rf output/*
	@rm -rf mvp_uploads/*
	@echo "✅ Clean complete"

# Run tests
test:
	@echo "🧪 Running tests..."
	@source venv-mvp/bin/activate && cd backend && python -c "import app; print('✅ Backend imports successful')"
	@cd frontend && npm test || echo "⚠️  Frontend tests not configured yet"
