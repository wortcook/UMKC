#!/bin/bash
#
# OpenGenome K=18 K-mer Analysis Script
# This script runs a deep k-mer analysis with k=18 on the organelle dataset
# Includes visualizations and comprehensive statistics
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
echo -e "${BLUE}OpenGenome K=18 K-mer Analysis${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Configuration:"
echo "  K value: 18"
echo "  Dataset: Organelle sequences (~2.8B bases)"
echo "  Expected runtime: ~45-60 minutes"
echo "  Expected unique k-mers: ~400-500 million"
echo ""

# Step 1: Verify dataset exists
echo -e "${GREEN}[Step 1/4] Verifying organelle dataset...${NC}"
if [ -d "data/parquet/organelle" ]; then
    ORGANELLE_COUNT=$(find data/parquet/organelle -name "*.parquet" 2>/dev/null | wc -l | tr -d ' ')
    if [ "$ORGANELLE_COUNT" -gt 0 ]; then
        echo "✓ Organelle dataset found ($ORGANELLE_COUNT parquet files)"
    else
        echo -e "${RED}✗ Organelle directory exists but is empty${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ Organelle dataset not found. Run demo_end_to_end.sh first${NC}"
    exit 1
fi
echo ""

# Step 2: Run K=18 analysis
echo -e "${GREEN}[Step 2/4] Running k=18 k-mer analysis...${NC}"
echo "NOTE: This analysis will take approximately 45-60 minutes"
echo "      Using RDD MapReduce approach with partition-level pre-aggregation"
echo "      For k=18, there are 4^18 = 68,719,476,736 possible k-mers"
echo ""
START_TIME=$(date +%s)
START_TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
echo "Started at: $START_TIMESTAMP"
echo ""

./opengenome analyze kmer \
    --input /data/parquet/organelle \
    --output /results/demo/kmer_18 \
    --k 18 \
    --min-count 10 \
    --top 20

END_TIME=$(date +%s)
END_TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
ELAPSED=$((END_TIME - START_TIME))
ELAPSED_MIN=$((ELAPSED / 60))
ELAPSED_SEC=$((ELAPSED % 60))

echo ""
echo "Completed at: $END_TIMESTAMP"
echo "Total runtime: ${ELAPSED_MIN} minutes ${ELAPSED_SEC} seconds"

if [ -d "results/demo/kmer_18" ]; then
    echo ""
    echo "✓ K=18 k-mer analysis complete!"
    echo "  Output: results/demo/kmer_18/"
else
    echo -e "${RED}✗ K=18 k-mer analysis failed${NC}"
    exit 1
fi
echo ""

# Step 3: Generate comprehensive statistics and visualizations
echo -e "${GREEN}[Step 3/4] Generating statistics and visualizations...${NC}"
echo ""

cat > /tmp/kmer18_analysis.py << 'VIZEOF'
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path
from datetime import datetime

sns.set_theme(style="whitegrid")

# Output directories
output_dir = Path("/results/demo/kmer_18")
viz_dir = output_dir / "visualizations"
viz_dir.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("K=18 K-MER ANALYSIS - COMPREHENSIVE REPORT")
print("=" * 70)
print()

# Load results
print("Loading k-mer results...")
df = pd.read_parquet(output_dir)
print(f"Loaded {len(df):,} k-mers from parquet")
print()

# Global statistics
print("=" * 70)
print("GLOBAL STATISTICS")
print("=" * 70)
total_unique = len(df)
total_count = df['count'].sum()
mean_freq = df['count'].mean()
median_freq = df['count'].median()
std_freq = df['count'].std()
max_freq = df['count'].max()
min_freq = df['count'].min()
max_possible = 4 ** 18

print(f"  Dataset: Organelle sequences")
print(f"  K value: 18")
print(f"  Minimum count threshold: 10")
print()
print(f"  Unique 18-mers found: {total_unique:,}")
print(f"  Theoretical maximum (4^18): {max_possible:,}")
print(f"  Saturation: {total_unique/max_possible*100:.4f}%")
print()
print(f"  Total occurrences: {total_count:,}")
print(f"  Mean frequency: {mean_freq:,.2f}")
print(f"  Median frequency: {median_freq:,.2f}")
print(f"  Std deviation: {std_freq:,.2f}")
print(f"  Max frequency: {max_freq:,}")
print(f"  Min frequency: {min_freq:,}")
print()

