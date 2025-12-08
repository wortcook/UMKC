#!/bin/bash
#
# OpenGenome2 Web UI Demonstration Script
#
# This script demonstrates all features of the web interface using curl
# to interact with the REST API endpoints. It showcases:
#   1. System health checks
#   2. Dataset browsing
#   3. Data ingestion (HuggingFace download)
#   4. K-mer analysis via web API
#   5. Codon analysis via web API
#   6. Results browsing
#
# Prerequisites:
#   - Docker containers running (docker-compose up -d)
#   - Web service accessible at http://localhost:5002
#

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Configuration
WEB_URL="http://localhost:5002"
API_BASE="$WEB_URL/api"
LOG_FILE="demo_web_ui_$(date +%Y%m%d_%H%M%S).log"

# Start logging
exec > >(tee -a "$LOG_FILE") 2>&1

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         OpenGenome2 Web UI Demonstration                       ║${NC}"
echo -e "${BLUE}║                                                                ║${NC}"
echo -e "${BLUE}║  Demonstrates all REST API endpoints and web interface         ║${NC}"
echo -e "${BLUE}║  capabilities through automated curl requests                  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Started at: $(date)"
echo "Log file: $LOG_FILE"
echo "Web URL: $WEB_URL"
echo ""

#=============================================================================
# Helper Functions
#=============================================================================

# Pretty print JSON response
print_json() {
    if command -v jq &> /dev/null; then
        echo "$1" | jq '.'
    else
        echo "$1" | python3 -m json.tool 2>/dev/null || echo "$1"
    fi
}

# Check if web service is running
check_web_service() {
    echo -e "${CYAN}Checking web service availability...${NC}"
    if curl -s -f "$API_BASE/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Web service is running${NC}"
        return 0
    else
        echo -e "${RED}✗ Web service is not accessible at $WEB_URL${NC}"
        echo -e "${YELLOW}Please start the services: docker-compose up -d${NC}"
        exit 1
    fi
}

# Wait for operation with spinner
wait_with_spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='|/-\'
    while ps -p $pid > /dev/null 2>&1; do
        local temp=${spinstr#?}
        printf " [%c]  " "$spinstr"
        local spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b\b"
    done
    printf "    \b\b\b\b"
}

#=============================================================================
# PHASE 1: SYSTEM STATUS & HEALTH
#=============================================================================
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  PHASE 1: SYSTEM STATUS & HEALTH CHECK                         ${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

check_web_service
echo ""

echo -e "${GREEN}[1.1] Testing health endpoint (GET /api/health)${NC}"
HEALTH_RESPONSE=$(curl -s "$API_BASE/health")
echo "Response:"
print_json "$HEALTH_RESPONSE"
echo ""

echo -e "${GREEN}[1.2] Listing available datasets (GET /api/datasets)${NC}"
DATASETS_RESPONSE=$(curl -s "$API_BASE/datasets")
echo "Response:"
print_json "$DATASETS_RESPONSE"
echo ""

DATASET_COUNT=$(echo "$DATASETS_RESPONSE" | grep -o '"name"' | wc -l | tr -d ' ')
echo -e "${BLUE}Found $DATASET_COUNT datasets${NC}"
echo ""

#=============================================================================
# PHASE 2: DATA INGESTION VIA WEB API
#=============================================================================
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  PHASE 2: DATA INGESTION DEMONSTRATION                         ${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${GREEN}[2.1] Testing organelle ingestion endpoint${NC}"
echo "This demonstrates downloading from HuggingFace and ingesting to Parquet"
echo ""

# Check if organelle dataset already exists
if echo "$DATASETS_RESPONSE" | grep -q '"organelle"'; then
    echo -e "${YELLOW}⚠ Organelle dataset already exists, skipping ingestion${NC}"
    echo "  To test ingestion, remove data/parquet/organelle/ and re-run"
else
    echo "Sending POST request to /api/ingest/organelle"
    echo "Parameters:"
    echo "  - dataset_name: LynixID/NCBI_Organelles"
    echo "  - chunk_size: 1000"
    echo "  - compression: snappy"
    echo "  - max_sequences: 5000 (sample for demo)"
    echo ""
    
    INGEST_REQUEST='{
        "dataset_name": "LynixID/NCBI_Organelles",
        "chunk_size": 1000,
        "compression": "snappy",
        "max_sequences": 5000
    }'
    
    echo "Request body:"
    print_json "$INGEST_REQUEST"
    echo ""
    
    echo -e "${YELLOW}Starting ingestion (this may take 2-3 minutes)...${NC}"
    INGEST_RESPONSE=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$INGEST_REQUEST" \
        "$API_BASE/ingest/organelle")
    
    echo "Response:"
    print_json "$INGEST_RESPONSE"
    echo ""
    
    if echo "$INGEST_RESPONSE" | grep -q '"status":"success"'; then
        echo -e "${GREEN}✓ Ingestion completed successfully${NC}"
    else
        echo -e "${RED}✗ Ingestion failed or already exists${NC}"
    fi
fi
echo ""

#=============================================================================
# PHASE 3: ANALYSIS - K-MER FREQUENCY
#=============================================================================
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  PHASE 3: K-MER FREQUENCY ANALYSIS                             ${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${GREEN}[3.1] Running k-mer analysis via web API${NC}"
echo "Analyzing 6-mers on organelle dataset"
echo ""

KMER_REQUEST='{
    "dataset": "organelle",
    "k": 6,
    "min_count": 10,
    "skip_n": true,
    "sample_size": 1000
}'

echo "Request body:"
print_json "$KMER_REQUEST"
echo ""

echo -e "${YELLOW}Starting k-mer analysis (this may take 1-2 minutes)...${NC}"
KMER_RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "$KMER_REQUEST" \
    "$API_BASE/analyze/kmer")

