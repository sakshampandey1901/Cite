#!/bin/bash
# Backend Startup Script
# This ensures the backend starts with the correct virtual environment

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting Cognitive Assistant Backend...${NC}"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo -e "${RED}Error: Virtual environment not found!${NC}"
    echo "Please run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
source venv/bin/activate

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Please create .env file with required configuration"
    exit 1
fi

# Check if SECRET_KEY is set
if ! grep -q "SECRET_KEY=" .env; then
    echo -e "${RED}Warning: SECRET_KEY not found in .env${NC}"
    echo "Generating new SECRET_KEY..."
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    echo "SECRET_KEY=$SECRET_KEY" >> .env
    echo -e "${GREEN}SECRET_KEY generated and added to .env${NC}"
fi

# Kill any existing backend process on port 8000
echo -e "${BLUE}Checking for existing process on port 8000...${NC}"
EXISTING_PID=$(lsof -ti :8000 || true)
if [ ! -z "$EXISTING_PID" ]; then
    echo -e "${BLUE}Killing existing process (PID: $EXISTING_PID)...${NC}"
    kill -9 $EXISTING_PID 2>/dev/null || true
    sleep 1
fi

# Start the backend server
echo -e "${GREEN}Starting uvicorn server...${NC}"
echo -e "${BLUE}Log file: /tmp/backend.log${NC}"
echo ""

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Note: If you want to run in background, use:
# nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/backend.log 2>&1 &
# echo -e "${GREEN}Backend started! PID: $!${NC}"
# echo -e "${BLUE}View logs: tail -f /tmp/backend.log${NC}"