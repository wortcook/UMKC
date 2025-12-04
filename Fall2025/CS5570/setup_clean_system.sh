#!/bin/bash
#
# Setup script for clean systems
# Ensures all Docker images are built with latest dependencies
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}==== OpenGenome2 Clean System Setup ====${NC}"

# Step 1: Copy .env.example to .env if not exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating .env from .env.example...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✓ .env created${NC}"
else
    echo -e "${GREEN}✓ .env already exists${NC}"
fi

# Step 2: Stop and remove any existing containers/images
echo -e "${YELLOW}Cleaning up any existing containers...${NC}"
docker-compose down --volumes --remove-orphans 2>/dev/null || true
echo -e "${GREEN}✓ Cleanup complete${NC}"

# Step 3: Remove old images and build cache to force rebuild
echo -e "${YELLOW}Removing old images and build cache...${NC}"
docker-compose rm -f 2>/dev/null || true
docker images | grep -E "cs5570|opengenome" | awk '{print $3}' | xargs -r docker rmi -f 2>/dev/null || true
# Remove build cache to ensure completely fresh build
docker builder prune -af 2>/dev/null || true
echo -e "${GREEN}✓ Old images and cache removed${NC}"

# Step 4: Build images from scratch
echo -e "${YELLOW}Building Docker images (this may take 5-10 minutes)...${NC}"
docker-compose build --no-cache --progress=plain 2>&1 | tee build.log
if [ ${PIPESTATUS[0]} -ne 0 ]; then
    echo -e "${RED}✗ Build failed - see build.log for details${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Images built successfully${NC}"

# Step 5: Start containers
echo -e "${YELLOW}Starting containers...${NC}"
docker-compose up -d
echo -e "${GREEN}✓ Containers started${NC}"

# Step 6: Wait for Spark to be ready
echo -e "${YELLOW}Waiting for Spark cluster to be ready (30 seconds)...${NC}"
sleep 30

# Step 7: Verify py4j is installed
echo -e "${YELLOW}Verifying py4j installation...${NC}"

# Check master
echo "Checking spark-master..."
docker exec opengenome-spark-master pip list | grep py4j
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ py4j verified in master${NC}"
else
    echo -e "${RED}✗ py4j NOT found in master${NC}"
    echo "Installed packages in master:"
    docker exec opengenome-spark-master pip list
    exit 1
fi

# Check worker
echo "Checking spark-worker-1..."
docker exec opengenome-spark-worker-1 pip list | grep py4j
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ py4j verified in worker-1${NC}"
else
    echo -e "${RED}✗ py4j NOT found in worker-1${NC}"
    echo "Installed packages in worker-1:"
    docker exec opengenome-spark-worker-1 pip list
    exit 1
fi

# Actually test importing py4j
echo "Testing py4j import..."
docker exec opengenome-spark-master python3 -c "import py4j; print(f'Successfully imported py4j {py4j.__version__}')"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ py4j imports successfully${NC}"
else
    echo -e "${RED}✗ py4j import failed${NC}"
    exit 1
fi

# Step 8: Test CLI
echo -e "${YELLOW}Testing OpenGenome CLI...${NC}"
./opengenome --help > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ CLI working${NC}"
else
    echo -e "${RED}✗ CLI test failed${NC}"
    exit 1
fi

echo -e "${GREEN}==== Setup Complete ====${NC}"
echo -e "${GREEN}System is ready to run demo_end_to_end.sh${NC}"
