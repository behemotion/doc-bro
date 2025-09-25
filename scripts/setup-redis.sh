#!/bin/bash
# Redis local installation script for DocBro (optional - Docker preferred)

set -e

echo "📦 Setting up Redis for DocBro (Local Installation - Optional)..."
echo "⚠️  Note: DocBro uses Docker for Redis by default. This script is for local development only."

# Check if Redis is already installed
if command -v redis-server &> /dev/null; then
    echo "✅ Redis is already installed"
    redis-server --version
else
    echo "📦 Installing Redis..."

    # Detect OS and install accordingly
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install redis
        else
            echo "❌ Please install Homebrew first or use Docker setup"
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux - detect distribution
        if command -v apt-get &> /dev/null; then
            sudo apt-get update
            sudo apt-get install -y redis-server
        elif command -v yum &> /dev/null; then
            sudo yum install -y redis
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y redis
        else
            echo "❌ Unsupported Linux distribution. Please install Redis manually or use Docker."
            exit 1
        fi
    else
        echo "❌ Unsupported OS. Please use Docker setup or install Redis manually."
        exit 1
    fi
fi

# Configure Redis for DocBro
echo "⚙️  Configuring Redis..."
redis_conf="/usr/local/etc/redis/redis.conf"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    redis_conf="/etc/redis/redis.conf"
fi

if [ -f "$redis_conf" ]; then
    echo "Enabling persistence and setting up for DocBro..."
    # Backup original config
    sudo cp "$redis_conf" "$redis_conf.backup"

    # Enable AOF persistence
    sudo sed -i 's/appendonly no/appendonly yes/' "$redis_conf"
    sudo sed -i 's/appendfsync everysec/appendfsync everysec/' "$redis_conf"
else
    echo "⚠️  Redis config file not found. Using default settings."
fi

# Start Redis service
echo "🚀 Starting Redis service..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    brew services start redis
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    sudo systemctl start redis-server
    sudo systemctl enable redis-server
fi

# Test Redis connection
echo "🧪 Testing Redis connection..."
sleep 2
if redis-cli ping | grep -q "PONG"; then
    echo "✅ Redis setup complete!"
    echo "Redis is running on localhost:6379"
else
    echo "❌ Redis connection failed. Please check the installation."
    exit 1
fi

echo "🎉 Redis is ready for DocBro!"
echo "💡 Tip: DocBro uses Docker by default. Run 'docker-compose up -d' for production setup."