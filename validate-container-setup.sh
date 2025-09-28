#!/bin/bash

echo "🔍 Validating Container Setup for Sensor Dashboard"
echo "================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track validation status
VALID=true

echo ""
echo "📋 Checking required files..."

# Check Dockerfile
if [ -f "Dockerfile" ]; then
    echo -e "${GREEN}✓${NC} Dockerfile exists"
    
    # Check if .env is NOT copied in Dockerfile (security check)
    if grep -q "COPY .env" Dockerfile; then
        echo -e "${RED}✗${NC} WARNING: Dockerfile copies .env file (security risk)"
        VALID=false
    else
        echo -e "${GREEN}✓${NC} Dockerfile does not copy .env (secure)"
    fi
    
    # Check if main.py is copied
    if grep -q "COPY main.py" Dockerfile; then
        echo -e "${GREEN}✓${NC} Dockerfile copies main.py"
    else
        echo -e "${RED}✗${NC} Dockerfile missing main.py copy"
        VALID=false
    fi
else
    echo -e "${RED}✗${NC} Dockerfile missing"
    VALID=false
fi

# Check .dockerignore
if [ -f ".dockerignore" ]; then
    echo -e "${GREEN}✓${NC} .dockerignore exists"
else
    echo -e "${YELLOW}⚠${NC}  .dockerignore missing (recommended)"
fi

# Check podman-compose.yml
if [ -f "podman-compose.yml" ]; then
    echo -e "${GREEN}✓${NC} podman-compose.yml exists"
    
    # Check if env_file is configured
    if grep -q "env_file:" podman-compose.yml; then
        echo -e "${GREEN}✓${NC} podman-compose.yml configured for .env file"
    else
        echo -e "${RED}✗${NC} podman-compose.yml missing env_file configuration"
        VALID=false
    fi
else
    echo -e "${YELLOW}⚠${NC}  podman-compose.yml missing (optional)"
fi

# Check run-podman.sh
if [ -f "run-podman.sh" ]; then
    echo -e "${GREEN}✓${NC} run-podman.sh exists"
    
    if [ -x "run-podman.sh" ]; then
        echo -e "${GREEN}✓${NC} run-podman.sh is executable"
    else
        echo -e "${YELLOW}⚠${NC}  run-podman.sh not executable (run: chmod +x run-podman.sh)"
    fi
    
    # Check if --env-file is used
    if grep -q "\--env-file" run-podman.sh; then
        echo -e "${GREEN}✓${NC} run-podman.sh configured for .env file"
    else
        echo -e "${RED}✗${NC} run-podman.sh missing --env-file configuration"
        VALID=false
    fi
else
    echo -e "${RED}✗${NC} run-podman.sh missing"
    VALID=false
fi

# Check .env file
echo ""
echo "🔐 Checking environment configuration..."

if [ -f ".env" ]; then
    echo -e "${GREEN}✓${NC} .env file exists"
    
    # Check required variables
    if grep -q "SUPABASE_URL=" .env; then
        echo -e "${GREEN}✓${NC} SUPABASE_URL configured"
    else
        echo -e "${RED}✗${NC} SUPABASE_URL missing in .env"
        VALID=false
    fi
    
    if grep -q "SUPABASE_KEY=" .env; then
        echo -e "${GREEN}✓${NC} SUPABASE_KEY configured"
    else
        echo -e "${RED}✗${NC} SUPABASE_KEY missing in .env"
        VALID=false
    fi
    
    if grep -q "DASHBOARD_USER=" .env; then
        echo -e "${GREEN}✓${NC} DASHBOARD_USER configured"
    else
        echo -e "${RED}✗${NC} DASHBOARD_USER missing in .env"
        VALID=false
    fi
    
    if grep -q "DASHBOARD_PASS=" .env; then
        echo -e "${GREEN}✓${NC} DASHBOARD_PASS configured"
        
        # Check if password is still default
        if grep -q "DASHBOARD_PASS=sensor123" .env; then
            echo -e "${YELLOW}⚠${NC}  Using default password (consider changing for production)"
        fi
    else
        echo -e "${RED}✗${NC} DASHBOARD_PASS missing in .env"
        VALID=false
    fi
else
    echo -e "${RED}✗${NC} .env file missing"
    VALID=false
fi

# Check main application file
echo ""
echo "🐍 Checking application files..."

if [ -f "main.py" ]; then
    echo -e "${GREEN}✓${NC} main.py exists"
else
    echo -e "${RED}✗${NC} main.py missing"
    VALID=false
fi

if [ -f "pyproject.toml" ]; then
    echo -e "${GREEN}✓${NC} pyproject.toml exists"
else
    echo -e "${RED}✗${NC} pyproject.toml missing"
    VALID=false
fi

# Check gitignore
echo ""
echo "📝 Checking project configuration..."

if [ -f ".gitignore" ]; then
    echo -e "${GREEN}✓${NC} .gitignore exists"
    
    if grep -q "\.env" .gitignore; then
        echo -e "${GREEN}✓${NC} .env is properly ignored in git"
    else
        echo -e "${RED}✗${NC} .env not in .gitignore (security risk)"
        VALID=false
    fi
else
    echo -e "${YELLOW}⚠${NC}  .gitignore missing (recommended)"
fi

# Final summary
echo ""
echo "================================================="
if [ "$VALID" = true ]; then
    echo -e "${GREEN}🎉 Container setup is valid!${NC}"
    echo ""
    echo "📋 Next steps on your Podman machine:"
    echo "1. Copy this project to your Podman machine"
    echo "2. Run: ./run-podman.sh build"
    echo "3. Run: ./run-podman.sh start"
    echo "4. Access dashboard at: http://localhost:8081"
else
    echo -e "${RED}❌ Container setup has issues that need to be fixed${NC}"
    echo ""
    echo "Please fix the issues above before deploying."
fi

echo ""
echo "🔗 Alternative deployment commands:"
echo "   Using podman-compose: podman-compose up -d"
echo "   Using direct podman:   podman build -t sensor-dashboard . && podman run -d --name sensor-dashboard -p 8081:8081 --env-file .env sensor-dashboard"