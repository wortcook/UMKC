#!/usr/bin/env python3
"""
Generate comprehensive codon analysis report with visualizations.
Analyzes codon usage from the combined genomic dataset.
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import pandas as pd
import numpy as np
from collections import defaultdict
import os

# Create output directory
os.makedirs('/results/demo/codon_report', exist_ok=True)

# Complete codon data from analysis (all 64 codons)
# Data from combined dataset: 247,190 sequences, 2.88 billion codons
codon_data = [
    ('TTT', 73517758, 0.0255351, 'F'), ('AAA', 72663678, 0.0252385, 'K'),
    ('CGC', 61075268, 0.0212135, 'R'), ('GCG', 60748053, 0.0210998, 'A'),
    ('ATT', 58183203, 0.0202090, 'I'), ('AAT', 58150123, 0.0201975, 'N'),
    ('GCC', 57957446, 0.0201305, 'A'), ('TTC', 57805028, 0.0200776, 'F'),
    ('GGC', 57519813, 0.0199785, 'G'), ('GAA', 56415540, 0.0195950, 'E'),
    ('CCG', 56013972, 0.0194555, 'P'), ('CGG', 55676430, 0.0193383, 'R'),
    ('ATC', 53406061, 0.0185497, 'I'), ('TCG', 53150389, 0.0184609, 'S'),
    ('CGA', 53032091, 0.0184198, 'R'), ('GAT', 52793108, 0.0183368, 'D'),
    ('CAA', 48792906, 0.0169474, 'Q'), ('CTT', 48492152, 0.0168429, 'L'),
    ('TTG', 48430320, 0.0168215, 'L'), ('ATA', 47672145, 0.0165581, 'I'),
    ('AAG', 47343451, 0.0164439, 'K'), ('TGA', 47285230, 0.0164237, '*'),
    ('TAT', 47201412, 0.0163946, 'Y'), ('TCA', 47167127, 0.0163827, 'S'),
    ('CCA', 45846404, 0.0159240, 'P'), ('GCA', 45840641, 0.0159220, 'A'),
    ('TGC', 45724284, 0.0158816, 'C'), ('CAT', 45479535, 0.0157965, 'H'),
    ('AGC', 45183449, 0.0156937, 'S'), ('GCT', 45009589, 0.0156333, 'A'),
    ('CTG', 44986518, 0.0156253, 'L'), ('TCT', 44818823, 0.0155671, 'S'),
    ('CAG', 44812460, 0.0155648, 'Q'), ('TGG', 44547541, 0.0154728, 'W'),
    ('ATG', 44389756, 0.0154180, 'M'), ('TCC', 44361654, 0.0154083, 'S'),
    ('AGA', 43479723, 0.0151019, 'R'), ('GGA', 43001059, 0.0149357, 'G'),
    ('CCT', 40359347, 0.0140181, 'P'), ('TAA', 40344177, 0.0140129, '*'),
    ('AAC', 40059705, 0.0139141, 'N'), ('ACC', 39906999, 0.0138610, 'T'),
    ('CTC', 39840094, 0.0138378, 'L'), ('TTA', 39695554, 0.0137876, 'L'),
    ('GTT', 39245823, 0.0136314, 'V'), ('AGG', 39086476, 0.0135760, 'R'),
    ('GAG', 38922843, 0.0135192, 'E'), ('CCC', 38875040, 0.0135026, 'P'),
    ('GGT', 38839585, 0.0134903, 'G'), ('GAC', 38710017, 0.0134453, 'D'),
    ('GTC', 38463860, 0.0133598, 'V'), ('GGG', 37271459, 0.0129456, 'G'),
    ('CGT', 36536659, 0.0126904, 'R'), ('ACG', 36460644, 0.0126640, 'T'),
    ('ACA', 34652543, 0.0120360, 'T'), ('CAC', 34373887, 0.0119392, 'H'),
    ('TGT', 33988331, 0.0118053, 'C'), ('GTG', 33797158, 0.0117389, 'V'),
    ('ACT', 30659543, 0.0106491, 'T'), ('AGT', 30172656, 0.0104800, 'S'),
    ('TAC', 28493494, 0.0098967, 'Y'), ('GTA', 28056045, 0.0097448, 'V'),
    ('CTA', 27493767, 0.0095495, 'L'), ('TAG', 26800999, 0.0093089, '*'),
]

df = pd.DataFrame(codon_data, columns=['codon', 'count', 'freq', 'aa'])
total_codons = df['count'].sum()

# Amino acid full names and properties
aa_info = {
    'A': ('Alanine', 'nonpolar'),      'R': ('Arginine', 'basic'),
    'N': ('Asparagine', 'polar'),      'D': ('Aspartate', 'acidic'),
    'C': ('Cysteine', 'polar'),        'Q': ('Glutamine', 'polar'),
    'E': ('Glutamate', 'acidic'),      'G': ('Glycine', 'nonpolar'),
    'H': ('Histidine', 'basic'),       'I': ('Isoleucine', 'nonpolar'),
    'L': ('Leucine', 'nonpolar'),      'K': ('Lysine', 'basic'),
    'M': ('Methionine', 'nonpolar'),   'F': ('Phenylalanine', 'aromatic'),
    'P': ('Proline', 'nonpolar'),      'S': ('Serine', 'polar'),
    'T': ('Threonine', 'polar'),       'W': ('Tryptophan', 'aromatic'),
    'Y': ('Tyrosine', 'aromatic'),     'V': ('Valine', 'nonpolar'),
    '*': ('Stop', 'stop'),
}

property_colors = {
    'nonpolar': '#3498db',   # blue
    'polar': '#2ecc71',      # green
    'basic': '#e74c3c',      # red
    'acidic': '#f39c12',     # orange
    'aromatic': '#9b59b6',   # purple
    'stop': '#7f8c8d',       # gray
}

# Set style
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")

print("Creating Figure 1: Codon Frequency Bar Chart (All 64 Codons)...")

# Figure 1: All 64 codons bar chart
fig, ax = plt.subplots(figsize=(20, 8))
colors = [property_colors[aa_info[aa][1]] for aa in df['aa']]
bars = ax.bar(range(len(df)), df['freq'] * 100, color=colors, edgecolor='white', linewidth=0.5)
ax.set_xticks(range(len(df)))
ax.set_xticklabels([f"{row['codon']}\n({row['aa']})" for _, row in df.iterrows()], 
                   rotation=90, fontsize=7, ha='center')
ax.set_xlabel('Codon (Amino Acid)', fontsize=12)
ax.set_ylabel('Frequency (%)', fontsize=12)
ax.set_title('Codon Usage Frequency - Combined Genomic Dataset\n(247,190 sequences, 2.88 billion codons)', fontsize=14, fontweight='bold')

# Add legend
legend_patches = [mpatches.Patch(color=color, label=prop.capitalize()) 
                  for prop, color in property_colors.items()]
ax.legend(handles=legend_patches, loc='upper right', title='Amino Acid Property')

# Add horizontal line for expected uniform frequency
ax.axhline(y=100/64, color='red', linestyle='--', alpha=0.7, label='Expected (uniform)')
ax.text(62, 100/64 + 0.05, 'Expected\n(1.56%)', fontsize=8, color='red', ha='right')

plt.tight_layout()
plt.savefig('/results/demo/codon_report/01_codon_frequency_all64.png', dpi=150, bbox_inches='tight')
plt.close()

print("Creating Figure 2: Codon Usage Heatmap...")

# Figure 2: Codon table heatmap (4x16 standard genetic code layout)
fig, ax = plt.subplots(figsize=(14, 10))

# Create 4x4x4 matrix (first base x second base x third base)
bases = ['T', 'C', 'A', 'G']
heatmap_data = np.zeros((16, 4))
labels = []
row_labels = []

row = 0
for first in bases:
    for second in bases:
        row_labels.append(f"{first}{second}X")
        for col, third in enumerate(bases):
            codon = first + second + third
            row_data = df[df['codon'] == codon]
            if not row_data.empty:
                heatmap_data[row, col] = row_data['freq'].values[0] * 100
        row += 1

# Create heatmap
im = ax.imshow(heatmap_data, cmap='YlOrRd', aspect='auto')

# Add colorbar
cbar = plt.colorbar(im, ax=ax, label='Frequency (%)')

# Set ticks
ax.set_xticks(range(4))
ax.set_xticklabels(['T', 'C', 'A', 'G'], fontsize=12, fontweight='bold')
ax.set_xlabel('Third Position', fontsize=12, fontweight='bold')

ax.set_yticks(range(16))
ax.set_yticklabels(row_labels, fontsize=10)
ax.set_ylabel('First + Second Position', fontsize=12, fontweight='bold')

# Add codon labels with counts
for i in range(16):
    for j in range(4):
        first = bases[i // 4]
        second = bases[i % 4]
        third = bases[j]
        codon = first + second + third
        row_data = df[df['codon'] == codon]
        if not row_data.empty:
            aa = row_data['aa'].values[0]
            freq = row_data['freq'].values[0] * 100
            text_color = 'white' if freq > 1.8 else 'black'
            ax.text(j, i, f"{codon}\n{aa}\n{freq:.2f}%", ha='center', va='center', 
                   fontsize=7, color=text_color, fontweight='bold')

ax.set_title('Codon Usage Heatmap - Genetic Code Table\n(Frequency % shown for each codon)', 
             fontsize=14, fontweight='bold')

plt.tight_layout()
plt.savefig('/results/demo/codon_report/02_codon_heatmap.png', dpi=150, bbox_inches='tight')
plt.close()

print("Creating Figure 3: Amino Acid Usage...")

# Figure 3: Amino acid usage (grouped by AA)
aa_counts = df.groupby('aa')['count'].sum().reset_index()
aa_counts['name'] = aa_counts['aa'].map(lambda x: aa_info[x][0])
aa_counts['property'] = aa_counts['aa'].map(lambda x: aa_info[x][1])
aa_counts['freq'] = aa_counts['count'] / total_codons * 100
aa_counts = aa_counts.sort_values('count', ascending=True)

fig, ax = plt.subplots(figsize=(12, 10))
colors = [property_colors[prop] for prop in aa_counts['property']]
bars = ax.barh(range(len(aa_counts)), aa_counts['freq'], color=colors, edgecolor='white')

ax.set_yticks(range(len(aa_counts)))
ax.set_yticklabels([f"{row['name']} ({row['aa']})" for _, row in aa_counts.iterrows()], fontsize=10)
ax.set_xlabel('Frequency (%)', fontsize=12)
ax.set_title('Amino Acid Usage Frequency\n(Combined from all synonymous codons)', fontsize=14, fontweight='bold')

# Add count labels
for i, (_, row) in enumerate(aa_counts.iterrows()):
    ax.text(row['freq'] + 0.1, i, f"{row['count']:,.0f}", va='center', fontsize=8)

legend_patches = [mpatches.Patch(color=color, label=prop.capitalize()) 
                  for prop, color in property_colors.items()]
ax.legend(handles=legend_patches, loc='lower right', title='Property')

plt.tight_layout()
plt.savefig('/results/demo/codon_report/03_amino_acid_usage.png', dpi=150, bbox_inches='tight')
plt.close()

print("Creating Figure 4: Codon Bias by Amino Acid (RSCU)...")

# Figure 4: Relative Synonymous Codon Usage (RSCU)
# RSCU = observed / expected (where expected = total_for_aa / num_codons_for_aa)

aa_totals = df.groupby('aa')['count'].sum()
aa_num_codons = df.groupby('aa').size()

df['expected'] = df.apply(lambda row: aa_totals[row['aa']] / aa_num_codons[row['aa']], axis=1)
df['rscu'] = df['count'] / df['expected']

# Group codons by amino acid for visualization
fig, axes = plt.subplots(3, 7, figsize=(20, 12))
axes = axes.flatten()

aa_list = sorted([aa for aa in df['aa'].unique() if aa != '*'])
aa_list.append('*')  # Add stop codons at end

for idx, aa in enumerate(aa_list):
    ax = axes[idx]
    aa_data = df[df['aa'] == aa].sort_values('codon')
    
    color = property_colors[aa_info[aa][1]]
    bars = ax.bar(aa_data['codon'], aa_data['rscu'], color=color, edgecolor='black', linewidth=0.5)
    
    ax.axhline(y=1.0, color='red', linestyle='--', alpha=0.7)
    ax.set_title(f"{aa_info[aa][0]} ({aa})", fontsize=10, fontweight='bold')
    ax.set_ylim(0, max(2.5, aa_data['rscu'].max() * 1.1))
    
    if idx >= 14:
        ax.set_xlabel('Codon', fontsize=8)
    if idx % 7 == 0:
        ax.set_ylabel('RSCU', fontsize=8)
    
    ax.tick_params(axis='x', labelsize=7, rotation=45)
    ax.tick_params(axis='y', labelsize=7)

# Remove empty subplot
axes[-1].axis('off')

fig.suptitle('Relative Synonymous Codon Usage (RSCU) by Amino Acid\n(RSCU = 1.0 indicates no bias, >1 = preferred, <1 = avoided)', 
             fontsize=14, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig('/results/demo/codon_report/04_rscu_by_amino_acid.png', dpi=150, bbox_inches='tight')
plt.close()

print("Creating Figure 5: GC Content at Codon Positions...")

# Figure 5: GC content at each codon position
def gc_content(codon, position):
    return 1 if codon[position] in ['G', 'C'] else 0

df['gc1'] = df['codon'].apply(lambda x: gc_content(x, 0))
df['gc2'] = df['codon'].apply(lambda x: gc_content(x, 1))
df['gc3'] = df['codon'].apply(lambda x: gc_content(x, 2))

gc1_total = (df['gc1'] * df['count']).sum() / total_codons * 100
gc2_total = (df['gc2'] * df['count']).sum() / total_codons * 100
gc3_total = (df['gc3'] * df['count']).sum() / total_codons * 100

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# GC content by position
ax = axes[0]
positions = ['Position 1', 'Position 2', 'Position 3', 'Overall']
gc_values = [gc1_total, gc2_total, gc3_total, (gc1_total + gc2_total + gc3_total) / 3]
colors_gc = ['#3498db', '#2ecc71', '#e74c3c', '#9b59b6']
bars = ax.bar(positions, gc_values, color=colors_gc, edgecolor='black')
ax.axhline(y=50, color='gray', linestyle='--', alpha=0.7, label='Expected (50%)')
ax.set_ylabel('GC Content (%)', fontsize=12)
ax.set_title('GC Content at Each Codon Position', fontsize=12, fontweight='bold')
ax.set_ylim(0, 70)
for bar, val in zip(bars, gc_values):
    ax.text(bar.get_x() + bar.get_width()/2, val + 1, f'{val:.1f}%', ha='center', fontsize=10, fontweight='bold')

# Nucleotide frequency at each position
ax = axes[1]
width = 0.2
x = np.arange(3)

for i, base in enumerate(['A', 'T', 'G', 'C']):
    freqs = []
    for pos in range(3):
        base_count = df[df['codon'].str[pos] == base]['count'].sum()
        freqs.append(base_count / total_codons * 100)
    ax.bar(x + i*width, freqs, width, label=base, 
           color=['#e74c3c', '#3498db', '#2ecc71', '#f39c12'][i])

ax.set_xticks(x + 1.5*width)
ax.set_xticklabels(['Position 1', 'Position 2', 'Position 3'])
ax.axhline(y=25, color='gray', linestyle='--', alpha=0.7)
ax.set_ylabel('Frequency (%)', fontsize=12)
ax.set_title('Nucleotide Frequency at Each Codon Position', fontsize=12, fontweight='bold')
ax.legend(title='Nucleotide')
ax.set_ylim(0, 35)

plt.tight_layout()
plt.savefig('/results/demo/codon_report/05_gc_content_analysis.png', dpi=150, bbox_inches='tight')
plt.close()

print("Creating Figure 6: Top 20 vs Bottom 20 Codons...")

# Figure 6: Top 20 vs Bottom 20 comparison
fig, axes = plt.subplots(1, 2, figsize=(16, 8))

# Top 20
ax = axes[0]
top20 = df.head(20)
colors_top = [property_colors[aa_info[aa][1]] for aa in top20['aa']]
bars = ax.barh(range(20), top20['freq'] * 100, color=colors_top, edgecolor='white')
ax.set_yticks(range(20))
ax.set_yticklabels([f"{row['codon']} ({row['aa']})" for _, row in top20.iterrows()])
ax.set_xlabel('Frequency (%)', fontsize=12)
ax.set_title('Top 20 Most Frequent Codons', fontsize=12, fontweight='bold')
ax.invert_yaxis()

# Bottom 20
ax = axes[1]
bottom20 = df.tail(20).iloc[::-1]
colors_bottom = [property_colors[aa_info[aa][1]] for aa in bottom20['aa']]
bars = ax.barh(range(20), bottom20['freq'] * 100, color=colors_bottom, edgecolor='white')
ax.set_yticks(range(20))
ax.set_yticklabels([f"{row['codon']} ({row['aa']})" for _, row in bottom20.iterrows()])
ax.set_xlabel('Frequency (%)', fontsize=12)
ax.set_title('Bottom 20 Least Frequent Codons', fontsize=12, fontweight='bold')
ax.invert_yaxis()

legend_patches = [mpatches.Patch(color=color, label=prop.capitalize()) 
                  for prop, color in property_colors.items()]
fig.legend(handles=legend_patches, loc='lower center', ncol=6, title='Amino Acid Property', 
           bbox_to_anchor=(0.5, -0.02))

plt.tight_layout()
plt.savefig('/results/demo/codon_report/06_top_bottom_codons.png', dpi=150, bbox_inches='tight')
plt.close()

print("Creating Figure 7: Stop Codon Usage...")

# Figure 7: Stop codon analysis
fig, ax = plt.subplots(figsize=(8, 6))
stop_codons = df[df['aa'] == '*'].sort_values('count', ascending=False)
colors_stop = ['#e74c3c', '#3498db', '#2ecc71']
bars = ax.bar(stop_codons['codon'], stop_codons['count'] / 1e6, color=colors_stop, edgecolor='black')
ax.set_ylabel('Count (Millions)', fontsize=12)
ax.set_xlabel('Stop Codon', fontsize=12)
ax.set_title('Stop Codon Usage\n(TGA > TAA > TAG)', fontsize=14, fontweight='bold')

for bar, row in zip(bars, stop_codons.itertuples()):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
            f'{row.count:,}\n({row.freq*100:.2f}%)', ha='center', fontsize=10)

total_stops = stop_codons['count'].sum()
ax.text(0.95, 0.95, f'Total stops: {total_stops:,}\n({total_stops/total_codons*100:.2f}% of all codons)', 
        transform=ax.transAxes, ha='right', va='top', fontsize=10,
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

plt.tight_layout()
plt.savefig('/results/demo/codon_report/07_stop_codon_usage.png', dpi=150, bbox_inches='tight')
plt.close()

print("Creating Figure 8: Codon Wheel...")

# Figure 8: Codon wheel (circular visualization)
fig, ax = plt.subplots(figsize=(14, 14), subplot_kw=dict(projection='polar'))

# Organize codons by first and second base
bases = ['T', 'C', 'A', 'G']
n_codons = 64
angles = np.linspace(0, 2*np.pi, n_codons, endpoint=False)

# Order codons in a systematic way for the wheel
ordered_codons = []
for first in bases:
    for second in bases:
        for third in bases:
            ordered_codons.append(first + second + third)

# Get frequencies for ordered codons
freqs = []
aas = []
for codon in ordered_codons:
    row_data = df[df['codon'] == codon]
    if not row_data.empty:
        freqs.append(row_data['freq'].values[0] * 100)
        aas.append(row_data['aa'].values[0])

colors_wheel = [property_colors[aa_info[aa][1]] for aa in aas]

# Create bar chart in polar coordinates
bars = ax.bar(angles, freqs, width=2*np.pi/n_codons * 0.9, color=colors_wheel, 
              edgecolor='white', linewidth=0.5, alpha=0.8)

# Add codon labels
for angle, codon, freq in zip(angles, ordered_codons, freqs):
    rotation = np.degrees(angle)
    if angle > np.pi/2 and angle < 3*np.pi/2:
        rotation += 180
        ha = 'right'
    else:
        ha = 'left'
    
    ax.text(angle, freq + 0.3, codon, ha='center', va='bottom', 
            fontsize=6, rotation=rotation - 90, rotation_mode='anchor')

# Add first base labels (outer ring markers)
for i, base in enumerate(bases):
    angle_start = i * np.pi/2
    ax.annotate(f'First: {base}', xy=(angle_start + np.pi/4, 3.2), 
                fontsize=12, fontweight='bold', ha='center')

ax.set_ylim(0, 3.5)
ax.set_title('Codon Usage Wheel\n(Organized by first → second → third base)', 
             fontsize=14, fontweight='bold', pad=20)

# Add legend
legend_patches = [mpatches.Patch(color=color, label=prop.capitalize()) 
                  for prop, color in property_colors.items()]
ax.legend(handles=legend_patches, loc='upper left', bbox_to_anchor=(1.1, 1), title='AA Property')

plt.tight_layout()
plt.savefig('/results/demo/codon_report/08_codon_wheel.png', dpi=150, bbox_inches='tight')
plt.close()

print("\nAll figures created successfully!")
print(f"\nOutput directory: /results/demo/codon_report/")

# List created files
files = sorted(os.listdir('/results/demo/codon_report/'))
print("\nGenerated files:")
for f in files:
    size = os.path.getsize(f'/results/demo/codon_report/{f}')
    print(f"  {f} ({size/1024:.1f} KB)")
