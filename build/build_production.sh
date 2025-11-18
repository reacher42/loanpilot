#!/bin/bash
# ============================================
# LoanPilot Production Build Script
# Builds secure Docker image with bytecode compilation
# ============================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="loanpilot"
VERSION="${VERSION:-1.0.0}"
CUSTOMER_ID="${CUSTOMER_ID:-DEMO}"
LICENSE_EXPIRY="${LICENSE_EXPIRY:-2025-12-31}"

# Generate license token
SECRET_KEY="loanpilot-2024-secure-key-change-per-customer"

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}LoanPilot Production Build${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --customer)
            CUSTOMER_ID="$2"
            shift 2
            ;;
        --expiry)
            LICENSE_EXPIRY="$2"
            shift 2
            ;;
        --version)
            VERSION="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --customer ID     Customer identifier (default: DEMO)"
            echo "  --expiry DATE     License expiry date YYYY-MM-DD (default: 2025-12-31)"
            echo "  --version VER     Version number (default: 1.0.0)"
            echo "  --help            Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 --customer ACME --expiry 2025-12-31 --version 1.0.0"
            echo "  $0 --customer TestCorp --expiry 2025-06-30"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Validate expiry date format
if ! date -d "$LICENSE_EXPIRY" >/dev/null 2>&1; then
    echo -e "${RED}❌ Invalid date format: $LICENSE_EXPIRY${NC}"
    echo -e "${YELLOW}   Use format: YYYY-MM-DD${NC}"
    exit 1
fi

