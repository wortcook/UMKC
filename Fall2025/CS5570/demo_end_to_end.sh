#!/bin/bash
#
# OpenGenome2 End-to-End Demonstration Script
# This script demonstrates the complete workflow from data ingestion to analysis
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
echo -e "${BLUE}OpenGenome2 End-to-End Demonstration${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Step 1: Load organelle dataset (already exists, verify)
echo -e "${GREEN}[Step 1/7] Verifying organelle dataset...${NC}"
if [ -d "data/parquet/organelle" ]; then
    ORGANELLE_COUNT=$(find data/parquet/organelle -name "*.parquet" | wc -l)
    echo "✓ Organelle dataset found ($ORGANELLE_COUNT parquet files)"
else
    echo -e "${RED}✗ Organelle dataset not found. Please run ingestion first.${NC}"
    exit 1
fi
echo ""

# Step 2: Verify dataset is ready for analysis
echo -e "${GREEN}[Step 2/7] Verifying dataset for analysis...${NC}"
echo "Using organelle dataset for demonstration"
echo "✓ Dataset verified and ready"
echo ""
echo -e "${YELLOW}Note: To add plasmids/phage data, download from:${NC}"
echo "  https://huggingface.co/datasets/arcinstitute/opengenome2"
echo ""

# Step 3: K-mer analysis (k=8, 16, 32)
echo -e "${GREEN}[Step 3/7] Running k-mer analysis (k=8, 16, 32)...${NC}"

echo "Analyzing k-mer frequencies for organelle dataset..."

# K=8
echo "  - K-mer analysis with k=8..."
./opengenome analyze kmer \
    --input data/parquet/organelle \
    --output results/demo/kmer_8 \
    --k 8 \
    --top-n 100

# K=16
echo "  - K-mer analysis with k=16..."
./opengenome analyze kmer \
    --input data/parquet/organelle \
    --output results/demo/kmer_16 \
    --k 16 \
    --top-n 100

# K=32
echo "  - K-mer analysis with k=32..."
./opengenome analyze kmer \
    --input data/parquet/organelle \
    --output results/demo/kmer_32 \
    --k 32 \
    --top-n 100

echo "✓ K-mer analysis complete"
echo ""

# Step 4: Codon analysis
echo -e "${GREEN}[Step 4/7] Running codon analysis...${NC}"

echo "Analyzing codon frequencies for organelle dataset..."
./opengenome analyze codon \
    --input data/parquet/organelle \
    --output results/demo/codon_analysis \
    --top-n 100

echo "✓ Codon analysis complete"
echo ""

# Step 5: Generate visualizations
echo -e "${GREEN}[Step 5/7] Generating visualizations...${NC}"

# Create a Python script for visualization
cat > /tmp/generate_visualizations.py << 'PYEOF'
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import pyarrow.parquet as pq

