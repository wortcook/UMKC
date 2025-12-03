"""
Plotting functions for genomic data visualization.

This module provides functions to create publication-quality plots for:
- K-mer frequency distributions
- Codon usage patterns
- GC content distributions
- Sequence length distributions
"""

import logging
from pathlib import Path
from typing import Optional, Tuple

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for containerized environments
import matplotlib.pyplot as plt
import pandas as pd
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

logger = logging.getLogger(__name__)


def plot_kmer_distribution(
    input_path: str,
    output_path: str,
    top_n: int = 20,
    figsize: Tuple[int, int] = (12, 7),
    dpi: int = 200,
    title: Optional[str] = None,
    color: str = 'skyblue'
) -> str:
    """
    Create a bar chart showing k-mer frequency distribution.
    
    Args:
        input_path: Path to k-mer analysis results (Parquet)
        output_path: Path to save the PNG file
        top_n: Number of top k-mers to display
        figsize: Figure size (width, height) in inches
        dpi: DPI for output image
        title: Custom title (defaults to "Top N k-mers")
        color: Bar color
        
    Returns:
        Path to saved PNG file
        
    Raises:
        RuntimeError: If plotting fails
    """
    try:
        spark = SparkSession.getActiveSession()
        if not spark:
            raise RuntimeError("No active Spark session")
        
        logger.info(f"Loading k-mer data from {input_path}")
        df = spark.read.parquet(input_path)
        
        # Get top N k-mers
        top_kmers = (
            df.orderBy(F.desc("count"))
            .limit(top_n)
            .toPandas()
        )
        
        logger.info(f"Creating bar chart for {len(top_kmers)} k-mers")
        
        # Create plot
        plt.figure(figsize=figsize)
        plt.bar(top_kmers["kmer"], top_kmers["count"], color=color)
        plt.xticks(rotation=90, fontsize=10)
        plt.title(title or f"Top {top_n} k-mers", fontsize=14)
        plt.xlabel("k-mer", fontsize=12)
        plt.ylabel("Count", fontsize=12)
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        
        # Save
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Saved k-mer plot to {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Failed to create k-mer plot: {e}")
        plt.close()
        raise RuntimeError(f"K-mer plotting failed: {e}") from e


def plot_codon_usage(
    input_path: str,
    output_path: str,
    top_n: int = 30,
    figsize: Tuple[int, int] = (14, 7),
    dpi: int = 200,
    title: Optional[str] = None,
    color: str = 'lightcoral',
    show_amino_acids: bool = True
) -> str:
    """
    Create a bar chart showing codon usage frequency.
    
    Args:
        input_path: Path to codon analysis results (Parquet)
        output_path: Path to save the PNG file
        top_n: Number of top codons to display
        figsize: Figure size (width, height) in inches
        dpi: DPI for output image
        title: Custom title (defaults to "Top N Codon Usage")
        color: Bar color
        show_amino_acids: Whether to show amino acid labels
        
    Returns:
        Path to saved PNG file
        
    Raises:
        RuntimeError: If plotting fails
    """
    try:
        spark = SparkSession.getActiveSession()
        if not spark:
            raise RuntimeError("No active Spark session")
        
        logger.info(f"Loading codon data from {input_path}")
        df = spark.read.parquet(input_path)
        
        # Ensure frequency column exists
        if "freq" not in df.columns:
            logger.info("Computing frequency column")
            total = df.agg(F.sum("count").alias("total")).first()["total"]
            df = df.withColumn("freq", F.col("count") / F.lit(float(total)))
        
        # Get top N codons
        top_codons = (
            df.orderBy(F.desc("freq"))
            .limit(top_n)
            .toPandas()
        )
        
        logger.info(f"Creating bar chart for {len(top_codons)} codons")
        
        # Create plot
        plt.figure(figsize=figsize)
        bars = plt.bar(top_codons["codon"], top_codons["freq"], color=color)
        
        # Optionally add amino acid labels
        if show_amino_acids and "aa" in top_codons.columns:
            for i, (bar, aa) in enumerate(zip(bars, top_codons["aa"])):
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height,
                        f'{aa}',
                        ha='center', va='bottom', fontsize=8, color='gray')
        
        plt.xticks(rotation=90, fontsize=10)
        plt.title(title or f"Top {top_n} Codon Usage (Frequency)", fontsize=14)
        plt.xlabel("Codon", fontsize=12)
        plt.ylabel("Frequency", fontsize=12)
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        
        # Save
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Saved codon plot to {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Failed to create codon plot: {e}")
        plt.close()
        raise RuntimeError(f"Codon plotting failed: {e}") from e


def plot_gc_content(
    input_path: str,
    output_path: str,
    bins: int = 50,
    figsize: Tuple[int, int] = (12, 7),
    dpi: int = 200,
    title: Optional[str] = None,
    color: str = 'mediumseagreen'
) -> str:
    """
    Create a histogram showing GC content distribution.
    
    Args:
        input_path: Path to sequence data (Parquet)
        output_path: Path to save the PNG file
        bins: Number of histogram bins
        figsize: Figure size (width, height) in inches
        dpi: DPI for output image
        title: Custom title (defaults to "GC Content Distribution")
        color: Histogram color
        
    Returns:
        Path to saved PNG file
        
    Raises:
        RuntimeError: If plotting fails
    """
    try:
        spark = SparkSession.getActiveSession()
        if not spark:
            raise RuntimeError("No active Spark session")
        
        logger.info(f"Loading sequence data from {input_path}")
        df = spark.read.parquet(input_path)
        
        # Calculate GC content if not present
        if "gc_content" not in df.columns:
            logger.info("Computing GC content")
            
            @F.udf(returnType='float')
            def calculate_gc(sequence: str) -> float:
                if not sequence:
                    return 0.0
                seq_upper = sequence.upper()
                gc_count = seq_upper.count('G') + seq_upper.count('C')
                return (gc_count / len(sequence)) * 100.0 if len(sequence) > 0 else 0.0
            
            df = df.withColumn("gc_content", calculate_gc(F.col("sequence")))
        
        # Collect GC content values
        gc_values = df.select("gc_content").toPandas()["gc_content"]
        
        logger.info(f"Creating histogram with {bins} bins for {len(gc_values)} sequences")
        
        # Create plot
        plt.figure(figsize=figsize)
        n, bins_edges, patches = plt.hist(gc_values, bins=bins, color=color, 
                                          edgecolor='black', alpha=0.7)
        
        # Add mean line
        mean_gc = gc_values.mean()
        plt.axvline(mean_gc, color='red', linestyle='--', linewidth=2,
                   label=f'Mean: {mean_gc:.2f}%')
        
        plt.title(title or "GC Content Distribution", fontsize=14)
        plt.xlabel("GC Content (%)", fontsize=12)
        plt.ylabel("Frequency", fontsize=12)
        plt.legend()
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        
        # Save
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Saved GC content plot to {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Failed to create GC content plot: {e}")
        plt.close()
        raise RuntimeError(f"GC content plotting failed: {e}") from e


def plot_sequence_length_distribution(
    input_path: str,
    output_path: str,
    bins: int = 50,
    figsize: Tuple[int, int] = (12, 7),
    dpi: int = 200,
    title: Optional[str] = None,
    color: str = 'mediumpurple'
) -> str:
    """
    Create a histogram showing sequence length distribution.
    
    Args:
        input_path: Path to sequence data (Parquet)
        output_path: Path to save the PNG file
        bins: Number of histogram bins
        figsize: Figure size (width, height) in inches
        dpi: DPI for output image
        title: Custom title (defaults to "Sequence Length Distribution")
        color: Histogram color
        
    Returns:
        Path to saved PNG file
        
    Raises:
        RuntimeError: If plotting fails
    """
    try:
        spark = SparkSession.getActiveSession()
        if not spark:
            raise RuntimeError("No active Spark session")
        
        logger.info(f"Loading sequence data from {input_path}")
        df = spark.read.parquet(input_path)
        
        # Get length column
        if "length" not in df.columns:
            logger.info("Computing sequence lengths")
            df = df.withColumn("length", F.length(F.col("sequence")))
        
        # Collect length values
        lengths = df.select("length").toPandas()["length"]
        
        logger.info(f"Creating histogram with {bins} bins for {len(lengths)} sequences")
        
        # Create plot
        plt.figure(figsize=figsize)
        n, bins_edges, patches = plt.hist(lengths, bins=bins, color=color,
                                          edgecolor='black', alpha=0.7)
        
        # Add statistics
        mean_len = lengths.mean()
        median_len = lengths.median()
        plt.axvline(mean_len, color='red', linestyle='--', linewidth=2,
                   label=f'Mean: {mean_len:.0f}')
        plt.axvline(median_len, color='orange', linestyle='--', linewidth=2,
                   label=f'Median: {median_len:.0f}')
        
        plt.title(title or "Sequence Length Distribution", fontsize=14)
        plt.xlabel("Sequence Length (bp)", fontsize=12)
        plt.ylabel("Frequency", fontsize=12)
        plt.legend()
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        
        # Save
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Saved sequence length plot to {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Failed to create sequence length plot: {e}")
        plt.close()
        raise RuntimeError(f"Sequence length plotting failed: {e}") from e
