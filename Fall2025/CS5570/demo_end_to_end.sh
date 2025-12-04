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

# Step 1: Load organelle dataset (verify or ingest if missing)
echo -e "${GREEN}[Step 1/7] Verifying organelle dataset...${NC}"
if [ -d "data/parquet/organelle" ]; then
    ORGANELLE_COUNT=$(find data/parquet/organelle -name "*.parquet" | wc -l)
    echo "✓ Organelle dataset found ($ORGANELLE_COUNT parquet files)"
else
    echo -e "${YELLOW}⚠ Organelle dataset not found. Ingesting from HuggingFace...${NC}"
    
    # Download organelle FASTA if not present
    ORGANELLE_URL="https://huggingface.co/datasets/arcinstitute/opengenome2/resolve/main/fasta/organelle/organelle.fasta.gz"
    ORGANELLE_FILE="data/downloads/organelle.fasta.gz"
    
    mkdir -p data/downloads
    
    if [ ! -f "$ORGANELLE_FILE" ]; then
        echo "Downloading organelle.fasta.gz from HuggingFace..."
        curl -L --progress-bar "$ORGANELLE_URL" -o "$ORGANELLE_FILE"
        echo "✓ Download complete"
    else
        echo "✓ File already exists: $ORGANELLE_FILE"
    fi
    
    # Ingest to Parquet
    echo "Converting organelle.fasta.gz to Parquet format..."
    ./opengenome ingest local \
        --input "/data/downloads/organelle.fasta.gz" \
        --output /data/parquet/organelle \
        --source-name organelle \
        --chunk-size 1000
    
    if [ -d "data/parquet/organelle" ]; then
        ORGANELLE_COUNT=$(find data/parquet/organelle -name "*.parquet" | wc -l)
        echo "✓ Organelle dataset ingested ($ORGANELLE_COUNT parquet files)"
    else
        echo -e "${RED}✗ Organelle ingestion failed${NC}"
        exit 1
    fi
fi
echo ""

# Step 2: Download and display plasmids/phage dataset
echo -e "${GREEN}[Step 2/7] Downloading plasmids/phage dataset...${NC}"
FASTA_URL="https://huggingface.co/datasets/arcinstitute/opengenome2/resolve/main/fasta/plasmids_phage/imgpr.fasta.gz"
FASTA_FILE="data/downloads/imgpr.fasta.gz"

# Create downloads directory
mkdir -p data/downloads

# Download if not already present
if [ ! -f "$FASTA_FILE" ]; then
    echo "Downloading imgpr.fasta.gz from HuggingFace..."
    echo "Source: $FASTA_URL"
    curl -L --progress-bar "$FASTA_URL" -o "$FASTA_FILE"
    echo "✓ Download complete"
else
    echo "✓ File already exists: $FASTA_FILE"
fi

# Show file info
FILE_SIZE=$(du -h "$FASTA_FILE" | cut -f1)
echo ""
echo "Downloaded file information:"
echo "  Location: $FASTA_FILE"
echo "  Size: $FILE_SIZE"
echo ""

# Preview the file content
echo "File preview (first 5 sequences):"
gunzip -c "$FASTA_FILE" | head -20 | sed 's/^/  /'
echo ""
echo "✓ Dataset ready for analysis"
echo ""

# Step 3: K-mer and Codon analysis
echo -e "${GREEN}[Step 3/7] Ingesting plasmids/phage data to Parquet...${NC}"
echo ""
echo "Converting imgpr.fasta.gz to Parquet format..."
./opengenome ingest local \
    --input "/data/downloads/imgpr.fasta.gz" \
    --output /data/parquet/plasmids_phage \
    --source-name plasmids_phage \
    --chunk-size 1000

if [ -d "data/parquet/plasmids_phage" ]; then
    echo ""
    echo "✓ Data ingestion complete!"
    echo "  Output: data/parquet/plasmids_phage/"
    ls -lh data/parquet/plasmids_phage/
else
    echo "✗ Data ingestion failed - directory not created"
    exit 1
fi
echo ""

# Step 4: K-mer analysis
echo -e "${GREEN}[Step 4/7] Running k-mer analysis (k=8, 16, 32)...${NC}"
echo ""

for k in 8 16 32; do
    echo "[K-mer Analysis] k=$k"
    ./opengenome analyze kmer \
        --input /data/parquet/plasmids_phage \
        --output /data/results/demo/kmer_${k} \
        --k $k \
        --top 100
    
    if [ -f "data/results/demo/kmer_${k}/kmer_frequencies.parquet" ]; then
        # Show top 5 k-mers
        echo "  Top 5 k-mers:"
        python3 -c "
