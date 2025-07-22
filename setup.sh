#!/bin/bash
# Open Science Tracker - Initial Setup Script
# This script sets up the virtual environment and installs all dependencies

echo "🔧 Open Science Tracker - Initial Setup"
echo "========================================"
echo ""

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Create virtual environment if it doesn't exist
if [ ! -d "ost_env" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv ost_env
    echo "✅ Virtual environment created!"
else
    echo "📦 Virtual environment already exists."
fi

# Activate virtual environment
echo "🚀 Activating virtual environment..."
source ost_env/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📥 Installing dependencies from requirements.txt..."
pip install -r requirements.txt

echo ""
echo "✅ Setup completed successfully!"
echo ""
echo "🚀 Next steps:"
echo "   1. Run: ./activate.sh"
echo "   2. Start Django server: python manage.py runserver"
echo "   3. Open http://localhost:8000 in your browser"
echo ""
echo "📚 Documentation: See README.md for detailed instructions" 