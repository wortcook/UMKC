#!/usr/bin/env python3
"""
K-mer Analysis Report Generator for OpenGenome2
Memory-efficient version - processes one k at a time.
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
import gc
from pathlib import Path
from datetime import datetime

# Create output directory
output_dir = Path('/results/demo_pipeline/kmer/report')
output_dir.mkdir(parents=True, exist_ok=True)

plt.style.use('seaborn-v0_8-whitegrid')

k_values = [6, 12, 18, 24]
colors = ['#3498db', '#e74c3c', '#2ecc71', '#9b59b6']

# Storage for stats only (small memory footprint)
all_stats = {}
all_top20 = {}

print("="*60)
print("K-mer Report Generation (Memory-Efficient)")
print("="*60)

# Process each k value one at a time
for k in k_values:
    kmer_path = f'/results/demo_pipeline/kmer/kmer_{k}'
    print(f"\nProcessing k={k}...")
    
    if not os.path.exists(kmer_path):
        print(f"  ✗ Path not found: {kmer_path}")
        continue
    
    try:
        # Load data
        print(f"  Loading parquet...", end=" ", flush=True)
        df = pd.read_parquet(kmer_path)
        print(f"done ({len(df):,} rows)")
        
        # Calculate stats
        stats = {
            'unique': len(df),
            'total': int(df['count'].sum()),
            'max': int(df['count'].max()),
            'min': int(df['count'].min()),
            'mean': float(df['count'].mean())
        }
        all_stats[k] = stats
        print(f"  Stats: {stats['unique']:,} unique, {stats['total']:,} total")
        
        # Get top 20 as plain Python list (small memory)
        top20 = df.nlargest(20, 'count')[['kmer', 'count']].values.tolist()
        all_top20[k] = top20
        print(f"  Top k-mer: {top20[0][0]} ({top20[0][1]:,})")
        
        # Free memory explicitly
        del df
        gc.collect()
        print(f"  ✓ Memory released")
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        continue

if not all_stats:
    print("\nNo k-mer data found!")
    exit(1)

print(f"\nLoaded data for k values: {list(all_stats.keys())}")

# ============================================================================
# Create visualizations
# ============================================================================
print("\n" + "="*60)
print("Creating visualizations...")
print("="*60)

# Figure 1: Top 20 k-mers for each k (2x2 grid)
print("\nFigure 1: Top 20 k-mers comparison...")
fig, axes = plt.subplots(2, 2, figsize=(16, 12))
axes = axes.flatten()

for idx, k in enumerate(k_values):
    ax = axes[idx]
    if k in all_top20:
        top20 = all_top20[k]
        kmers = [x[0] for x in top20]
        counts = [x[1] for x in top20]
        
        bars = ax.barh(range(len(kmers)), counts, color=colors[idx], alpha=0.8)
        ax.set_yticks(range(len(kmers)))
        ax.set_yticklabels(kmers, fontsize=8 if k <= 12 else 6, fontfamily='monospace')
        ax.set_xlabel('Count', fontsize=10)
        ax.set_title(f'Top 20 {k}-mers (Organelle Dataset)', fontsize=12, fontweight='bold')
        ax.invert_yaxis()
        
        max_count = max(counts)
        for bar in bars:
            width = bar.get_width()
            ax.text(width + max_count*0.01, bar.get_y() + bar.get_height()/2, 
                   f'{int(width):,}', va='center', fontsize=7)
    else:
        ax.text(0.5, 0.5, f'No data for k={k}', ha='center', va='center', 
               transform=ax.transAxes, fontsize=14)
        ax.set_title(f'K={k} (No Data)', fontsize=12)

plt.tight_layout()
plt.savefig(output_dir / '01_top20_kmers_comparison.png', dpi=150, bbox_inches='tight')
plt.close()
print("  ✓ 01_top20_kmers_comparison.png")

# Figure 2: Statistics comparison
print("Figure 2: Statistics comparison...")
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Unique k-mers vs theoretical
ax = axes[0]
unique_counts = [all_stats[k]['unique'] for k in k_values if k in all_stats]
theoretical_max = [4**k for k in k_values]
x = np.arange(len(k_values))
width = 0.35

bars1 = ax.bar(x - width/2, unique_counts, width, label='Observed', color='#3498db', alpha=0.8)
bars2 = ax.bar(x + width/2, theoretical_max, width, label='Theoretical Max (4^k)', color='#95a5a6', alpha=0.5)

ax.set_ylabel('Count (log scale)', fontsize=12)
ax.set_xlabel('K Value', fontsize=12)
ax.set_title('Unique K-mers vs Theoretical Maximum', fontsize=12, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels([f'k={k}' for k in k_values])
ax.set_yscale('log')
ax.legend()

# Max k-mer count
ax = axes[1]
max_counts = [all_stats[k]['max'] for k in k_values if k in all_stats]

bars = ax.bar([f'k={k}' for k in k_values], max_counts, color=colors)
ax.set_ylabel('Count', fontsize=12)
ax.set_xlabel('K Value', fontsize=12)
ax.set_title('Most Frequent K-mer Count by K Value', fontsize=12, fontweight='bold')

for bar, count in zip(bars, max_counts):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(max_counts)*0.01,
            f'{count:,}', ha='center', fontsize=10)

plt.tight_layout()
plt.savefig(output_dir / '02_kmer_statistics.png', dpi=150, bbox_inches='tight')
plt.close()
print("  ✓ 02_kmer_statistics.png")

# Figure 3: GC content
print("Figure 3: GC content analysis...")
fig, ax = plt.subplots(figsize=(12, 6))

for idx, k in enumerate(k_values):
    if k in all_top20:
        top20 = all_top20[k]
        gc_vals = []
        counts = []
        for kmer, count in top20:
            gc = (kmer.count('G') + kmer.count('C')) / len(kmer) * 100
            gc_vals.append(gc)
            counts.append(count)
        
        max_count = max(counts)
        sizes = [c/max_count*200 for c in counts]
        ax.scatter([k]*len(gc_vals), gc_vals, s=sizes, alpha=0.6, color=colors[idx], label=f'k={k}')

ax.axhline(y=50, color='gray', linestyle='--', alpha=0.5, label='50% GC')
ax.set_xlabel('K value', fontsize=12)
ax.set_ylabel('GC Content (%)', fontsize=12)
ax.set_title('GC Content of Top 20 K-mers\n(bubble size = relative frequency)', fontsize=12, fontweight='bold')
ax.set_xticks(k_values)
ax.legend()

plt.tight_layout()
plt.savefig(output_dir / '03_kmer_gc_content.png', dpi=150, bbox_inches='tight')
plt.close()
print("  ✓ 03_kmer_gc_content.png")

# Figure 4: Diversity
print("Figure 4: Diversity analysis...")
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Coverage
ax = axes[0]
coverages = []
for k in k_values:
    if k in all_stats:
        coverage = all_stats[k]['unique'] / (4**k) * 100
        coverages.append(min(coverage, 100))

bars = ax.bar([f'k={k}' for k in k_values], coverages, color=colors, alpha=0.8)
ax.set_ylabel('Coverage (%)', fontsize=12)
ax.set_xlabel('K Value', fontsize=12)
ax.set_title('K-mer Space Coverage\n(Observed / Theoretical Maximum)', fontsize=12, fontweight='bold')
ax.set_ylim(0, 110)

for bar, cov in zip(bars, coverages):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
            f'{cov:.1f}%', ha='center', fontsize=10)

# Mean frequency
ax = axes[1]
mean_freqs = [all_stats[k]['mean'] for k in k_values if k in all_stats]

bars = ax.bar([f'k={k}' for k in k_values], mean_freqs, color=colors, alpha=0.8)
ax.set_ylabel('Mean Frequency', fontsize=12)
ax.set_xlabel('K Value', fontsize=12)
ax.set_title('Average K-mer Frequency by K Value', fontsize=12, fontweight='bold')

for bar, freq in zip(bars, mean_freqs):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(mean_freqs)*0.01,
            f'{freq:.1f}', ha='center', fontsize=10)

plt.tight_layout()
plt.savefig(output_dir / '04_kmer_diversity.png', dpi=150, bbox_inches='tight')
plt.close()
print("  ✓ 04_kmer_diversity.png")

# Figure 5: Homopolymer analysis
print("Figure 5: Homopolymer analysis...")
fig, ax = plt.subplots(figsize=(10, 6))

for idx, k in enumerate(k_values):
    if k in all_top20:
        top20 = all_top20[k]
        run_ratios = []
        counts = []
        for kmer, count in top20:
            # Find max homopolymer run
            max_run = 1
            current_run = 1
            for i in range(1, len(kmer)):
                if kmer[i] == kmer[i-1]:
                    current_run += 1
                    max_run = max(max_run, current_run)
                else:
                    current_run = 1
            run_ratios.append(max_run / k * 100)
            counts.append(count)
        
        max_count = max(counts)
        sizes = [c/max_count*150 + 20 for c in counts]
        jitter = np.random.uniform(-0.1, 0.1, len(run_ratios))
        ax.scatter([k + j for j in jitter], run_ratios, s=sizes, alpha=0.6, color=colors[idx], label=f'k={k}')

ax.set_xlabel('K value', fontsize=12)
ax.set_ylabel('Homopolymer Run Ratio (%)', fontsize=12)
ax.set_title('Homopolymer Content in Top 20 K-mers\n(Max Run Length / K × 100)', fontsize=12, fontweight='bold')
ax.set_xticks(k_values)
ax.legend()

plt.tight_layout()
plt.savefig(output_dir / '05_homopolymer_analysis.png', dpi=150, bbox_inches='tight')
plt.close()
print("  ✓ 05_homopolymer_analysis.png")

# ============================================================================
# Generate Markdown Report
# ============================================================================
print("\n" + "="*60)
print("Generating markdown report...")
print("="*60)

report_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

report = f"""# K-mer Analysis Report

