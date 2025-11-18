#!/bin/bash
# ============================================
# LoanPilot Image Export and Packaging Script
# Creates distribution package for customer delivery
# ============================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
IMAGE_NAME="loanpilot"
VERSION="${VERSION:-1.0.0}"
CUSTOMER_ID="${CUSTOMER_ID:-DEMO}"
OUTPUT_DIR="./distribution"

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}LoanPilot Image Export & Packaging${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --customer)
            CUSTOMER_ID="$2"
            shift 2
            ;;
        --version)
            VERSION="$2"
            shift 2
            ;;
        --output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --customer ID     Customer identifier (default: DEMO)"
            echo "  --version VER     Version number (default: 1.0.0)"
            echo "  --output DIR      Output directory (default: ./distribution)"
            echo "  --help            Show this help message"
            echo ""
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

IMAGE_TAG="${IMAGE_NAME}:${CUSTOMER_ID}-${VERSION}"
PACKAGE_NAME="loanpilot-${CUSTOMER_ID}-v${VERSION}"
PACKAGE_DIR="${OUTPUT_DIR}/${PACKAGE_NAME}"

echo -e "${GREEN}Export Configuration:${NC}"
echo "  Customer ID: ${CUSTOMER_ID}"
echo "  Version: ${VERSION}"
echo "  Image Tag: ${IMAGE_TAG}"
echo "  Package: ${PACKAGE_NAME}"
echo ""

# Check if image exists
if ! docker images "${IMAGE_TAG}" --format "{{.ID}}" | grep -q .; then
    echo -e "${RED}❌ Image not found: ${IMAGE_TAG}${NC}"
    echo -e "${YELLOW}   Run: ./build/build_production.sh --customer ${CUSTOMER_ID} --version ${VERSION}${NC}"
    exit 1
fi

# Create output directory
mkdir -p "${PACKAGE_DIR}"
echo -e "${GREEN}✓${NC} Created package directory: ${PACKAGE_DIR}"

# Export Docker image
echo ""
echo -e "${BLUE}📦 Exporting Docker image...${NC}"
docker save "${IMAGE_TAG}" | gzip > "${PACKAGE_DIR}/${PACKAGE_NAME}.tar.gz"

IMAGE_SIZE_MB=$(du -m "${PACKAGE_DIR}/${PACKAGE_NAME}.tar.gz" | cut -f1)
echo -e "${GREEN}✓${NC} Image exported: ${PACKAGE_NAME}.tar.gz (${IMAGE_SIZE_MB}MB)"

# Generate SHA256 checksum
echo ""
echo -e "${BLUE}🔐 Generating checksums...${NC}"
cd "${PACKAGE_DIR}"
sha256sum "${PACKAGE_NAME}.tar.gz" > SHA256SUMS
cd - > /dev/null
echo -e "${GREEN}✓${NC} Checksum generated: SHA256SUMS"

# Create minimal docker-compose.yml for customer
echo ""
echo -e "${BLUE}📝 Creating customer files...${NC}"

cat > "${PACKAGE_DIR}/docker-compose.yml" << EOF
version: '3.8'

services:
  loanpilot:
    image: ${IMAGE_TAG}
    container_name: loanpilot-app
    ports:
      - "8000:8000"
    volumes:
      - ./loanpilot.db:/app/loanpilot.db
      - ./backups:/app/backups
      - ./logs:/app/web-app/logs
    environment:
      - ANTHROPIC_API_KEY=\${ANTHROPIC_API_KEY}
    env_file:
      - .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

networks:
  default:
    name: loanpilot-network
EOF

echo -e "${GREEN}✓${NC} Created: docker-compose.yml"

# Create .env.example
cat > "${PACKAGE_DIR}/.env.example" << EOF
# LoanPilot Configuration
# Replace with your actual Anthropic API key
ANTHROPIC_API_KEY=your-anthropic-api-key-here
EOF

echo -e "${GREEN}✓${NC} Created: .env.example"

# Copy sample data
mkdir -p "${PACKAGE_DIR}/data/v3"
if [ -f "data/v3/Non-QM_Matrix.xlsx - Attributes.tsv" ]; then
    cp "data/v3/Non-QM_Matrix.xlsx - Attributes.tsv" "${PACKAGE_DIR}/data/v3/"
    echo -e "${GREEN}✓${NC} Copied: sample data"
fi

# Create installation script
cat > "${PACKAGE_DIR}/install.sh" << 'INSTALL_EOF'
#!/bin/bash
set -e

echo "=========================================="
echo "LoanPilot Installation"
echo "=========================================="
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not installed"
    echo "   Install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

echo "✓ Docker installed"

# Check docker-compose
if ! docker compose version &> /dev/null 2>&1 && ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not installed"
    exit 1
fi

echo "✓ Docker Compose installed"
echo ""

# Load image
IMAGE_FILE=$(ls loanpilot-*.tar.gz | head -1)
if [ -z "$IMAGE_FILE" ]; then
    echo "❌ No image file found (loanpilot-*.tar.gz)"
    exit 1
fi

echo "📦 Loading Docker image: $IMAGE_FILE"
echo "   This may take a few minutes..."
docker load -i "$IMAGE_FILE"

echo ""
echo "✓ Image loaded successfully"
echo ""

# Setup environment
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your ANTHROPIC_API_KEY"
    echo "   Run: nano .env"
    echo ""
    read -p "Press Enter after updating the API key..."
fi

