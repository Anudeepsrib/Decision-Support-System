# macOS Setup Guide

This guide is specifically for macOS users setting up the KSERC Decision Support System MVP.

## 🍎 Prerequisites

- macOS 10.15+ (Catalina or later)
- Xcode Command Line Tools
- Admin access for installing system dependencies

## 🚀 One-Command Setup

```bash
# Clone the repository
git clone <repository-url>
cd Decision-Support-System

# Run the setup script (installs everything)
./setup-mac.sh

# Start the MVP
./start-mvp-mac.sh
```

## 📋 What the Setup Script Does

### System Dependencies (via Homebrew)
- Python 3 (if not installed)
- Node.js (if not installed)
- WeasyPrint dependencies: pango, gdk-pixbuf, libffi, cairo

### Python Environment
- Creates virtual environment (`venv/`)
- Installs all Python packages from `requirements.txt`

### Frontend Environment
- Installs Node.js packages in `frontend/`
- Sets up Vite + React development environment

## 🛠️ Manual Setup (Alternative)

If you prefer manual setup:

### 1. Install System Dependencies
```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python node pango gdk-pixbuf libffi cairo
```

### 2. Setup Python Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Setup Frontend
```bash
cd frontend
npm install
cd ..
```

### 4. Create Directories
```bash
mkdir -p output mvp_uploads data
```

## 🎯 Start the Application

### Option 1: Startup Script
```bash
./start-mvp-mac.sh
```

### Option 2: Makefile
```bash
make start
```

### Option 3: Manual (Two Terminals)

**Terminal 1 (Backend):**
```bash
source venv/bin/activate
cd backend
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 (Frontend):**
```bash
cd frontend
npm run dev
```

## 📱 Access Points

Once running, access the application at:
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 🔧 Common Issues & Solutions

### Issue: "command not found: python3"
**Solution**: Install Python via Homebrew:
```bash
brew install python
```

### Issue: WeasyPrint installation fails
**Solution**: Install system dependencies:
```bash
brew install pango gdk-pixbuf libffi cairo
```

### Issue: Node.js not found
**Solution**: Install Node.js via Homebrew:
```bash
brew install node
```

### Issue: Permission denied on scripts
**Solution**: Make scripts executable:
```bash
chmod +x *.sh
```

### Issue: Port already in use
**Solution**: Kill existing processes:
```bash
# Kill backend
pkill -f uvicorn

# Kill frontend
pkill -f vite
```

## 🛑 Stop the Application

### Using Ctrl+C
If you started with `./start-mvp-mac.sh`, press `Ctrl+C` in the terminal.

### Using Makefile
```bash
make stop
```

### Manual Cleanup
```bash
pkill -f uvicorn
pkill -f vite
```

## 🧹 Clean Up

To completely reset the environment:
```bash
make clean
```

This removes:
- Virtual environment (`venv/`)
- Node modules (`frontend/node_modules/`)
- Database files (`*.db`)
- Generated files (`output/`, `mvp_uploads/`)

## 📝 Development Tips

### Backend Development
- Backend auto-reloads on file changes
- Database is SQLite (file-based)
- Logs are shown in the terminal

### Frontend Development
- Frontend hot-reloads on file changes
- Tailwind CSS is already configured
- TypeScript is enabled

### API Testing
- Use http://localhost:8000/docs for interactive API testing
- Health check: http://localhost:8000/health

## 🆘 Troubleshooting

If you encounter issues:

1. **Check system dependencies**: Ensure all Homebrew packages are installed
2. **Verify Python version**: Should be Python 3.8+
3. **Check Node.js version**: Should be Node.js 16+
4. **Clear caches**: 
   ```bash
   npm cache clean --force
   pip cache purge
   ```
5. **Re-run setup**: `./setup-mac.sh`

## 📞 Support

For additional help:
- Check the main README: `README-MVP.md`
- Review API documentation: http://localhost:8000/docs
- Check application logs in terminal output