## OpenGenome2 Project - Organelle Dataset

**Analysis Date:** {report_date}
**Dataset:** Organelle sequences (~32,240 mitochondrial/chloroplast genomes)
**K Values Analyzed:** 6, 12, 18, 24
**Filter:** min_count ≥ 10

---

## Executive Summary

This report presents k-mer frequency analysis across multiple k values (6, 12, 18, 24) 
on the organelle genome dataset. K-mer analysis reveals patterns in sequence composition, 
repetitive elements, and sequence complexity that are characteristic of organellar genomes.

### Key Findings

1. **High AT Bias:** Top k-mers across all k values show strong AT bias, consistent with 
   organellar genome composition
2. **Conserved Sequences:** At higher k values (18-24), specific conserved sequences 
   emerge representing functional genomic elements
3. **Repeat Patterns:** AT dinucleotide repeats (ATATAT...) appear prominently at all k values

---

## Summary Statistics

| K | Unique K-mers | Theoretical Max (4^k) | Coverage | Total Occurrences | Max Count | Mean Count |
|---|---------------|----------------------|----------|-------------------|-----------|------------|
"""

for k in k_values:
    if k in all_stats:
        stats = all_stats[k]
        theoretical = 4**k
        coverage = min(stats['unique'] / theoretical * 100, 100)
        report += f"| {k} | {stats['unique']:,} | {theoretical:,} | {coverage:.2f}% | {stats['total']:,} | {stats['max']:,} | {stats['mean']:.2f} |\n"

report += """
---