# Create directories
mkdir -p backups logs

# Verify checksum
if [ -f SHA256SUMS ]; then
    echo "🔐 Verifying checksum..."
    if sha256sum -c SHA256SUMS 2>/dev/null; then
        echo "✓ Checksum verified"
    else
        echo "⚠️  Checksum verification failed"
    fi
    echo ""
fi

# Initialize database if needed
if [ ! -f loanpilot.db ]; then
    echo "📊 Initializing database..."
    echo "   Database will be created on first run with sample data"
fi

# Start application
echo "🚀 Starting LoanPilot..."
echo ""
docker-compose up -d

echo ""
echo "⏳ Waiting for application to start..."
sleep 10

# Check health
if curl -sf http://localhost:8000/api/health > /dev/null 2>&1; then
    echo ""
    echo "=========================================="
    echo "✅ Installation Successful!"
    echo "=========================================="
    echo ""
    echo "Access LoanPilot:"
    echo "  http://localhost:8000"
    echo ""
    echo "Useful commands:"
    echo "  View logs:    docker-compose logs -f"
    echo "  Stop:         docker-compose stop"
    echo "  Restart:      docker-compose restart"
    echo "  Status:       docker-compose ps"
    echo ""
else
    echo ""
    echo "⚠️  Application started but health check failed"
    echo "   Check logs: docker-compose logs -f"
    echo ""
fi
INSTALL_EOF

chmod +x "${PACKAGE_DIR}/install.sh"
echo -e "${GREEN}✓${NC} Created: install.sh"

# Create verification script
cat > "${PACKAGE_DIR}/verify.sh" << 'VERIFY_EOF'
#!/bin/bash

echo "=========================================="
echo "LoanPilot Health Check"
echo "=========================================="
echo ""

# Check if container is running
if docker ps | grep -q loanpilot-app; then
    echo "✓ Container is running"
else
    echo "✗ Container is not running"
    echo "  Start with: docker-compose up -d"
    exit 1
fi

# Check health endpoint
echo "Testing health endpoint..."
if curl -sf http://localhost:8000/api/health > /dev/null; then
    echo "✓ Health check passed"
    echo ""
    echo "LoanPilot Status: HEALTHY"
    echo "Access: http://localhost:8000"
else
    echo "✗ Health check failed"
    echo "  Check logs: docker-compose logs -f"
    exit 1
fi

# Show container stats
echo ""
echo "Container Stats:"
docker stats --no-stream loanpilot-app
VERIFY_EOF

chmod +x "${PACKAGE_DIR}/verify.sh"
echo -e "${GREEN}✓${NC} Created: verify.sh"

# Create README for customer
cat > "${PACKAGE_DIR}/README.txt" << README_EOF
========================================
LoanPilot v${VERSION}
Customer: ${CUSTOMER_ID}
========================================

QUICK START
-----------

1. Run the installation script:
   ./install.sh

2. Edit .env file with your API key:
   nano .env

3. Access the application:
   http://localhost:8000


REQUIREMENTS
------------

- Docker 20.10 or later
- Docker Compose 2.0 or later
- 2GB RAM minimum
- 5GB disk space


INSTALLATION
------------

1. Extract this package
2. Run ./install.sh
3. Configure your API key in .env
4. Access http://localhost:8000


SUPPORT
-------

Email: support@loanpilot.com
Phone: 1-800-LOAN-PILOT


LICENSE
-------

This software is licensed for use by ${CUSTOMER_ID} only.
License expires on: $(docker inspect ${IMAGE_TAG} --format='{{.Config.Env}}' | grep LICENSE_EXPIRY | cut -d= -f2)

Unauthorized distribution or use is prohibited.


FILES
-----

${PACKAGE_NAME}.tar.gz    Docker image (compressed)
docker-compose.yml        Container orchestration
.env.example              Configuration template
install.sh                Automated installation
verify.sh                 Health check script
SHA256SUMS                Checksum verification
data/                     Sample data files

========================================
README_EOF

echo -e "${GREEN}✓${NC} Created: README.txt"

# Create archive of entire package
echo ""
echo -e "${BLUE}📦 Creating distribution archive...${NC}"
cd "${OUTPUT_DIR}"
tar -czf "${PACKAGE_NAME}.tar.gz" "${PACKAGE_NAME}/"
cd - > /dev/null

PACKAGE_SIZE_MB=$(du -m "${OUTPUT_DIR}/${PACKAGE_NAME}.tar.gz" | cut -f1)
echo -e "${GREEN}✓${NC} Package created: ${OUTPUT_DIR}/${PACKAGE_NAME}.tar.gz (${PACKAGE_SIZE_MB}MB)"

# Summary
echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${GREEN}✅ Export Complete${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""
echo -e "${GREEN}Distribution Package:${NC}"
echo "  Location: ${OUTPUT_DIR}/${PACKAGE_NAME}.tar.gz"
echo "  Size: ${PACKAGE_SIZE_MB}MB"
echo ""
echo -e "${GREEN}Package Contents:${NC}"
ls -lh "${PACKAGE_DIR}" | tail -n +2 | awk '{print "  " $9 " (" $5 ")"}'
echo ""
echo -e "${GREEN}Customer Delivery:${NC}"
echo "  1. Send: ${OUTPUT_DIR}/${PACKAGE_NAME}.tar.gz"
echo "  2. Instruct customer to extract and run: ./install.sh"
echo "  3. Provide support contact: support@loanpilot.com"
echo ""
