#!/bin/bash
# LoanPilot Docker Setup Validation Script

set -e

echo "=================================================="
echo "LoanPilot Docker Setup Validation"
echo "=================================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# Check function
check() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $1"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} $1"
        ((FAILED++))
    fi
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

echo "1. Checking Required Files..."
echo "-----------------------------------"

# Check Dockerfile
if [ -f "Dockerfile" ]; then
    check "Dockerfile exists"
else
    check "Dockerfile missing"
fi

# Check docker-compose.yml
if [ -f "docker-compose.yml" ]; then
    check "docker-compose.yml exists"
else
    check "docker-compose.yml missing"
fi

# Check .dockerignore
if [ -f ".dockerignore" ]; then
    check ".dockerignore exists"
else
    check ".dockerignore missing"
fi

# Check .env.example
if [ -f ".env.example" ]; then
    check ".env.example exists"
else
    check ".env.example missing"
fi

echo ""
echo "2. Checking Application Files..."
echo "-----------------------------------"

# Check requirements.txt
if [ -f "requirements.txt" ]; then
    check "requirements.txt exists"
    LINE_COUNT=$(wc -l < requirements.txt)
    if [ $LINE_COUNT -gt 0 ]; then
        check "requirements.txt has $LINE_COUNT dependencies"
    else
        warn "requirements.txt is empty"
    fi
else
    check "requirements.txt missing"
fi

# Check main application
if [ -f "web-app/main.py" ]; then
    check "web-app/main.py exists"
else
    check "web-app/main.py missing"
fi

# Check sample data
if [ -f "data/v3/Non-QM_Matrix.xlsx - Attributes.tsv" ]; then
    check "Sample data TSV exists"
else
    warn "Sample data TSV missing (required for database reset)"
fi

echo ""
echo "3. Checking Directory Structure..."
echo "-----------------------------------"

# Check directories
for dir in "web-app" "data/v3" "backups" "utils"; do
    if [ -d "$dir" ]; then
        check "Directory '$dir' exists"
    else
        if [ "$dir" == "backups" ]; then
            warn "Directory '$dir' missing (will be created automatically)"
        else
            check "Directory '$dir' missing"
        fi
    fi
done

echo ""
echo "4. Checking Environment Configuration..."
echo "-----------------------------------"

# Check .env file
if [ -f ".env" ]; then
    check ".env file exists"

    # Check if API key is set
    if grep -q "ANTHROPIC_API_KEY=sk-ant-" .env 2>/dev/null; then
        check "ANTHROPIC_API_KEY appears to be set"
    elif grep -q "ANTHROPIC_API_KEY=your_api_key_here" .env 2>/dev/null; then
        warn "ANTHROPIC_API_KEY not configured (using placeholder)"
    else
        warn "ANTHROPIC_API_KEY may not be properly configured"
    fi
else
    warn ".env file missing (create from .env.example)"
fi

echo ""
echo "5. Validating Dockerfile..."
echo "-----------------------------------"

# Check Dockerfile content
if grep -q "FROM python:3.11-slim" Dockerfile 2>/dev/null; then
    check "Dockerfile uses Python 3.11 base image"
else
    check "Dockerfile base image not found"
fi

if grep -q "EXPOSE 8000" Dockerfile 2>/dev/null; then
    check "Dockerfile exposes port 8000"
else
    check "Dockerfile port not exposed"
fi

if grep -q "uvicorn" Dockerfile 2>/dev/null; then
    check "Dockerfile CMD uses uvicorn"
else
    check "Dockerfile CMD not found"
fi

if grep -q "HEALTHCHECK" Dockerfile 2>/dev/null; then
    check "Dockerfile includes health check"
else
    warn "Dockerfile missing health check"
fi

echo ""
echo "6. Validating docker-compose.yml..."
echo "-----------------------------------"

if grep -q "version:" docker-compose.yml 2>/dev/null; then
    check "docker-compose.yml has version specified"
else
    check "docker-compose.yml version missing"
fi

if grep -q "8000:8000" docker-compose.yml 2>/dev/null; then
    check "docker-compose.yml maps port 8000"
else
    check "docker-compose.yml port mapping missing"
fi

if grep -q "volumes:" docker-compose.yml 2>/dev/null; then
    check "docker-compose.yml includes volume mounts"
else
    check "docker-compose.yml volumes missing"
fi

if grep -q "loanpilot.db" docker-compose.yml 2>/dev/null; then
    check "docker-compose.yml mounts database file"
else
    warn "docker-compose.yml database mount missing"
fi

if grep -q "env_file:" docker-compose.yml 2>/dev/null; then
    check "docker-compose.yml loads .env file"
else
    warn "docker-compose.yml .env loading missing"
fi

echo ""
echo "7. Checking Docker Installation..."
echo "-----------------------------------"

# Check if Docker is installed
if command -v docker &> /dev/null; then
    check "Docker is installed"
    DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | tr -d ',')
    echo "   Version: $DOCKER_VERSION"
else
    warn "Docker is not installed (install before deploying)"
fi

# Check if Docker Compose is available
if command -v docker-compose &> /dev/null; then
    check "docker-compose is installed"
    COMPOSE_VERSION=$(docker-compose --version | cut -d' ' -f4 | tr -d ',')
    echo "   Version: $COMPOSE_VERSION"
elif docker compose version &> /dev/null 2>&1; then
    check "docker compose (plugin) is available"
    COMPOSE_VERSION=$(docker compose version --short)
    echo "   Version: $COMPOSE_VERSION"
else
    warn "Docker Compose not installed (install before deploying)"
fi

echo ""
echo "8. File Size Checks..."
echo "-----------------------------------"

# Check if files are not empty
for file in "Dockerfile" "docker-compose.yml" ".dockerignore" "requirements.txt"; do
    if [ -f "$file" ]; then
        SIZE=$(wc -c < "$file")
        if [ $SIZE -gt 0 ]; then
            check "$file is not empty ($SIZE bytes)"
        else
            warn "$file is empty"
        fi
    fi
done

echo ""
echo "=================================================="
echo "Validation Summary"
echo "=================================================="
echo -e "${GREEN}Passed:${NC} $PASSED"
if [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}Warnings:${NC} $WARNINGS"
fi
if [ $FAILED -gt 0 ]; then
    echo -e "${RED}Failed:${NC} $FAILED"
fi
echo ""

if [ $FAILED -gt 0 ]; then
    echo -e "${RED}❌ Validation FAILED. Please fix the errors above.${NC}"
    exit 1
elif [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}⚠ Validation completed with warnings.${NC}"
    echo "Review warnings above before deploying."
    exit 0
else
    echo -e "${GREEN}✅ All checks passed! Docker setup is ready.${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Ensure .env file has valid ANTHROPIC_API_KEY"
    echo "2. Run: docker-compose build"
    echo "3. Run: docker-compose up -d"
    echo "4. Access: http://localhost:8000"
    exit 0
fi