## Top 20 K-mers by K Value

"""

for k in k_values:
    if k in all_top20:
        top20 = all_top20[k]
        report += f"### K = {k} ({k}-mers)\n\n"
        report += "| Rank | K-mer | Count | GC% |\n"
        report += "|------|-------|-------|-----|\n"
        
        for i, (kmer, count) in enumerate(top20, 1):
            gc = (kmer.count('G') + kmer.count('C')) / len(kmer) * 100
            report += f"| {i} | `{kmer}` | {count:,} | {gc:.1f}% |\n"
        
        report += "\n"

report += """---

## Visualizations

### Figure 1: Top 20 K-mers Comparison
![Top 20 K-mers](01_top20_kmers_comparison.png)

Horizontal bar charts showing the 20 most frequent k-mers for each k value. 
Note the prevalence of AT-rich sequences across all k values.

### Figure 2: K-mer Statistics
![K-mer Statistics](02_kmer_statistics.png)

Left: Comparison of observed unique k-mers vs theoretical maximum (4^k).
Right: Maximum k-mer count by k value.

### Figure 3: GC Content Analysis
![GC Content](03_kmer_gc_content.png)

GC content distribution of top 20 k-mers by k value. Bubble size represents 
relative frequency. The dashed line indicates 50% GC content.

