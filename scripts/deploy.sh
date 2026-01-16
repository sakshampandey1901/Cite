#!/bin/bash
# Master deployment script for production setup

set -e  # Exit on error

echo "============================================================"
echo "Production Deployment Setup"
echo "============================================================"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in production mode
echo -e "\n${YELLOW}Checking environment...${NC}"
if grep -q "ENVIRONMENT=production" "$BACKEND_DIR/.env" 2>/dev/null; then
    echo -e "${GREEN}✅ Environment set to production${NC}"
else
    echo -e "${RED}❌ ENVIRONMENT not set to production in backend/.env${NC}"
    read -p "Continue anyway? (y/n): " confirm
    if [[ $confirm != "y" ]]; then
        exit 1
    fi
fi

# Step 1: Install Python dependencies
echo -e "\n============================================================"
echo "Step 1: Installing Python dependencies"
echo "============================================================"

cd "$BACKEND_DIR"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt --quiet

echo -e "${GREEN}✅ Dependencies installed${NC}"

# Step 2: Download embedding models
echo -e "\n============================================================"
echo "Step 2: Downloading embedding models"
echo "============================================================"

python3 "$SCRIPT_DIR/download_models.py"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Embedding models ready${NC}"
else
    echo -e "${RED}❌ Failed to download models${NC}"
    exit 1
fi

# Step 3: Initialize database
echo -e "\n============================================================"
echo "Step 3: Initializing database tables"
echo "============================================================"

python3 "$SCRIPT_DIR/init_database.py"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Database initialized${NC}"
else
    echo -e "${RED}❌ Database initialization failed${NC}"
    exit 1
fi

# Step 4: Initialize Pinecone
echo -e "\n============================================================"
echo "Step 4: Initializing Pinecone index"
echo "============================================================"

python3 "$SCRIPT_DIR/init_pinecone.py"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Pinecone initialized${NC}"
else
    echo -e "${RED}❌ Pinecone initialization failed${NC}"
    exit 1
fi

# Step 5: Redis setup (optional)
echo -e "\n============================================================"
echo "Step 5: Redis setup (optional)"
echo "============================================================"

read -p "Do you want to set up Redis for rate limiting? (y/n): " setup_redis

if [[ $setup_redis == "y" ]]; then
    bash "$SCRIPT_DIR/setup_redis.sh"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Redis configured${NC}"
    else
        echo -e "${YELLOW}⚠️  Redis setup incomplete - rate limiting will be disabled${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Skipping Redis - rate limiting will be disabled${NC}"
fi

# Step 6: Frontend build (if needed)
echo -e "\n============================================================"
echo "Step 6: Frontend build"
echo "============================================================"

read -p "Build frontend? (y/n): " build_frontend

if [[ $build_frontend == "y" ]]; then
    cd "$PROJECT_ROOT"

    if [ ! -d "node_modules" ]; then
        echo "Installing frontend dependencies..."
        npm install
    fi

    echo "Building frontend..."
    npm run build

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Frontend built successfully${NC}"
        echo "Output directory: $PROJECT_ROOT/dist"
    else
        echo -e "${RED}❌ Frontend build failed${NC}"
        exit 1
    fi
else
    echo "Skipping frontend build"
fi

# Step 7: Final checks
echo -e "\n============================================================"
echo "Final Configuration Checklist"
echo "============================================================"

echo -e "\n${YELLOW}Please verify the following:${NC}"
echo ""
echo "1. Credentials rotated:"
echo "   ❓ Have you rotated SECRET_KEY? (new value in .env)"
echo "   ❓ Using production Supabase project?"
echo "   ❓ Using production Pinecone API key?"
echo "   ❓ Using production Groq API key?"
echo ""
echo "2. Configuration:"
echo "   ❓ ENVIRONMENT=production in backend/.env"
echo "   ❓ CORS_ORIGINS set to production domains"
echo "   ❓ Sentry DSN configured (optional)"
echo ""
echo "3. Services ready:"
echo "   ✓ Database tables initialized"
echo "   ✓ Pinecone index created"
echo "   ✓ Embedding models downloaded"
echo "   $([ "$setup_redis" == "y" ] && echo "✓" || echo "⚠️ ") Redis configured"
echo ""

read -p "All checks complete? Ready to start server? (y/n): " ready

if [[ $ready == "y" ]]; then
    echo -e "\n============================================================"
    echo "Starting Production Server"
    echo "============================================================"
    echo ""
    echo "Starting backend with gunicorn..."
    echo ""

    cd "$BACKEND_DIR"

    # Check if gunicorn is installed
    if ! command -v gunicorn &> /dev/null; then
        echo "Installing gunicorn..."
        pip install gunicorn
    fi

    echo "Server will start on port 8000"
    echo "Press Ctrl+C to stop"
    echo ""

    gunicorn app.main:app \
        --workers 4 \
        --worker-class uvicorn.workers.UvicornWorker \
        --bind 0.0.0.0:8000 \
        --timeout 120 \
        --access-logfile - \
        --error-logfile -
else
    echo -e "\n${YELLOW}Deployment setup complete but server not started${NC}"
    echo ""
    echo "To start the server manually:"
    echo "  cd $BACKEND_DIR"
    echo "  source venv/bin/activate"
    echo "  gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000"
    echo ""
fi

echo -e "\n============================================================"
echo -e "${GREEN}✅ Deployment setup complete!${NC}"
echo "============================================================"