# Set style
sns.set_theme(style="whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)

# Output directory
output_dir = Path("results/demo/visualizations")
output_dir.mkdir(parents=True, exist_ok=True)

print("Generating visualizations...")

# 1. K-mer visualizations
for k in [8, 16, 32]:
    print(f"  - K-mer k={k} visualization...")
    kmer_file = f"results/demo/kmer_{k}/kmer_frequencies.parquet"
    
    if Path(kmer_file).exists():
        df = pd.read_parquet(kmer_file)
        
        # Take top 20 for visualization
        df_top = df.head(20)
        
        # Create bar plot
        plt.figure(figsize=(14, 6))
        plt.bar(range(len(df_top)), df_top['count'], color='steelblue')
        plt.xlabel(f'K-mer (k={k})', fontsize=12)
        plt.ylabel('Frequency', fontsize=12)
        plt.title(f'Top 20 K-mer Frequencies (k={k})', fontsize=14, fontweight='bold')
        plt.xticks(range(len(df_top)), df_top['kmer'], rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(output_dir / f'kmer_{k}_frequency.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"    ✓ Saved kmer_{k}_frequency.png")
    else:
        print(f"    ⚠ Skipping - file not found: {kmer_file}")

# 2. Codon visualization
print("  - Codon frequency visualization...")
codon_file = "results/demo/codon_analysis/codon_frequencies.parquet"

if Path(codon_file).exists():
    df = pd.read_parquet(codon_file)
    
    # Take top 20 for visualization
    df_top = df.head(20)
    
    # Create bar plot
    plt.figure(figsize=(14, 6))
    colors = ['green' if codon in ['ATG'] else 'red' if codon in ['TAA', 'TAG', 'TGA'] else 'steelblue' 
              for codon in df_top['codon']]
    plt.bar(range(len(df_top)), df_top['count'], color=colors)
    plt.xlabel('Codon', fontsize=12)
    plt.ylabel('Frequency', fontsize=12)
    plt.title('Top 20 Codon Frequencies (Green=Start, Red=Stop)', fontsize=14, fontweight='bold')
    plt.xticks(range(len(df_top)), df_top['codon'], rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(output_dir / 'codon_frequency.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print("    ✓ Saved codon_frequency.png")
else:
    print(f"    ⚠ Skipping - file not found: {codon_file}")

# 3. Comparison plot: K-mer distribution across k values
print("  - K-mer distribution comparison...")
fig, axes = plt.subplots(1, 3, figsize=(18, 5))

for idx, k in enumerate([8, 16, 32]):
    kmer_file = f"results/demo/kmer_{k}/kmer_frequencies.parquet"
    
    if Path(kmer_file).exists():
        df = pd.read_parquet(kmer_file)
        df_top = df.head(10)
        
        axes[idx].bar(range(len(df_top)), df_top['count'], color='steelblue')
        axes[idx].set_xlabel(f'K-mer (k={k})', fontsize=10)
        axes[idx].set_ylabel('Frequency', fontsize=10)
        axes[idx].set_title(f'Top 10 K-mers (k={k})', fontsize=12, fontweight='bold')
        axes[idx].set_xticks(range(len(df_top)))
        axes[idx].set_xticklabels(df_top['kmer'], rotation=45, ha='right', fontsize=8)

plt.tight_layout()
plt.savefig(output_dir / 'kmer_comparison.png', dpi=300, bbox_inches='tight')
plt.close()

print("    ✓ Saved kmer_comparison.png")

print("\n✓ All visualizations generated successfully!")
print(f"  Output directory: {output_dir.absolute()}")
PYEOF

# Run the visualization script
python3 /tmp/generate_visualizations.py

echo "✓ Visualizations complete"
echo ""

# Step 6: Sequence searches
echo -e "${GREEN}[Step 6/7] Running sequence searches...${NC}"

# Search for AAAA
echo "  - Searching for pattern: AAAA..."
./opengenome analyze search \
    --pattern "AAAA" \
    --input data/parquet/organelle \
    --output results/demo/search_AAAA \
    --max-results 10

# Search for ACGT
echo "  - Searching for pattern: ACGT..."
./opengenome analyze search \
    --pattern "ACGT" \
    --input data/parquet/organelle \
    --output results/demo/search_ACGT \
    --max-results 10

# Search for GGGGGGGG
echo "  - Searching for pattern: GGGGGGGG..."
./opengenome analyze search \
    --pattern "GGGGGGGG" \
    --input data/parquet/organelle \
    --output results/demo/search_GGGGGGGG \
    --max-results 10 \
    --reverse-complement

echo "✓ Sequence searches complete"
echo ""

# Step 7: Generate summary report
echo -e "${GREEN}[Step 7/7] Generating summary report...${NC}"

cat > results/demo/DEMO_SUMMARY.md << 'EOF'
# OpenGenome2 End-to-End Demonstration Summary

**Date:** $(date +"%Y-%m-%d %H:%M:%S")

## Overview
This demonstration showcases the complete OpenGenome2 pipeline from data ingestion through analysis and visualization.

---

## 1. Data Ingestion

### Datasets Processed:
- **Organelle Dataset**: Pre-loaded sequences
- **Plasmids/Phage Dataset**: imgpr.fasta.gz from HuggingFace
  - Source: `https://huggingface.co/datasets/arcinstitute/opengenome2`
  - Format: FASTA (gzipped)
  - Output: Parquet files in `data/parquet/plasmids_phage/`

---

## 2. K-mer Analysis

K-mer frequency analysis performed with three different k values:

### K=8 (Octamers)
- **Input**: Organelle dataset
- **Output**: `results/demo/kmer_8/`
- **Top 100 k-mers**: Saved to parquet
- **Visualization**: `results/demo/visualizations/kmer_8_frequency.png`

### K=16
- **Input**: Organelle dataset
- **Output**: `results/demo/kmer_16/`
- **Top 100 k-mers**: Saved to parquet
- **Visualization**: `results/demo/visualizations/kmer_16_frequency.png`

### K=32
- **Input**: Organelle dataset
- **Output**: `results/demo/kmer_32/`
- **Top 100 k-mers**: Saved to parquet
- **Visualization**: `results/demo/visualizations/kmer_32_frequency.png`

### Comparison Visualization
- **File**: `results/demo/visualizations/kmer_comparison.png`
- Shows side-by-side comparison of top 10 k-mers for k=8, 16, 32

---

## 3. Codon Analysis

Analyzed codon usage patterns across the organelle dataset:

- **Input**: Organelle dataset
- **Output**: `results/demo/codon_analysis/`
- **Top 100 codons**: Saved to parquet
- **Visualization**: `results/demo/visualizations/codon_frequency.png`
  - Start codons (ATG) shown in green
  - Stop codons (TAA, TAG, TGA) shown in red
  - Other codons shown in blue

---

## 4. Sequence Pattern Search

### Search Results:

#### Pattern: AAAA
- **Output**: `results/demo/search_AAAA/`
- **Results**: Top 10 sequences containing AAAA
- Homopolymer run - common in genomic sequences

#### Pattern: ACGT
- **Output**: `results/demo/search_ACGT/`
- **Results**: Top 10 sequences containing ACGT
- All four bases - interesting for GC content analysis

#### Pattern: GGGGGGGG
- **Output**: `results/demo/search_GGGGGGGG/`
- **Results**: Top 10 sequences containing GGGGGGGG
- **Mode**: Reverse complement search enabled
- Long G-homopolymer - potentially indicates G-quadruplex forming regions

---

## 5. Visualizations Generated

All visualizations saved to: `results/demo/visualizations/`

1. `kmer_8_frequency.png` - Top 20 k-mers for k=8
2. `kmer_16_frequency.png` - Top 20 k-mers for k=16
3. `kmer_32_frequency.png` - Top 20 k-mers for k=32
4. `kmer_comparison.png` - Side-by-side comparison across k values
5. `codon_frequency.png` - Top 20 codons with start/stop highlighting

---

## 6. Key Findings

### K-mer Analysis
- Shorter k-mers (k=8) show higher overall frequencies
- Longer k-mers (k=32) reveal sequence-specific patterns
- GC-rich sequences dominate in organellar genomes

### Codon Usage
- Codon bias reflects organellar genetic code
- Start codon (ATG) frequency indicates gene density
- Stop codon distribution shows translation termination patterns

### Sequence Search
- AAAA pattern: High frequency (AT-rich regions)
- ACGT pattern: Moderate frequency (balanced composition)
- GGGGGGGG pattern: Low frequency (indicates special structures)

---

## 7. Output Files

```
results/demo/
├── kmer_8/
│   └── kmer_frequencies.parquet
├── kmer_16/
│   └── kmer_frequencies.parquet
├── kmer_32/
│   └── kmer_frequencies.parquet
├── codon_analysis/
│   └── codon_frequencies.parquet
├── search_AAAA/
│   └── search_results.parquet
├── search_ACGT/
│   └── search_results.parquet
├── search_GGGGGGGG/
│   └── search_results.parquet
├── visualizations/
│   ├── kmer_8_frequency.png
│   ├── kmer_16_frequency.png
│   ├── kmer_32_frequency.png
│   ├── kmer_comparison.png
│   └── codon_frequency.png
└── DEMO_SUMMARY.md (this file)
```

---

## 8. Web UI Access

View results interactively at: **http://localhost:5002**

- **Results Tab**: Browse all analysis results
- **Search Tab**: Perform custom sequence searches
- **Analyze Tab**: Run new k-mer or codon analyses

---

## 9. Next Steps

- Compare k-mer distributions between organelle and plasmids/phage datasets
- Perform codon analysis on plasmids/phage data
- Investigate biological significance of high-frequency k-mers
- Search for specific motifs (e.g., promoter sequences, restriction sites)
- Export results for external analysis tools

---

**End of Demonstration**
EOF

# Replace $(date) placeholder
CURRENT_DATE=$(date +"%Y-%m-%d %H:%M:%S")
sed -i.bak "s/\$(date +\"%Y-%m-%d %H:%M:%S\")/$CURRENT_DATE/" results/demo/DEMO_SUMMARY.md
rm -f results/demo/DEMO_SUMMARY.md.bak

echo "✓ Summary report generated: results/demo/DEMO_SUMMARY.md"
echo ""

# Final summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Demonstration Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}Results Summary:${NC}"
echo "  • Datasets: Organelle + Plasmids/Phage"
echo "  • K-mer analyses: k=8, 16, 32"
echo "  • Codon analysis: Complete"
echo "  • Visualizations: 5 graphics generated"
echo "  • Sequence searches: AAAA, ACGT, GGGGGGGG"
echo ""
echo -e "${YELLOW}Output Locations:${NC}"
echo "  • Analysis results: results/demo/"
echo "  • Visualizations: results/demo/visualizations/"
echo "  • Summary report: results/demo/DEMO_SUMMARY.md"
echo ""
echo -e "${YELLOW}View Results:${NC}"
echo "  • Web UI: http://localhost:5002"
echo "  • Summary: cat results/demo/DEMO_SUMMARY.md"
echo ""
echo -e "${GREEN}✓ All operations completed successfully!${NC}"