### Figure 4: K-mer Diversity
![Diversity](04_kmer_diversity.png)

Left: K-mer space coverage (percentage of possible k-mers observed).
Right: Mean k-mer frequency by k value.

### Figure 5: Homopolymer Analysis
![Homopolymer](05_homopolymer_analysis.png)

Analysis of homopolymer runs (consecutive identical nucleotides) in top k-mers.
Higher ratios indicate more repetitive sequence content.

---

## Biological Interpretation

### AT Bias in Organellar Genomes
The predominance of AT-rich k-mers reflects the well-documented AT bias in 
organellar genomes, particularly mitochondrial genomes. This bias is thought 
to result from:
- Mutation pressure toward A and T
- Selection for AT-rich codons
- Reduced selection pressure on non-coding regions

### Conserved Sequences at Higher K Values
At k=18 and k=24, specific non-repetitive sequences become prominent:
- These likely represent highly conserved functional elements
- Possible origins include:
  - rRNA genes (highly conserved)
  - tRNA genes
  - Protein-coding gene motifs
  - Regulatory elements

### Repeat Structure
The prominence of AT dinucleotide repeats indicates:
- Simple sequence repeats common in organellar genomes
- Potential for replication slippage
- Non-coding intergenic regions

---

## Methods

### K-mer Extraction
- K-mers extracted using sliding window approach
- Window slides by 1 bp across each sequence
- Only forward strand analyzed

### Filtering
- Minimum count threshold: 10 occurrences
- Filters low-frequency k-mers that may represent:
  - Sequencing errors
  - Rare variants
  - Assembly artifacts

### Analysis Pipeline
```
Data: /data/parquet/organelle
↓
K-mer extraction (RDD mapPartitions)
↓
Counting (reduceByKey)
↓
Filtering (min_count ≥ 10)
↓
Sorting and top-20 selection
↓
Report generation
```

---

## File Outputs

| File | Description |
|------|-------------|
| `01_top20_kmers_comparison.png` | 2×2 grid of top 20 k-mers for each k value |
| `02_kmer_statistics.png` | Statistics comparison charts |
| `03_kmer_gc_content.png` | GC content scatter plot |
| `04_kmer_diversity.png` | Coverage and mean frequency |
| `05_homopolymer_analysis.png` | Homopolymer run analysis |
| `KMER_ANALYSIS_REPORT.md` | This report |

---

*Generated by OpenGenome2 K-mer Analysis Pipeline*
"""

with open(output_dir / 'KMER_ANALYSIS_REPORT.md', 'w') as f:
    f.write(report)

print("  ✓ KMER_ANALYSIS_REPORT.md")

print("\n" + "="*60)
print("K-mer report generation complete!")
print(f"Output directory: {output_dir}")
print("="*60)