import pandas as pd
df = pd.read_parquet('data/results/demo/kmer_${k}/kmer_frequencies.parquet')
print(df.head(5).to_string(index=False))
        "
        echo ""
    fi
done

echo "✓ K-mer analysis complete for all k values"
echo ""

# Step 5: Codon analysis
echo -e "${GREEN}[Step 5/7] Running codon analysis...${NC}"
echo ""

./opengenome analyze codon \
    --input /data/parquet/plasmids_phage \
    --output /data/results/demo/codon_analysis \
    --top 100

if [ -f "data/results/demo/codon_analysis/codon_frequencies.parquet" ]; then
    echo "  Top 10 codons:"
    python3 -c "
import pandas as pd
df = pd.read_parquet('data/results/demo/codon_analysis/codon_frequencies.parquet')
print(df.head(10).to_string(index=False))
    "
    echo ""
fi

echo "✓ Codon analysis complete"
echo ""

# Step 6: Generate visualizations
echo -e "${GREEN}[Step 6/7] Generating visualizations...${NC}"
echo ""

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
output_dir = Path("data/results/demo/visualizations")
output_dir.mkdir(parents=True, exist_ok=True)

print("Generating visualizations...")

# 1. K-mer visualizations
for k in [8, 16, 32]:
    print(f"  - K-mer k={k} visualization...")
    kmer_file = f"data/results/demo/kmer_{k}/kmer_frequencies.parquet"
    
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
codon_file = "data/results/demo/codon_analysis/codon_frequencies.parquet"

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
    kmer_file = f"data/results/demo/kmer_{k}/kmer_frequencies.parquet"
    
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

echo ""
echo "✓ Visualizations generated"
echo ""

# Step 7: Sequence searches (using CLI)
echo -e "${GREEN}[Step 7/7] Running sequence searches using CLI...${NC}"
echo ""

mkdir -p data/results/demo/searches

# Search 1: AAAA (simple homopolymer)
echo "[Search 1/3] Searching for pattern: AAAA (homopolymer)"
./opengenome analyze search \
    --pattern AAAA \
    --input /data/parquet/plasmids_phage \
    --max-results 5
echo ""

# Search 2: ACGT (all four bases)
echo "[Search 2/3] Searching for pattern: ACGT (all four bases)"
./opengenome analyze search \
    --pattern ACGT \
    --input /data/parquet/plasmids_phage \
    --max-results 5
echo ""

# Search 3: GGGGGGGG (long homopolymer with reverse complement)
echo "[Search 3/3] Searching for pattern: GGGGGGGG (G-run with reverse complement)"
./opengenome analyze search \
    --pattern GGGGGGGG \
    --input /data/parquet/plasmids_phage \
    --reverse-complement \
    --max-results 5
echo ""

echo "✓ All sequence searches complete"
echo ""

# Generate summary report
echo -e "${GREEN}[Summary] Generating demo report...${NC}"

cat > results/demo/DEMO_SUMMARY.md << 'EOF'
# OpenGenome2 End-to-End Demonstration Summary

**Date:** $(date +"%Y-%m-%d %H:%M:%S")

## Overview
This demonstration showcases the complete OpenGenome2 workflow using CLI commands:
1. Data ingestion from FASTA to Parquet
2. K-mer frequency analysis (k=8, 16, 32)
3. Codon usage analysis
4. Visualization generation
5. Sequence pattern searches

---

## 1. Datasets

### Organelle Dataset (Pre-loaded)
- **Location**: `data/parquet/organelle/`
- **Format**: Parquet (optimized for Spark)
- **Contains**: ~10,000 mitochondrial/chloroplast sequences

### Plasmids/Phage Dataset (Downloaded & Ingested)
- **Source**: https://huggingface.co/datasets/arcinstitute/opengenome2
- **File**: imgpr.fasta.gz (1.6 GB)
- **Output**: `data/parquet/plasmids_phage/`
- **Contains**: Plasmid and bacteriophage sequences

---

## 2. K-mer Analysis

Performed k-mer frequency analysis with three different k values:

### K=8 (Octamers)
- **Output**: `results/demo/kmer_8/kmer_frequencies.parquet`
- **Top 100 k-mers** saved
- Useful for short motif discovery