# Distribution statistics
q25 = df['count'].quantile(0.25)
q75 = df['count'].quantile(0.75)
q90 = df['count'].quantile(0.90)
q95 = df['count'].quantile(0.95)
q99 = df['count'].quantile(0.99)

print("  Frequency Percentiles:")
print(f"    25th percentile: {q25:,.0f}")
print(f"    50th percentile (median): {median_freq:,.0f}")
print(f"    75th percentile: {q75:,.0f}")
print(f"    90th percentile: {q90:,.0f}")
print(f"    95th percentile: {q95:,.0f}")
print(f"    99th percentile: {q99:,.0f}")
print()

# Top 20 k-mers table
print("=" * 70)
print("TOP 20 K-MERS BY FREQUENCY")
print("=" * 70)
df_top20 = df.nlargest(20, 'count').reset_index(drop=True)
print()
print(f"{'Rank':<6} {'18-mer':<22} {'Count':>15} {'% of Total':>12}")
print("-" * 60)
for i, row in df_top20.iterrows():
    pct = row['count'] / total_count * 100
    print(f"{i+1:<6} {row['kmer']:<22} {row['count']:>15,} {pct:>11.4f}%")
print()

# Base composition analysis
print("=" * 70)
print("BASE COMPOSITION ANALYSIS (Top 20 k-mers)")
print("=" * 70)
base_counts = {'A': 0, 'T': 0, 'G': 0, 'C': 0}
for kmer in df_top20['kmer']:
    for base in kmer:
        if base in base_counts:
            base_counts[base] += 1

total_bases = sum(base_counts.values())
print(f"  A: {base_counts['A']:>4} ({base_counts['A']/total_bases*100:.1f}%)")
print(f"  T: {base_counts['T']:>4} ({base_counts['T']/total_bases*100:.1f}%)")
print(f"  G: {base_counts['G']:>4} ({base_counts['G']/total_bases*100:.1f}%)")
print(f"  C: {base_counts['C']:>4} ({base_counts['C']/total_bases*100:.1f}%)")
print(f"  AT content: {(base_counts['A']+base_counts['T'])/total_bases*100:.1f}%")
print(f"  GC content: {(base_counts['G']+base_counts['C'])/total_bases*100:.1f}%")
print()

# ============================================================
# VISUALIZATION 1: Top 20 K-mer Bar Chart
# ============================================================
print("Generating visualizations...")
print("  [1/4] Top 20 k-mer frequency bar chart...")

fig, ax = plt.subplots(figsize=(16, 8))
colors = plt.cm.viridis(np.linspace(0.2, 0.8, 20))
bars = ax.bar(range(20), df_top20['count'], color=colors, edgecolor='black', linewidth=0.5)

ax.set_xlabel('18-mer', fontsize=14, fontweight='bold')
ax.set_ylabel('Frequency', fontsize=14, fontweight='bold')
ax.set_title('Top 20 18-mer Frequencies\nOrganelle Dataset (~2.8B bases)', fontsize=16, fontweight='bold')
ax.set_xticks(range(20))
ax.set_xticklabels(df_top20['kmer'], rotation=45, ha='right', fontsize=10, family='monospace')
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format(int(x), ',')))

# Add value labels on bars
for i, (bar, val) in enumerate(zip(bars, df_top20['count'])):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max_freq*0.01, 
            f'{val:,}', ha='center', va='bottom', fontsize=8, rotation=90)

plt.tight_layout()
plt.savefig(viz_dir / 'kmer_18_top20_barchart.png', dpi=300, bbox_inches='tight')
plt.close()
print("    Saved: kmer_18_top20_barchart.png")

# ============================================================
# VISUALIZATION 2: Frequency Distribution Histogram
# ============================================================
print("  [2/4] Frequency distribution histogram...")

fig, axes = plt.subplots(1, 2, figsize=(16, 6))

