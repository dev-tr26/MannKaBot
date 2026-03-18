#!/bin/bash
# ============================================
# MannKaBot - Setup Script
# ============================================

echo "🎙️  MannKaBot Voice AI Journal - Setup"
echo "========================================"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required. Please install Python 3.9+"
    exit 1
fi

# Check MongoDB
if ! command -v mongod &> /dev/null; then
    echo "⚠️  MongoDB not found. Please install MongoDB:"
    echo "   macOS: brew install mongodb-community"
    echo "   Ubuntu: sudo apt install mongodb"
    echo "   Or use MongoDB Atlas: https://www.mongodb.com/atlas"
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate
source venv/bin/activate 2>/dev/null || . venv/Scripts/activate 2>/dev/null

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Copy .env if not exists
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚙️  Created .env file - please configure your API keys!"
    echo ""
    echo "   Required keys:"
    echo "   - GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET (https://console.cloud.google.com)"
    echo "   - SARVAM_API_KEY (https://app.sarvam.ai)"
    echo ""
fi

echo "✅ Setup complete!"
echo ""
echo "🚀 To run:"
echo "   source venv/bin/activate"
echo "   cd backend && python main.py"
echo ""
echo "🌐 Then open: http://localhost:8000"