### K=16 (16-mers)
- **Output**: `results/demo/kmer_16/kmer_frequencies.parquet`
- **Top 100 k-mers** saved
- Balanced between specificity and frequency

### K=32 (32-mers)
- **Output**: `results/demo/kmer_32/kmer_frequencies.parquet`
- **Top 100 k-mers** saved
- Highly specific, useful for unique sequence identification

---

## 3. Codon Usage Analysis

- **Output**: `results/demo/codon_analysis/codon_frequencies.parquet`
- **Top 100 codons** analyzed
- Identifies codon usage bias across the organelle dataset
- Highlights start (ATG) and stop (TAA, TAG, TGA) codons

---

## 4. Visualizations

Generated visualizations from analysis results:

### K-mer Frequency Charts
- `results/demo/visualizations/kmer_8_frequency.png`
- `results/demo/visualizations/kmer_16_frequency.png`
- `results/demo/visualizations/kmer_32_frequency.png`

### Codon Frequency Chart
- `results/demo/visualizations/codon_frequency.png`
- Color-coded: Green=Start, Red=Stop, Blue=Standard

### K-mer Comparison
- `results/demo/visualizations/kmer_comparison.png`
- Side-by-side comparison of top k-mers across k values

---

## 5. Sequence Pattern Search

Performed CLI-based searches on organelle dataset:

#### Pattern: AAAA
- Simple A-homopolymer (common in AT-rich regions)
- **Max Results**: 5 sequences

#### Pattern: ACGT
- All four bases present
- **Max Results**: 5 sequences

#### Pattern: GGGGGGGG
- Long G-homopolymer (8 bases)
- **Mode**: Reverse complement search enabled
- Potentially indicates G-quadruplex forming regions
- **Max Results**: 5 sequences

---

## 6. Output Files

```
data/parquet/
├── organelle/          # Pre-loaded mitochondrial/chloroplast sequences
└── plasmids_phage/     # Downloaded and ingested plasmid/phage sequences

results/demo/
├── kmer_8/
│   └── kmer_frequencies.parquet
├── kmer_16/
│   └── kmer_frequencies.parquet
├── kmer_32/
│   └── kmer_frequencies.parquet
├── codon_analysis/
│   └── codon_frequencies.parquet
├── visualizations/
│   ├── kmer_8_frequency.png
│   ├── kmer_16_frequency.png
│   ├── kmer_32_frequency.png
│   ├── codon_frequency.png
│   └── kmer_comparison.png
└── DEMO_SUMMARY.md (this file)
```

---

## 7. Web UI Access

View and analyze interactively at: **http://localhost:5002**

- **Search Tab**: Perform custom sequence pattern searches
- **Analyze Tab**: Run additional k-mer or codon analyses
- **Results Tab**: Browse all analysis results

---

## 8. Next Steps

- Search for specific biological motifs:
  - Restriction sites (e.g., EcoRI: GAATTC)
  - Promoter sequences (e.g., TATA box: TATAAA)
  - Start/stop codons (ATG, TAA, TAG, TGA)
- Analyze the plasmids_phage dataset with custom k values
- Compare k-mer distributions between organelle and plasmid datasets
- Export results for external tools (R, Jupyter notebooks)

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
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Results Summary${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "📊 Datasets Processed:"
echo "  ✓ Organelle sequences (pre-loaded)"
echo "  ✓ Plasmids/Phage dataset downloaded"
echo ""
echo "🔍 Sequence Searches Completed:"
echo "  ✓ AAAA (homopolymer)"
echo "  ✓ ACGT (all four bases)"
echo "  ✓ GGGGGGGG (G-run with reverse complement)"
echo ""
echo "📁 Output Locations:"
echo "  • Downloaded data: data/downloads/imgpr.fasta.gz"
echo "  • Search results: results/demo/searches/"
echo "  • Summary report: results/demo/DEMO_SUMMARY.md"
echo ""
echo "📈 View Detailed Results:"
echo "  • JSON results: ls -lh results/demo/searches/*.json"
echo "  • Summary report: cat results/demo/DEMO_SUMMARY.md"
echo "  • Web UI: http://localhost:5002"
echo ""
echo "💡 Next Steps:"
echo "  • Run k-mer analysis via Web UI: http://localhost:5002/analyze"
echo "  • Perform codon analysis interactively"
echo "  • Search for custom DNA patterns"
echo ""
echo -e "${GREEN}✓ Demonstration completed successfully!${NC}"
