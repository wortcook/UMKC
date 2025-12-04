#!/bin/bash
#
# OpenGenome2 Web API Demonstration Script
# This script demonstrates the search functionality using the web API
#

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Base directory
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASE_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}OpenGenome2 Web API Demonstration${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if web service is running
echo -e "${GREEN}[Step 1/3] Checking web service...${NC}"
if curl -s http://localhost:5002/api/health > /dev/null; then
    echo "✓ Web service is running at http://localhost:5002"
else
    echo -e "${RED}✗ Web service is not running${NC}"
    echo "Please start services with: docker-compose up -d"
    exit 1
fi
echo ""

# Create output directory
mkdir -p results/demo/api_searches
OUTPUT_DIR="results/demo/api_searches"

# Step 2: Perform sequence searches via API
echo -e "${GREEN}[Step 2/3] Running sequence searches via API...${NC}"
echo ""

# Search 1: AAAA
echo "  [Search 1/3] Pattern: AAAA (homopolymer)..."
curl -s -X POST http://localhost:5002/api/analyze/search \
  -H "Content-Type: application/json" \
  -d '{
    "pattern": "AAAA",
    "input_dir": "/data/parquet/organelle",
    "case_sensitive": false,
    "reverse_complement": false,
    "max_results": 10
  }' | python3 -c "
import sys, json
data = json.load(sys.stdin)
with open('$OUTPUT_DIR/search_AAAA.json', 'w') as f:
    json.dump(data, f, indent=2)
if data.get('status') == 'success':
    result = data['result']
    print(f'    ✓ Found {result[\"matching_sequences\"]} sequences with AAAA')
    print(f'      Match rate: {result[\"match_percentage\"]}%')
    print(f'      Top match: {result[\"sample_matches\"][0][\"sequence_id\"]} ({result[\"sample_matches\"][0][\"match_count\"]} occurrences)')
else:
    print(f'    ✗ Error: {data.get(\"message\", \"Unknown error\")}')
    sys.exit(1)
"
echo ""

# Search 2: ACGT
echo "  [Search 2/3] Pattern: ACGT (all four bases)..."
curl -s -X POST http://localhost:5002/api/analyze/search \
  -H "Content-Type: application/json" \
  -d '{
    "pattern": "ACGT",
    "input_dir": "/data/parquet/organelle",
    "case_sensitive": false,
    "reverse_complement": false,
    "max_results": 10
  }' | python3 -c "
import sys, json
data = json.load(sys.stdin)
with open('$OUTPUT_DIR/search_ACGT.json', 'w') as f:
    json.dump(data, f, indent=2)
if data.get('status') == 'success':
    result = data['result']
    print(f'    ✓ Found {result[\"matching_sequences\"]} sequences with ACGT')
    print(f'      Match rate: {result[\"match_percentage\"]}%')
    print(f'      Top match: {result[\"sample_matches\"][0][\"sequence_id\"]} ({result[\"sample_matches\"][0][\"match_count\"]} occurrences)')
else:
    print(f'    ✗ Error: {data.get(\"message\", \"Unknown error\")}')
    sys.exit(1)
"
echo ""

# Search 3: GGGGGGGG with reverse complement
echo "  [Search 3/3] Pattern: GGGGGGGG (G-run with reverse complement)..."
curl -s -X POST http://localhost:5002/api/analyze/search \
  -H "Content-Type: application/json" \
  -d '{
    "pattern": "GGGGGGGG",
    "input_dir": "/data/parquet/organelle",
    "case_sensitive": false,
    "reverse_complement": true,
    "max_results": 10
  }' | python3 -c "
import sys, json
data = json.load(sys.stdin)
with open('$OUTPUT_DIR/search_GGGGGGGG.json', 'w') as f:
    json.dump(data, f, indent=2)
if data.get('status') == 'success':
    result = data['result']
    print(f'    ✓ Found {result[\"matching_sequences\"]} sequences with GGGGGGGG')
    print(f'      Match rate: {result[\"match_percentage\"]}%')
    if result['sample_matches']:
        top = result['sample_matches'][0]
        print(f'      Top match: {top[\"sequence_id\"]}')
        print(f'        Forward: {top[\"match_count\"]} occurrences')
        print(f'        Reverse: {top[\"rev_comp_count\"]} occurrences')
        print(f'        Total: {top[\"total_match_count\"]} occurrences')
    print(f'      Reverse complement pattern: {result[\"reverse_complement_pattern\"]}')
else:
    print(f'    ✗ Error: {data.get(\"message\", \"Unknown error\")}')
    sys.exit(1)
"
echo ""

echo "✓ All searches complete"
echo ""

