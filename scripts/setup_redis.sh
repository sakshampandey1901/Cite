#!/bin/bash
# Redis installation and setup script

echo "============================================================"
echo "Redis Setup for Rate Limiting"
echo "============================================================"

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
else
    OS="unknown"
fi

echo -e "\nDetected OS: $OS"

# Installation instructions
if [ "$OS" == "macos" ]; then
    echo -e "\n1. Installing Redis via Homebrew..."

    # Check if Homebrew is installed
    if ! command -v brew &> /dev/null; then
        echo "❌ Homebrew not found. Install from https://brew.sh"
        exit 1
    fi

    # Install Redis
    if command -v redis-server &> /dev/null; then
        echo "✅ Redis already installed"
    else
        echo "Installing Redis..."
        brew install redis
    fi

    echo -e "\n2. Starting Redis..."
    brew services start redis

    echo -e "\n3. Verifying Redis is running..."
    sleep 2
    if redis-cli ping &> /dev/null; then
        echo "✅ Redis is running"
    else
        echo "⚠️  Redis may not be running. Try: brew services restart redis"
    fi

elif [ "$OS" == "linux" ]; then
    echo -e "\n=== Linux Installation ==="
    echo ""
    echo "Option 1: Using Docker (Recommended)"
    echo "  docker run -d --name redis --restart unless-stopped -p 6379:6379 redis:7-alpine"
    echo ""
    echo "Option 2: Using apt (Ubuntu/Debian)"
    echo "  sudo apt update"
    echo "  sudo apt install redis-server -y"
    echo "  sudo systemctl enable redis-server"
    echo "  sudo systemctl start redis-server"
    echo ""
    echo "Option 3: Using yum (CentOS/RHEL)"
    echo "  sudo yum install redis -y"
    echo "  sudo systemctl enable redis"
    echo "  sudo systemctl start redis"
    echo ""
    read -p "Choose option (1/2/3): " choice

    case $choice in
        1)
            echo "Starting Redis with Docker..."
            docker run -d --name redis --restart unless-stopped -p 6379:6379 redis:7-alpine
            echo "✅ Redis started in Docker"
            ;;
        2)
            echo "Installing with apt..."
            sudo apt update
            sudo apt install redis-server -y
            sudo systemctl enable redis-server
            sudo systemctl start redis-server
            echo "✅ Redis installed and started"
            ;;
        3)
            echo "Installing with yum..."
            sudo yum install redis -y
            sudo systemctl enable redis
            sudo systemctl start redis
            echo "✅ Redis installed and started"
            ;;
        *)
            echo "Invalid choice"
            exit 1
            ;;
    esac

else
    echo "❌ Unsupported OS. Please install Redis manually:"
    echo ""
    echo "Docker (All OS):"
    echo "  docker run -d --name redis --restart unless-stopped -p 6379:6379 redis:7-alpine"
    echo ""
    echo "Or use a cloud-hosted Redis:"
    echo "  - Upstash: https://upstash.com (10k commands/day free)"
    echo "  - Redis Cloud: https://redis.com/cloud (30MB free)"
    echo ""
    exit 1
fi

# Verify installation
echo -e "\n============================================================"
echo "Verification"
echo "============================================================"

if command -v redis-cli &> /dev/null; then
    echo -e "\n✅ redis-cli found"

    # Test connection
    if redis-cli ping &> /dev/null; then
        echo "✅ Redis connection successful"

        # Show Redis info
        echo -e "\nRedis Info:"
        redis-cli --version
        echo "Redis URL: redis://localhost:6379/0"

        echo -e "\n============================================================"
        echo "✅ Redis setup complete!"
        echo "============================================================"
        echo ""
        echo "Rate limiting is now ENABLED"
        echo ""
        echo "Useful commands:"
        echo "  - Check status: redis-cli ping"
        echo "  - Monitor activity: redis-cli monitor"
        echo "  - View keys: redis-cli keys '*'"

        if [ "$OS" == "macos" ]; then
            echo "  - Stop Redis: brew services stop redis"
            echo "  - Restart Redis: brew services restart redis"
        fi

        exit 0
    else
        echo "⚠️  Redis installed but not running"
        echo ""
        if [ "$OS" == "macos" ]; then
            echo "Try: brew services restart redis"
        else
            echo "Try: sudo systemctl restart redis"
        fi
        exit 1
    fi
else
    echo "❌ redis-cli not found in PATH"
    echo ""
    echo "If using Docker, Redis is running but CLI is in container."
    echo "Test with: docker exec redis redis-cli ping"
    exit 1
fi