# Generate LICENSE_TOKEN with HMAC signature
generate_license_token() {
    local date="$1"
    local customer="$2"
    local message="${date}:${customer}"

    # Use Python to generate HMAC
    LICENSE_TOKEN=$(python3 -c "
import hmac
import hashlib
secret = b'${SECRET_KEY}'
message = '${message}'.encode()
signature = hmac.new(secret, message, hashlib.sha256).hexdigest()[:16]
print(f'${date}:${customer}:{signature}')
")

    echo "$LICENSE_TOKEN"
}

LICENSE_TOKEN=$(generate_license_token "$LICENSE_EXPIRY" "$CUSTOMER_ID")

# Display build configuration
echo -e "${GREEN}Build Configuration:${NC}"
echo "  Customer ID: ${CUSTOMER_ID}"
echo "  Version: ${VERSION}"
echo "  License Expiry: ${LICENSE_EXPIRY}"
echo "  License Token: ${LICENSE_TOKEN}"
echo "  Image Tag: ${IMAGE_NAME}:${CUSTOMER_ID}-${VERSION}"
echo ""

# Check if Dockerfile exists
if [ ! -f "Dockerfile.production" ]; then
    echo -e "${RED}❌ Dockerfile.production not found${NC}"
    exit 1
fi

# Copy production .dockerignore
echo -e "${BLUE}📝 Setting up production .dockerignore...${NC}"
if [ -f ".dockerignore.production" ]; then
    cp .dockerignore .dockerignore.backup
    cp .dockerignore.production .dockerignore
    echo -e "${GREEN}✓${NC} Production .dockerignore activated"
else
    echo -e "${YELLOW}⚠️  .dockerignore.production not found, using default${NC}"
fi

# Build Docker image
echo ""
echo -e "${BLUE}🔨 Building Docker image...${NC}"
echo ""

docker build \
    --file Dockerfile.production \
    --build-arg LICENSE_TOKEN="$LICENSE_TOKEN" \
    --build-arg LICENSE_EXPIRY="$LICENSE_EXPIRY" \
    --build-arg CUSTOMER_ID="$CUSTOMER_ID" \
    --tag "${IMAGE_NAME}:${CUSTOMER_ID}-${VERSION}" \
    --tag "${IMAGE_NAME}:${CUSTOMER_ID}-latest" \
    .

BUILD_STATUS=$?

# Restore original .dockerignore
if [ -f ".dockerignore.backup" ]; then
    mv .dockerignore.backup .dockerignore
    echo -e "${GREEN}✓${NC} Restored original .dockerignore"
fi

if [ $BUILD_STATUS -ne 0 ]; then
    echo ""
    echo -e "${RED}❌ Build failed${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${GREEN}✅ Build Successful${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Get image size
IMAGE_SIZE=$(docker images "${IMAGE_NAME}:${CUSTOMER_ID}-${VERSION}" --format "{{.Size}}")
echo -e "${GREEN}Image Details:${NC}"
echo "  Repository: ${IMAGE_NAME}"
echo "  Tag: ${CUSTOMER_ID}-${VERSION}"
echo "  Size: ${IMAGE_SIZE}"
echo ""

# Verify image contents
echo -e "${BLUE}🔍 Verifying image contents...${NC}"
echo ""

# Check for source files (should be none)
SOURCE_FILES=$(docker run --rm "${IMAGE_NAME}:${CUSTOMER_ID}-${VERSION}" find /app -name "*.py" ! -name "__init__.py" 2>/dev/null | wc -l)
if [ "$SOURCE_FILES" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Warning: Found $SOURCE_FILES .py source files in image${NC}"
    docker run --rm "${IMAGE_NAME}:${CUSTOMER_ID}-${VERSION}" find /app -name "*.py" ! -name "__init__.py"
else
    echo -e "${GREEN}✓${NC} No source .py files found (bytecode only)"
fi

# Check for bytecode files
BYTECODE_FILES=$(docker run --rm "${IMAGE_NAME}:${CUSTOMER_ID}-${VERSION}" find /app -name "*.pyc" 2>/dev/null | wc -l)
echo -e "${GREEN}✓${NC} Found $BYTECODE_FILES .pyc bytecode files"

# Check for documentation
DOC_FILES=$(docker run --rm "${IMAGE_NAME}:${CUSTOMER_ID}-${VERSION}" find /app -name "*.md" 2>/dev/null | wc -l)
if [ "$DOC_FILES" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Warning: Found $DOC_FILES .md documentation files${NC}"
else
    echo -e "${GREEN}✓${NC} No documentation files found"
fi

# Check for utils directory
if docker run --rm "${IMAGE_NAME}:${CUSTOMER_ID}-${VERSION}" test -d /app/utils 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Warning: utils/ directory found in image${NC}"
else
    echo -e "${GREEN}✓${NC} utils/ directory excluded"
fi

echo ""

# Test health endpoint
echo -e "${BLUE}🧪 Testing image...${NC}"
echo "  Starting test container..."

docker run -d \
    --name loanpilot-test-$$ \
    -p 8001:8000 \
    -e ANTHROPIC_API_KEY=test-key \
    "${IMAGE_NAME}:${CUSTOMER_ID}-${VERSION}" \
    > /dev/null 2>&1

sleep 5

# Test health check
if curl -sf http://localhost:8001/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Health check passed"
else
    echo -e "${RED}✗${NC} Health check failed"
    docker logs loanpilot-test-$$
fi

# Cleanup test container
docker stop loanpilot-test-$$ > /dev/null 2>&1
docker rm loanpilot-test-$$ > /dev/null 2>&1

echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${GREEN}Next Steps:${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""
echo "1. Test the image locally:"
echo -e "   ${YELLOW}docker run -p 8000:8000 -e ANTHROPIC_API_KEY=your-key ${IMAGE_NAME}:${CUSTOMER_ID}-${VERSION}${NC}"
echo ""
echo "2. Export for distribution:"
echo -e "   ${YELLOW}./build/export_image.sh --customer ${CUSTOMER_ID} --version ${VERSION}${NC}"
echo ""
echo "3. View image details:"
echo -e "   ${YELLOW}docker images ${IMAGE_NAME}:${CUSTOMER_ID}-${VERSION}${NC}"
echo ""