# Step 3: Generate summary
echo -e "${GREEN}[Step 3/3] Generating summary report...${NC}"

# Create summary report
cat > $OUTPUT_DIR/SEARCH_SUMMARY.md << 'EOF'
# OpenGenome2 Sequence Search Demonstration

**Date:** DATE_PLACEHOLDER

## Overview
This demonstration showcases the sequence search functionality using the OpenGenome2 Web API.

---

## Search Results

### 1. Pattern: AAAA (Homopolymer)
**File:** `search_AAAA.json`

- **Pattern Type:** Adenine homopolymer (4 consecutive A's)
- **Biological Significance:** Common in AT-rich regions, potential poly-A signals
- **Results:** See JSON file for complete data

### 2. Pattern: ACGT (All Four Bases)
**File:** `search_ACGT.json`

- **Pattern Type:** Mixed base composition
- **Biological Significance:** Represents balanced GC content, common in coding regions
- **Results:** See JSON file for complete data

### 3. Pattern: GGGGGGGG (Long G-run)
**File:** `search_GGGGGGGG.json`

- **Pattern Type:** Guanine homopolymer (8 consecutive G's)
- **Reverse Complement:** CCCCCCCC (searched both strands)
- **Biological Significance:** 
  - Potential G-quadruplex forming sequence
  - Found in telomeres and regulatory regions
  - May affect DNA stability and gene expression
- **Results:** See JSON file for complete data

---

## API Endpoint Used

```
POST http://localhost:5002/api/analyze/search
```

**Request Parameters:**
- `pattern`: DNA sequence to search for
- `input_dir`: Path to parquet data
- `case_sensitive`: Boolean (false for all searches)
- `reverse_complement`: Boolean (true for GGGGGGGG search)
- `max_results`: Maximum sequences to return (10)

---

## Output Files

```
results/demo/api_searches/
├── search_AAAA.json           # JSON results for AAAA pattern
├── search_ACGT.json           # JSON results for ACGT pattern
├── search_GGGGGGGG.json       # JSON results for GGGGGGGG pattern
└── SEARCH_SUMMARY.md          # This summary file
```

---

## Next Steps

1. **Explore Results:** Open JSON files to see detailed match information
2. **Web UI:** Visit http://localhost:5002/search for interactive searching
3. **Custom Searches:** Use the API or web UI to search for:
   - Restriction sites (e.g., EcoRI: GAATTC)
   - Promoter motifs (e.g., TATA box: TATAAA)
   - Start/stop codons (ATG, TAA, TAG, TGA)
   - Palindromic sequences
   - Any custom DNA pattern

---

## Understanding Results

Each JSON file contains:
- `pattern`: The searched pattern
- `matching_sequences`: Number of sequences containing the pattern
- `total_sequences_searched`: Total dataset size
- `match_percentage`: Percentage of sequences with matches
- `sample_matches`: Top 10 sequences with detailed information:
  - `sequence_id`: Sequence identifier
  - `description`: Sequence description
  - `match_count`: Number of pattern occurrences
  - `match_position`: Position of first match
  - `sequence_length`: Total sequence length
  - `pattern_coverage`: Percentage of sequence covered by pattern

For reverse complement searches, additional fields:
- `rev_comp_count`: Matches on reverse strand
- `total_match_count`: Combined forward + reverse matches
- `reverse_complement_pattern`: The reverse complement searched

---

**End of Demonstration**
EOF

# Replace date placeholder
CURRENT_DATE=$(date +"%Y-%m-%d %H:%M:%S")
sed -i.bak "s/DATE_PLACEHOLDER/$CURRENT_DATE/" $OUTPUT_DIR/SEARCH_SUMMARY.md
rm -f $OUTPUT_DIR/SEARCH_SUMMARY.md.bak

echo "✓ Summary report generated: $OUTPUT_DIR/SEARCH_SUMMARY.md"
echo ""

# Final summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Demonstration Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}Results Summary:${NC}"
echo "  • Searches performed: 3"
echo "  • Patterns tested: AAAA, ACGT, GGGGGGGG"
echo "  • Reverse complement: Used for GGGGGGGG"
echo ""
echo -e "${YELLOW}Output Location:${NC}"
echo "  • Results: $OUTPUT_DIR/"
echo "  • Summary: $OUTPUT_DIR/SEARCH_SUMMARY.md"
echo ""
echo -e "${YELLOW}View Results:${NC}"
echo "  • Summary: cat $OUTPUT_DIR/SEARCH_SUMMARY.md"
echo "  • JSON files: ls -l $OUTPUT_DIR/*.json"
echo "  • Web UI: http://localhost:5002/search"
echo ""
echo -e "${GREEN}✓ All searches completed successfully!${NC}"
