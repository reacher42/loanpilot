#!/bin/bash
# Quick Start Script for LoanPilot Docker Deployment

set -e

echo "========================================"
echo "LoanPilot Docker Quick Start"
echo "========================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠ .env file not found!"
    echo ""
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "✓ Created .env file"
    echo ""
    echo "⚠ IMPORTANT: Edit .env and add your ANTHROPIC_API_KEY"
    echo "   nano .env"
    echo ""
    read -p "Press Enter after updating the API key..."
fi

# Check if API key is set
if grep -q "your_api_key_here" .env; then
    echo "⚠ WARNING: ANTHROPIC_API_KEY still has placeholder value"
    echo "   Please update .env with a valid API key"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "Starting LoanPilot with Docker Compose..."
echo ""

# Create directories if needed
mkdir -p backups web-app/logs

# Build and start
docker-compose up -d --build

echo ""
echo "✓ LoanPilot is starting..."
echo ""
echo "Waiting for application to be ready..."
sleep 5

# Check status
docker-compose ps

echo ""
echo "========================================"
echo "✓ Deployment Complete!"
echo "========================================"
echo ""
echo "Access the application:"
echo "  Local: http://localhost:8000"
echo "  Network: http://$(hostname -I | awk '{print $1}'):8000"
echo ""
echo "Useful commands:"
echo "  View logs:    docker-compose logs -f"
echo "  Stop app:     docker-compose stop"
echo "  Restart app:  docker-compose restart"
echo "  Remove app:   docker-compose down"
echo ""
