"""
K-mer frequency analysis using Spark RDD MapReduce.

This module uses pure RDD operations (mapPartitions + reduceByKey) for reliable
k-mer counting. The approach:
1. MAP: Extract k-mers from each sequence within partitions using Counter for pre-aggregation
2. SHUFFLE: reduceByKey to aggregate across partitions  
3. REDUCE: Final counts converted to DataFrame

This avoids the issues with mapInPandas where generator data can be lost.
"""

import logging
from typing import Optional, Dict, Any
from pathlib import Path

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql import types as T


logger = logging.getLogger(__name__)


class KmerAnalyzer:
    """K-mer frequency analysis using distributed RDD MapReduce."""
    
    def __init__(self, spark: SparkSession, k: int = 6):
        """
        Initialize k-mer analyzer.
        
        Args:
            spark: Active Spark session
            k: K-mer length (typically 6-8)
        """
        self.spark = spark
        self.k = k
        
        if k < 1:
            raise ValueError(f"k must be positive, got {k}")
        if k > 32:
            logger.warning(f"Large k={k} may cause memory issues")
        
        # Calculate theoretical max unique k-mers (4^k)
        self.max_unique_kmers = 4 ** k
        logger.info(f"Initialized k-mer analyzer (k={k}, max unique k-mers: {self.max_unique_kmers:,})")
    
    def analyze(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        skip_n: bool = True,
        min_count: int = 1,
        sample_size: Optional[int] = None
    ) -> DataFrame:
        """
        Perform k-mer frequency analysis using RDD MapReduce.
        
        MapReduce workflow:
        1. MAP: Extract k-mers from each sequence, pre-aggregate with Counter per partition
        2. SHUFFLE: reduceByKey to sum counts across partitions
        3. REDUCE: Convert to DataFrame, apply filters
        
        Args:
            input_path: Path to Parquet files with sequences
            output_path: Optional path to save results
            skip_n: Skip k-mers containing 'N' (ambiguous base)
            min_count: Minimum frequency threshold
            sample_size: Optional number of sequences to sample
            
        Returns:
            DataFrame with columns: kmer, count
        """
        try:
            logger.info(f"Starting k-mer analysis (k={self.k})")
            logger.info(f"Input: {input_path}")
            logger.info(f"Skip N: {skip_n}, Min count: {min_count}")
            if sample_size:
                logger.info(f"Sample size: {sample_size:,} sequences")
            
            # Load sequences
            df = self.spark.read.parquet(input_path)
            total_sequences = df.count()
            logger.info(f"Loaded {total_sequences:,} sequences")
            
            # Apply sampling if requested
            if sample_size and sample_size < total_sequences:
                sample_fraction = sample_size / total_sequences
                df = df.sample(withReplacement=False, fraction=sample_fraction, seed=42)
                sampled_count = df.count()
                logger.info(f"Sampled {sampled_count:,} sequences")
            
            # Use RDD-based MapReduce approach
            logger.info("Extracting k-mers using RDD mapPartitions + reduceByKey")
            result_df = self._count_kmers_rdd(df, skip_n, min_count)
            
            # Get count and log
            total_kmers = result_df.count()
            logger.info(f"Found {total_kmers:,} unique k-mers")
            
            # Save results if output path provided
            if output_path:
                logger.info(f"Saving results to {output_path}")
                result_df.write.mode("overwrite").parquet(output_path)
            
            return result_df
            
        except Exception as e:
            logger.error(f"K-mer analysis failed: {e}")
            raise RuntimeError(f"K-mer analysis failed: {e}") from e
    
    def _count_kmers_rdd(self, df: DataFrame, skip_n: bool, min_count: int) -> DataFrame:
        """
        Count k-mers using pure RDD operations.
        
        This approach:
        1. Uses mapPartitions to extract k-mers and pre-aggregate with Counter
        2. Uses reduceByKey to sum counts across partitions
        3. Converts final RDD to DataFrame
        
        The Counter pre-aggregation is key: for k=6 there are only 4^6=4096 possible
        k-mers, so each partition outputs at most 4096 (kmer, count) pairs instead
        of millions of individual k-mers.
        """
        k = self.k
        
        def extract_kmers_from_partition(partition):
            """
            Extract k-mers from sequences in a partition with pre-aggregation.
            
            Uses Counter to aggregate within the partition, yielding (kmer, count)
            pairs instead of individual k-mers. This dramatically reduces shuffle data.
            """
            from collections import Counter
            
            kmer_counts = Counter()
            
            for row in partition:
                seq = row.sequence
                if not seq or len(seq) < k:
                    continue
                    
                seq_upper = str(seq).upper()
                seq_len = len(seq_upper)
                
                # Extract all k-mers from sequence
                for i in range(seq_len - k + 1):
                    kmer = seq_upper[i:i+k]
                    
                    # Skip k-mers with ambiguous bases if requested
                    if skip_n and 'N' in kmer:
                        continue
                    
                    kmer_counts[kmer] += 1
            
            # Yield (kmer, count) pairs
            for kmer, count in kmer_counts.items():
                yield (kmer, count)
        
        # Convert DataFrame to RDD and process
        sequences_rdd = df.rdd
        num_partitions = sequences_rdd.getNumPartitions()
        logger.info(f"Processing {num_partitions} partitions")
        
        # MAP: Extract k-mers with partition-level pre-aggregation
        kmer_pairs_rdd = sequences_rdd.mapPartitions(extract_kmers_from_partition)
        
        # REDUCE: Sum counts across partitions
        kmer_totals_rdd = kmer_pairs_rdd.reduceByKey(lambda a, b: a + b)
        
        # Apply min_count filter if needed
        if min_count > 1:
            kmer_totals_rdd = kmer_totals_rdd.filter(lambda x: x[1] >= min_count)
        
        # Convert to DataFrame with proper schema
        schema = T.StructType([
            T.StructField("kmer", T.StringType(), False),
            T.StructField("count", T.LongType(), False)
        ])
        
        result_df = kmer_totals_rdd.toDF(schema)
        
        # Sort by count descending and cache
        result_df = result_df.orderBy(F.desc("count")).cache()
        
        return result_df
    
    def get_statistics(self, kmer_df: DataFrame) -> Dict[str, Any]:
        """
        Calculate k-mer statistics.
        
        Args:
            kmer_df: K-mer frequency DataFrame
            
        Returns:
            Dictionary with statistics:
                - total_kmers: Total unique k-mers
                - total_count: Sum of all k-mer occurrences
                - mean_count: Average frequency
                - max_count: Maximum frequency
                - min_count: Minimum frequency
        """
        stats = kmer_df.agg(
            F.count("*").alias("total_kmers"),
            F.sum("count").alias("total_count"),
            F.mean("count").alias("mean_count"),
            F.max("count").alias("max_count"),
            F.min("count").alias("min_count")
        ).first()
        
        return {
            "total_kmers": stats["total_kmers"],
            "total_count": stats["total_count"],
            "mean_count": round(stats["mean_count"], 2),
            "max_count": stats["max_count"],
            "min_count": stats["min_count"]
        }
    
    def get_top_kmers(self, kmer_df: DataFrame, n: int = 20) -> list:
        """
        Get top N most frequent k-mers.
        
        Args:
            kmer_df: K-mer frequency DataFrame
            n: Number of top k-mers to return
            
        Returns:
            List of (kmer, count) tuples
        """
        top = kmer_df.limit(n).collect()
        return [(row["kmer"], row["count"]) for row in top]