echo "Response:"
print_json "$KMER_RESPONSE"
echo ""

if echo "$KMER_RESPONSE" | grep -q '"status":"success"'; then
    echo -e "${GREEN}✓ K-mer analysis completed successfully${NC}"
    
    # Extract statistics
    UNIQUE_KMERS=$(echo "$KMER_RESPONSE" | grep -o '"unique_kmers":[0-9]*' | cut -d: -f2)
    TOTAL_KMERS=$(echo "$KMER_RESPONSE" | grep -o '"total_kmers":[0-9]*' | cut -d: -f2)
    
    if [ -n "$UNIQUE_KMERS" ] && [ -n "$TOTAL_KMERS" ]; then
        echo ""
        echo "Analysis Results:"
        echo "  - Unique k-mers: $(printf "%'d" $UNIQUE_KMERS)"
        echo "  - Total k-mers: $(printf "%'d" $TOTAL_KMERS)"
    fi
else
    echo -e "${RED}✗ K-mer analysis failed${NC}"
fi
echo ""

#=============================================================================
# PHASE 4: ANALYSIS - CODON USAGE
#=============================================================================
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  PHASE 4: CODON USAGE ANALYSIS                                 ${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${GREEN}[4.1] Running codon analysis via web API${NC}"
echo "Analyzing codon usage on organelle dataset"
echo ""

CODON_REQUEST='{
    "dataset": "organelle",
    "frame": 0,
    "skip_n": true,
    "skip_stops": false,
    "sample_size": 1000
}'

echo "Request body:"
print_json "$CODON_REQUEST"
echo ""

echo -e "${YELLOW}Starting codon analysis (this may take 1-2 minutes)...${NC}"
CODON_RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "$CODON_REQUEST" \
    "$API_BASE/analyze/codon")

echo "Response:"
print_json "$CODON_RESPONSE"
echo ""

if echo "$CODON_RESPONSE" | grep -q '"status":"success"'; then
    echo -e "${GREEN}✓ Codon analysis completed successfully${NC}"
    
    # Extract statistics
    UNIQUE_CODONS=$(echo "$CODON_RESPONSE" | grep -o '"unique_codons":[0-9]*' | cut -d: -f2)
    TOTAL_CODONS=$(echo "$CODON_RESPONSE" | grep -o '"total_codons":[0-9]*' | cut -d: -f2)
    
    if [ -n "$UNIQUE_CODONS" ] && [ -n "$TOTAL_CODONS" ]; then
        echo ""
        echo "Analysis Results:"
        echo "  - Unique codons: $(printf "%'d" $UNIQUE_CODONS)"
        echo "  - Total codons: $(printf "%'d" $TOTAL_CODONS)"
    fi
