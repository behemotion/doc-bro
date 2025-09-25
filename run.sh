#!/bin/bash
# Quick start script for DocBro

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "==================================="
echo "     Starting DocBro Services"
echo "==================================="
echo

# Start Docker services
echo "Starting Docker services..."
if docker-compose -f docker/docker-compose.yml up -d 2>/dev/null; then
    echo -e "${GREEN}✓ Docker services started${NC}"
else
    echo -e "${YELLOW}⚠ Docker services not available${NC}"
fi

# Check Ollama
echo "Checking Ollama..."
if ! curl -s http://localhost:11434/api/version &> /dev/null; then
    echo -e "${YELLOW}Starting Ollama in background...${NC}"
    nohup ollama serve > /dev/null 2>&1 &
    sleep 2
fi
echo -e "${GREEN}✓ Ollama ready${NC}"

# Show status
echo
echo "Running status check..."
python3 -m src.cli.main status

echo
echo "==================================="
echo -e "${GREEN}DocBro is ready!${NC}"
echo "==================================="
echo
echo "Quick commands:"
echo "  docbro --help                    # Show all commands"
echo "  docbro status                    # Check system status"
echo "  docbro list                      # List projects"
echo "  docbro create <name> --url <url> # Create project"
echo "  docbro crawl <name>              # Crawl documentation"
echo "  docbro search <query>            # Search documentation"
echo "  docbro serve                     # Start MCP server"
echo