# Log-scale histogram
ax1 = axes[0]
# Sample for histogram if too many points
if len(df) > 1000000:
    df_sample = df.sample(n=1000000, random_state=42)
else:
    df_sample = df
    
ax1.hist(df_sample['count'], bins=100, color='steelblue', edgecolor='black', linewidth=0.3, alpha=0.7)
ax1.set_xlabel('Frequency', fontsize=12, fontweight='bold')
ax1.set_ylabel('Number of K-mers', fontsize=12, fontweight='bold')
ax1.set_title('K-mer Frequency Distribution (Linear Scale)', fontsize=14, fontweight='bold')
ax1.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format(int(x), ',')))
ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format(int(x), ',')))

# Log-log histogram
ax2 = axes[1]
log_counts = np.log10(df_sample['count'] + 1)
ax2.hist(log_counts, bins=100, color='coral', edgecolor='black', linewidth=0.3, alpha=0.7)
ax2.set_xlabel('Log10(Frequency)', fontsize=12, fontweight='bold')
ax2.set_ylabel('Number of K-mers', fontsize=12, fontweight='bold')
ax2.set_title('K-mer Frequency Distribution (Log Scale)', fontsize=14, fontweight='bold')
ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format(int(x), ',')))

plt.tight_layout()
plt.savefig(viz_dir / 'kmer_18_distribution.png', dpi=300, bbox_inches='tight')
plt.close()
print("    Saved: kmer_18_distribution.png")

# ============================================================
# VISUALIZATION 3: Base Composition Pie Chart
# ============================================================
print("  [3/4] Base composition pie chart...")

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Pie chart for top 20 k-mers base composition
ax1 = axes[0]
colors_pie = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
wedges, texts, autotexts = ax1.pie(
    [base_counts['A'], base_counts['T'], base_counts['G'], base_counts['C']],
    labels=['A', 'T', 'G', 'C'],
    colors=colors_pie,
    autopct='%1.1f%%',
    startangle=90,
    explode=(0.02, 0.02, 0.02, 0.02)
)
ax1.set_title('Base Composition\n(Top 20 K-mers)', fontsize=14, fontweight='bold')

# AT vs GC bar chart
ax2 = axes[1]
at_content = (base_counts['A'] + base_counts['T']) / total_bases * 100
gc_content = (base_counts['G'] + base_counts['C']) / total_bases * 100
bars = ax2.bar(['AT Content', 'GC Content'], [at_content, gc_content], 
               color=['#FF6B6B', '#45B7D1'], edgecolor='black', linewidth=1)
ax2.set_ylabel('Percentage (%)', fontsize=12, fontweight='bold')
ax2.set_title('AT vs GC Content\n(Top 20 K-mers)', fontsize=14, fontweight='bold')
ax2.set_ylim(0, 100)
for bar, val in zip(bars, [at_content, gc_content]):
    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, 
             f'{val:.1f}%', ha='center', va='bottom', fontsize=14, fontweight='bold')

plt.tight_layout()
plt.savefig(viz_dir / 'kmer_18_base_composition.png', dpi=300, bbox_inches='tight')
plt.close()
print("    Saved: kmer_18_base_composition.png")

# ============================================================
# VISUALIZATION 4: Cumulative Distribution
# ============================================================
print("  [4/4] Cumulative distribution curve...")

fig, ax = plt.subplots(figsize=(12, 6))

# Sort by count and compute cumulative
df_sorted = df.sort_values('count', ascending=False).reset_index(drop=True)
df_sorted['cumulative_pct'] = df_sorted['count'].cumsum() / total_count * 100
df_sorted['rank_pct'] = (df_sorted.index + 1) / len(df_sorted) * 100

# Sample for plotting if too many points
if len(df_sorted) > 10000:
    sample_idx = np.logspace(0, np.log10(len(df_sorted)-1), 10000).astype(int)
    sample_idx = np.unique(sample_idx)
    df_plot = df_sorted.iloc[sample_idx]
else:
    df_plot = df_sorted

