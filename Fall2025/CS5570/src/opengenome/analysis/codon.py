"""
Codon usage analysis using Spark MapReduce.

This module implements codon frequency analysis and RSCU (Relative Synonymous
Codon Usage) calculation for genomic sequences.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import pandas as pd

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql import types as T
from typing import Iterator

logger = logging.getLogger(__name__)


# Standard genetic code mapping
GENETIC_CODE = {
    "TTT": "F", "TTC": "F", "TTA": "L", "TTG": "L",
    "CTT": "L", "CTC": "L", "CTA": "L", "CTG": "L",
    "ATT": "I", "ATC": "I", "ATA": "I", "ATG": "M",
    "GTT": "V", "GTC": "V", "GTA": "V", "GTG": "V",
    "TCT": "S", "TCC": "S", "TCA": "S", "TCG": "S",
    "CCT": "P", "CCC": "P", "CCA": "P", "CCG": "P",
    "ACT": "T", "ACC": "T", "ACA": "T", "ACG": "T",
    "GCT": "A", "GCC": "A", "GCA": "A", "GCG": "A",
    "TAT": "Y", "TAC": "Y", "TAA": "*", "TAG": "*",
    "CAT": "H", "CAC": "H", "CAA": "Q", "CAG": "Q",
    "AAT": "N", "AAC": "N", "AAA": "K", "AAG": "K",
    "GAT": "D", "GAC": "D", "GAA": "E", "GAG": "E",
    "TGT": "C", "TGC": "C", "TGA": "*", "TGG": "W",
    "CGT": "R", "CGC": "R", "CGA": "R", "CGG": "R",
    "AGT": "S", "AGC": "S", "AGA": "R", "AGG": "R",
    "GGT": "G", "GGC": "G", "GGA": "G", "GGG": "G"
}


class CodonAnalyzer:
    """
    Analyze codon usage patterns in genomic sequences.
    
    Uses Spark MapReduce for distributed codon counting and RSCU calculation.
    """
    
    def __init__(self, spark: SparkSession, frame: int = 0):
        """
        Initialize codon analyzer.
        
        Args:
            spark: Active SparkSession
            frame: Reading frame (0, 1, or 2)
        """
        self.spark = spark
        self.frame = frame
        if frame not in [0, 1, 2]:
            raise ValueError(f"Frame must be 0, 1, or 2, got {frame}")
        logger.info(f"Initialized codon analyzer (frame={frame})")
    
    def analyze(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        skip_n: bool = True,
        skip_stops: bool = False,
        min_count: int = 1
    ) -> DataFrame:
        """
        Analyze codon usage in sequences.
        
        Args:
            input_path: Path to Parquet input (e.g., "/data/parquet/organelle/*.parquet")
            output_path: Optional path to save results as Parquet
            skip_n: Skip codons containing 'N'
            skip_stops: Exclude stop codons from analysis
            min_count: Minimum codon count to include in results
            
        Returns:
            DataFrame with columns: codon, count, freq, aa, sorted by count descending
        """
        try:
            logger.info(f"Starting codon analysis (frame={self.frame})")
            logger.info(f"Input: {input_path}")
            logger.info(f"Skip N: {skip_n}, Skip stops: {skip_stops}, Min count: {min_count}")
            
            # Load sequences
            df = self.spark.read.parquet(input_path)
            df = df.select("sequence")
            
            total_sequences = df.count()
            logger.info(f"Loaded {total_sequences:,} sequences")
            
            # Extract codons using MapReduce
            codon_df = self._extract_codons(df, skip_n)
            
            # Count codons (Reduce phase)
            codon_counts = (
                codon_df
                .groupBy("codon")
                .agg(F.count("*").alias("count"))
                .filter(F.col("count") >= min_count)
            )
            
            # Calculate total for frequency
            total_codons = codon_counts.agg(F.sum("count").alias("total")).first()["total"]
            logger.info(f"Found {codon_counts.count():,} unique codons")
            logger.info(f"Total codon count: {total_codons:,}")
            
            # Add frequency and amino acid
            result_df = (
                codon_counts
                .withColumn("freq", F.col("count") / F.lit(float(total_codons)))
                .withColumn("aa", self._map_codon_to_aa_udf()(F.col("codon")))
            )
            
            # Filter stops if requested
            if skip_stops:
                result_df = result_df.filter(F.col("aa") != "*")
                logger.info("Filtered stop codons")
            
            # Order by count descending
            result_df = result_df.orderBy(F.desc("count"))
            
            # Save results if output path provided
            if output_path:
                logger.info(f"Saving results to {output_path}")
                result_df.write.mode("overwrite").parquet(output_path)
            
            return result_df
            
        except Exception as e:
            logger.error(f"Codon analysis failed: {e}")
            raise RuntimeError(f"Codon analysis failed: {e}") from e
    
    def _extract_codons(self, df: DataFrame, skip_n: bool) -> DataFrame:
        """
        Extract codons from sequences using memory-efficient mapInPandas.
        
        Args:
            df: DataFrame with sequence column
            skip_n: Whether to skip codons containing N
            
        Returns:
            DataFrame with single 'codon' column
        """
        frame = self.frame
        schema = T.StructType([
            T.StructField("codon", T.StringType(), False)
        ])
        
        def extract_codons_partition(iterator):
            """Process one partition at a time, yielding in batches."""
            import pandas as pd_local
            
            batch_size = 10000  # Yield every 10k codons to limit memory
            
            for pdf in iterator:
                codons = []
                for seq in pdf['sequence']:
                    if not seq or len(seq) < 3:
                        continue
                    
                    seq_upper = str(seq).upper()
                    # Trim to frame and make length divisible by 3
                    seq_frame = seq_upper[frame:]
                    length_divisible = (len(seq_frame) // 3) * 3
                    seq_trimmed = seq_frame[:length_divisible]
                    
                    # Extract codons (step by 3)
                    for i in range(0, len(seq_trimmed), 3):
                        codon = seq_trimmed[i:i+3]
                        # Skip codons with ambiguity codes if skip_n is True
                        # IUPAC codes: R, Y, S, W, K, M, B, D, H, V, N
                        if skip_n:
                            # Check if codon contains only standard bases (A, T, G, C)
                            if not all(base in 'ATGC' for base in codon):
                                continue
                        codons.append((codon,))
                        
                        # Yield batch to limit memory usage
                        if len(codons) >= batch_size:
                            yield pd_local.DataFrame(codons, columns=['codon'])
                            codons = []
                
                # Yield remaining codons from this partition
                if codons:
                    yield pd_local.DataFrame(codons, columns=['codon'])
        
        codon_df = df.mapInPandas(extract_codons_partition, schema=schema)
        return codon_df
    
    def _map_codon_to_aa_udf(self):
        """Create UDF to map codons to amino acids."""
        @F.udf(returnType=T.StringType())
        def map_codon(codon: str) -> str:
            if not codon or len(codon) != 3:
                return None
            return GENETIC_CODE.get(codon.upper(), "X")  # X for unknown
        return map_codon
    
    def calculate_rscu(self, codon_df: DataFrame) -> DataFrame:
        """
        Calculate RSCU (Relative Synonymous Codon Usage).
        
        RSCU = observed_frequency / expected_frequency
        where expected_frequency = 1/n for n synonymous codons
        
        Args:
            codon_df: DataFrame with codon, count, freq, aa columns
            
        Returns:
            DataFrame with additional rscu column
        """
        logger.info("Calculating RSCU values")
        
        # Get counts per amino acid
        aa_totals = (
            codon_df
            .groupBy("aa")
            .agg(
                F.sum("count").alias("aa_total"),
                F.count("*").alias("synonymous_count")
            )
        )
        
        # Join and calculate RSCU
        rscu_df = (
            codon_df.alias("c")
            .join(aa_totals.alias("a"), "aa")
            .withColumn(
                "rscu",
                (F.col("c.count") / F.col("a.aa_total")) * F.col("a.synonymous_count")
            )
            .select("c.codon", "c.count", "c.freq", "c.aa", "rscu")
            .orderBy(F.desc("rscu"))
        )
        
        logger.info("RSCU calculation complete")
        return rscu_df
    
    def get_statistics(self, codon_df: DataFrame) -> Dict[str, Any]:
        """
        Calculate codon usage statistics.
        
        Args:
            codon_df: Codon frequency DataFrame
            
        Returns:
            Dictionary with statistics
        """
        stats = codon_df.agg(
            F.count("*").alias("unique_codons"),
            F.sum("count").alias("total_count"),
            F.mean("freq").alias("mean_freq"),
            F.max("freq").alias("max_freq"),
            F.min("freq").alias("min_freq")
        ).first()
        
        return {
            "unique_codons": stats["unique_codons"],
            "total_count": stats["total_count"],
            "mean_freq": round(stats["mean_freq"], 6),
            "max_freq": round(stats["max_freq"], 6),
            "min_freq": round(stats["min_freq"], 6)
        }
    
    def get_top_codons(self, codon_df: DataFrame, n: int = 20) -> List[Tuple[str, int, str]]:
        """
        Get top N most frequent codons.
        
        Args:
            codon_df: Codon frequency DataFrame
            n: Number of top codons to return
            
        Returns:
            List of (codon, count, amino_acid) tuples
        """
        top = codon_df.orderBy(F.desc("count")).limit(n).collect()
        return [(row["codon"], row["count"], row["aa"]) for row in top]
    
    def get_preferred_codons(self, rscu_df: DataFrame, threshold: float = 1.0) -> List[Tuple[str, float, str]]:
        """
        Get preferred codons (RSCU > threshold).
        
        Args:
            rscu_df: DataFrame with RSCU values
            threshold: RSCU threshold (default 1.0)
            
        Returns:
            List of (codon, rscu, amino_acid) tuples
        """
        preferred = (
            rscu_df
            .filter(F.col("rscu") > threshold)
            .orderBy(F.desc("rscu"))
            .collect()
        )
        return [(row["codon"], row["rscu"], row["aa"]) for row in preferred]
