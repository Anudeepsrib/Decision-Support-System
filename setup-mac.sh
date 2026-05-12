#!/bin/bash
# KSERC DSS MVP Setup Script for macOS

set -e

echo "🍎 Setting up KSERC DSS MVP for macOS..."

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "📦 Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
    echo "✅ Homebrew is already installed"
fi

# Install Python 3 if not present
if ! command -v python3 &> /dev/null; then
    echo "🐍 Installing Python 3..."
    brew install python
else
    echo "✅ Python 3 is already installed"
fi

# Install Node.js if not present
if ! command -v node &> /dev/null; then
    echo "📦 Installing Node.js..."
    brew install node
else
    echo "✅ Node.js is already installed"
fi

# Install system dependencies for WeasyPrint
echo "📦 Installing system dependencies for PDF generation..."
brew install pango gdk-pixbuf libffi cairo

# Create clean virtual environment
if [ ! -d "venv-mvp" ]; then
    echo "🐍 Creating clean Python virtual environment..."
    python3 -m venv venv-mvp
else
    echo "✅ Clean virtual environment already exists"
fi

# Activate virtual environment and install Python dependencies
echo "📚 Installing Python dependencies..."
source venv-mvp/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Install Node.js dependencies
echo "📚 Installing Node.js dependencies..."
cd frontend
npm install
cd ..

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p output mvp_uploads data

echo ""
echo "🎉 Setup complete!"
echo ""
echo "🚀 To start the MVP:"
echo "   ./start-mvp-mac.sh"
echo ""
echo "🛠️  Or use Makefile:"
echo "   make start"
echo ""
