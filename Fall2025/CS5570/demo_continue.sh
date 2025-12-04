#!/bin/bash
#
# OpenGenome2 Demo - Continue from Step 4
# Runs only the analysis steps (4-7) after successful data ingestion
#

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "============================================================"
echo "OpenGenome2 Demo - Continue Analysis (Steps 4-7)"
echo "============================================================"
echo ""

# Verify data exists
if [ ! -d "data/parquet/plasmids_phage" ]; then
    echo -e "${RED}✗ Plasmids/phage dataset not found!${NC}"
    echo "Please run the full demo first: ./demo_end_to_end.sh"
    exit 1
fi

echo "✓ Found plasmids/phage dataset ($(ls data/parquet/plasmids_phage/*.parquet | wc -l | tr -d ' ') shards)"
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
    
    if [ -f "results/demo/kmer_${k}/kmer_frequencies.parquet" ]; then
        # Show top 5 k-mers
        echo "  Top 5 k-mers:"
        python3 -c "
import pandas as pd
df = pd.read_parquet('results/demo/kmer_${k}/kmer_frequencies.parquet')
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

if [ -f "results/demo/codon_analysis/codon_frequencies.parquet" ]; then
    echo "  Top 10 codons:"
    python3 -c "
import pandas as pd
df = pd.read_parquet('results/demo/codon_analysis/codon_frequencies.parquet')
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
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Set style
sns.set_theme(style="whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)

# Output directory
output_dir = Path("results/demo/visualizations")
output_dir.mkdir(parents=True, exist_ok=True)

print("Generating visualizations...")

# 1. K-mer frequency distribution (k=8)
print("  - K-mer frequency distribution (k=8)...")
kmer_file = "results/demo/kmer_8/kmer_frequencies.parquet"

if Path(kmer_file).exists():
    df = pd.read_parquet(kmer_file)
    df_top = df.head(20)
    
    plt.figure(figsize=(14, 6))
    plt.bar(range(len(df_top)), df_top['count'], color='steelblue')
    plt.xlabel('K-mer (k=8)', fontsize=12)
    plt.ylabel('Frequency', fontsize=12)
    plt.title('Top 20 K-mer Frequencies (k=8)', fontsize=14, fontweight='bold')
    plt.xticks(range(len(df_top)), df_top['kmer'], rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(output_dir / 'kmer_8_frequency.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print("    ✓ Saved kmer_8_frequency.png")
else:
    print(f"    ⚠ Skipping - file not found: {kmer_file}")

# 2. Codon frequency
print("  - Codon frequency distribution...")
codon_file = "results/demo/codon_analysis/codon_frequencies.parquet"

if Path(codon_file).exists():
    df = pd.read_parquet(codon_file)
    df_top = df.head(20)
    
    plt.figure(figsize=(14, 6))
    
    # Color code: start (green), stop (red), others (blue)
    start_codons = {'ATG', 'GTG', 'TTG'}
    stop_codons = {'TAA', 'TAG', 'TGA'}
    colors = ['green' if codon in start_codons else 'red' if codon in stop_codons else 'steelblue'
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

echo ""
echo "✓ Visualizations generated"
echo ""

# Step 7: Sequence searches (using CLI)
echo -e "${GREEN}[Step 7/7] Running sequence searches using CLI...${NC}"
echo ""

mkdir -p results/demo/searches

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

# Final summary
echo "============================================================"
echo -e "${GREEN}Demo Analysis Complete!${NC}"
echo "============================================================"
echo ""
echo "Results available in: results/demo/"
echo ""
echo "Contents:"
echo "  - kmer_8/      : K-mer frequencies (k=8)"
echo "  - kmer_16/     : K-mer frequencies (k=16)"
echo "  - kmer_32/     : K-mer frequencies (k=32)"
echo "  - codon_analysis/  : Codon usage frequencies"
echo "  - visualizations/  : PNG charts"
echo "  - searches/        : Search results"
echo ""