else
    echo -e "${RED}✗ Codon analysis failed${NC}"
fi
echo ""

#=============================================================================
# PHASE 5: RESULTS BROWSING
#=============================================================================
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  PHASE 5: RESULTS BROWSING                                     ${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${GREEN}[5.1] Listing all analysis results (GET /api/results)${NC}"
RESULTS_RESPONSE=$(curl -s "$API_BASE/results")
echo "Response:"
print_json "$RESULTS_RESPONSE"
echo ""

RESULTS_COUNT=$(echo "$RESULTS_RESPONSE" | grep -o '"name"' | wc -l | tr -d ' ')
echo -e "${BLUE}Found $RESULTS_COUNT result directories${NC}"
echo ""

echo -e "${GREEN}[5.2] Refreshing datasets list${NC}"
DATASETS_FINAL=$(curl -s "$API_BASE/datasets")
echo "Response:"
print_json "$DATASETS_FINAL"
echo ""

#=============================================================================
# PHASE 6: WEB UI PAGES DEMONSTRATION
#=============================================================================
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  PHASE 6: WEB UI PAGES                                         ${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${GREEN}[6.1] Testing HTML pages availability${NC}"
echo ""

PAGES=(
    "/"
    "/ingest"
    "/analyze"
    "/results"
    "/search"
)

PAGE_NAMES=(
    "Home Page"
    "Data Ingestion"
    "Analysis"
    "Results Browser"
    "Sequence Search"
)

for i in "${!PAGES[@]}"; do
    PAGE="${PAGES[$i]}"
    NAME="${PAGE_NAMES[$i]}"
    
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$WEB_URL$PAGE")
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo -e "  ${GREEN}✓${NC} $NAME ($PAGE) - Accessible"
    else
        echo -e "  ${RED}✗${NC} $NAME ($PAGE) - Failed (HTTP $HTTP_CODE)"
    fi
done
echo ""

#=============================================================================
# SUMMARY
#=============================================================================
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  DEMONSTRATION SUMMARY                                         ${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${BOLD}Web UI Features Demonstrated:${NC}"
echo ""
echo "✓ REST API Endpoints:"
echo "  • GET  /api/health     - System health check"
echo "  • GET  /api/datasets   - List available datasets"
echo "  • GET  /api/results    - Browse analysis results"
echo "  • POST /api/ingest/organelle - Download from HuggingFace"
echo "  • POST /api/analyze/kmer     - K-mer frequency analysis"
echo "  • POST /api/analyze/codon    - Codon usage analysis"
echo ""
echo "✓ HTML Pages:"
echo "  • /          - Home page with system status"
echo "  • /ingest    - Data ingestion interface"
echo "  • /analyze   - Analysis execution interface"
echo "  • /results   - Results browser"
echo "  • /search    - Sequence search interface"
echo ""

echo -e "${BOLD}Access the Web UI:${NC}"
echo "  Open your browser to: ${CYAN}$WEB_URL${NC}"
echo ""

echo -e "${BOLD}Key Features:${NC}"
echo "  • Browser-based interface for all CLI operations"
echo "  • No command-line knowledge required"
echo "  • Real-time analysis execution"
echo "  • Dataset browsing and management"
echo "  • Results visualization and download"
echo ""

echo -e "${BOLD}API Documentation:${NC}"
echo "  • Full API docs: src/opengenome/web/README.md"
echo "  • Example curl commands logged in: $LOG_FILE"
echo ""

echo "Completed at: $(date)"
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Web UI Demonstration Complete!                                ║${NC}"
echo -e "${GREEN}║                                                                ║${NC}"
echo -e "${GREEN}║  Try it yourself at: http://localhost:5002                     ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