ax.plot(df_plot['rank_pct'], df_plot['cumulative_pct'], color='darkblue', linewidth=2)
ax.fill_between(df_plot['rank_pct'], df_plot['cumulative_pct'], alpha=0.3, color='steelblue')
ax.set_xlabel('Cumulative % of K-mers (ranked by frequency)', fontsize=12, fontweight='bold')
ax.set_ylabel('Cumulative % of Total Occurrences', fontsize=12, fontweight='bold')
ax.set_title('K-mer Frequency Cumulative Distribution\n(Pareto Analysis)', fontsize=14, fontweight='bold')
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.grid(True, alpha=0.3)

# Add reference lines
ax.axhline(y=50, color='red', linestyle='--', alpha=0.5, label='50% of occurrences')
ax.axhline(y=80, color='orange', linestyle='--', alpha=0.5, label='80% of occurrences')
ax.legend(loc='lower right')

plt.tight_layout()
plt.savefig(viz_dir / 'kmer_18_cumulative.png', dpi=300, bbox_inches='tight')
plt.close()
print("    Saved: kmer_18_cumulative.png")

print()
print("=" * 70)
print("VISUALIZATION FILES GENERATED")
print("=" * 70)
print(f"  Location: {viz_dir}")
print("  Files:")
print("    - kmer_18_top20_barchart.png    (Top 20 k-mers bar chart)")
print("    - kmer_18_distribution.png      (Frequency distribution)")
print("    - kmer_18_base_composition.png  (Base composition analysis)")
print("    - kmer_18_cumulative.png        (Cumulative distribution)")
print()

# Save statistics to JSON
import json
stats = {
    'k': 18,
    'dataset': 'organelle',
    'timestamp': datetime.now().isoformat(),
    'unique_kmers': int(total_unique),
    'total_occurrences': int(total_count),
    'theoretical_max': int(max_possible),
    'saturation_pct': float(total_unique/max_possible*100),
    'mean_frequency': float(mean_freq),
    'median_frequency': float(median_freq),
    'std_frequency': float(std_freq),
    'max_frequency': int(max_freq),
    'min_frequency': int(min_freq),
    'percentiles': {
        'p25': float(q25),
        'p50': float(median_freq),
        'p75': float(q75),
        'p90': float(q90),
        'p95': float(q95),
        'p99': float(q99)
    },
    'top_20': [{'kmer': row['kmer'], 'count': int(row['count'])} for _, row in df_top20.iterrows()]
}

with open(output_dir / 'statistics.json', 'w') as f:
    json.dump(stats, f, indent=2)
print(f"Statistics saved to: {output_dir / 'statistics.json'}")
print()
print("=" * 70)
print("ANALYSIS COMPLETE")
print("=" * 70)
VIZEOF

# Copy script to web container and run
docker cp /tmp/kmer18_analysis.py opengenome-web:/tmp/kmer18_analysis.py
docker exec opengenome-web python3 /tmp/kmer18_analysis.py

echo ""
echo "✓ Statistics and visualizations generated"
echo ""

# Step 4: Copy visualizations to local results
echo -e "${GREEN}[Step 4/4] Finalizing output...${NC}"
echo ""

# List generated files
echo "Generated files:"
ls -lh results/demo/kmer_18/
echo ""
echo "Visualizations:"
ls -lh results/demo/kmer_18/visualizations/ 2>/dev/null || echo "  (in container)"
echo ""

# Final summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}K=18 Analysis Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Runtime: ${ELAPSED_MIN} minutes ${ELAPSED_SEC} seconds"
echo ""
echo "📁 Output Files:"
echo "  • K-mer data: results/demo/kmer_18/*.parquet"
echo "  • Statistics: results/demo/kmer_18/statistics.json"
echo "  • Visualizations: results/demo/kmer_18/visualizations/"
echo ""
echo "📊 Visualization Files:"
echo "  • kmer_18_top20_barchart.png    - Top 20 k-mers bar chart"
echo "  • kmer_18_distribution.png      - Frequency distribution"
echo "  • kmer_18_base_composition.png  - Base composition analysis"
echo "  • kmer_18_cumulative.png        - Cumulative distribution"
echo ""
echo -e "${GREEN}✓ K=18 k-mer analysis completed successfully!${NC}"
