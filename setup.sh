#!/bin/bash

# Setup script for Cognitive Assistant
# This script automates the initial setup process

set -e  # Exit on error

echo "=================================="
echo "Cognitive Assistant Setup"
echo "=================================="
echo ""

# Check prerequisites
echo "Checking prerequisites..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✓ Python $PYTHON_VERSION found"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed"
    exit 1
fi

NODE_VERSION=$(node --version)
echo "✓ Node.js $NODE_VERSION found"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed"
    exit 1
fi

DOCKER_VERSION=$(docker --version | cut -d' ' -f3)
echo "✓ Docker $DOCKER_VERSION found"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "Error: Docker Compose is not installed"
    exit 1
fi

echo "✓ Docker Compose found"
echo ""

# Backend setup
echo "Setting up backend..."
cd backend

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating backend .env file..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Edit backend/.env and add your API keys:"
    echo "   - GROQ_API_KEY"
    echo "   - PINECONE_API_KEY"
    echo ""
fi

cd ..

# Frontend setup
echo "Setting up frontend..."

# Install Node dependencies
echo "Installing Node.js dependencies..."
npm install --silent

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating frontend .env file..."
    cp .env.example .env
fi

echo ""
echo "=================================="
echo "Setup Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Add your API keys to backend/.env:"
echo "   nano backend/.env"
echo ""
echo "2. Start the database services:"
echo "   cd backend && docker-compose up -d postgres redis"
echo ""
echo "3. Start the backend (in one terminal):"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   python -m app.main"
echo ""
echo "4. Start the frontend (in another terminal):"
echo "   npm run dev"
echo ""
echo "5. Open http://localhost:5173 in your browser"
echo ""
echo "For more details, see IMPLEMENTATION_GUIDE.md"
echo ""
