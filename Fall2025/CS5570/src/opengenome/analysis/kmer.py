"""
K-mer frequency analysis using Spark MapReduce.
"""

import logging
from typing import Optional, Dict, Any
from pathlib import Path

import pandas as pd
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql import types as T


logger = logging.getLogger(__name__)


class KmerAnalyzer:
    """K-mer frequency analysis using distributed MapReduce."""
    
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
        
        logger.info(f"Initialized k-mer analyzer (k={k})")
    
    def analyze(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        skip_n: bool = True,
        min_count: int = 1
    ) -> DataFrame:
        """
        Perform k-mer frequency analysis.
        
        MapReduce workflow:
        1. MAP: Extract k-mers from each sequence
        2. SHUFFLE: Group by k-mer
        3. REDUCE: Count occurrences
        
        Args:
            input_path: Path to Parquet files with sequences
            output_path: Optional path to save results
            skip_n: Skip k-mers containing 'N' (ambiguous base)
            min_count: Minimum frequency threshold
            
        Returns:
            DataFrame with columns: kmer, count
            
        Raises:
            RuntimeError: If analysis fails
        """
        try:
            logger.info(f"Starting k-mer analysis (k={self.k})")
            logger.info(f"Input: {input_path}")
            logger.info(f"Skip N: {skip_n}, Min count: {min_count}")
            
            # Load sequences
            df = self.spark.read.parquet(input_path)
            total_sequences = df.count()
            logger.info(f"Loaded {total_sequences:,} sequences")
            
            # MAP: Generate k-mers using SQL
            # Use substring and sequence to extract all k-mers
            kmer_df = self._extract_kmers(df, skip_n)
            
            # REDUCE: Count k-mer frequencies
            result_df = (
                kmer_df
                .groupBy("kmer")
                .agg(F.count("*").alias("count"))
                .filter(F.col("count") >= min_count)
                .orderBy(F.desc("count"))
                .cache()
            )
            
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
    
    def _extract_kmers(self, df: DataFrame, skip_n: bool) -> DataFrame:
        """
        Extract k-mers from sequences using memory-efficient approach.
        
        Strategy: Use mapPartitions with iterator to avoid loading all k-mers
        into memory at once. Process sequences one at a time and yield k-mers.
        
        Args:
            df: DataFrame with 'sequence' column
            skip_n: Skip k-mers containing 'N'
            
        Returns:
            DataFrame with 'kmer' column
        """
        k = self.k
        
        # Use pandas UDF for better performance and memory efficiency
        @F.pandas_udf(T.StringType())
        def extract_single_kmer(sequences: pd.Series, positions: pd.Series) -> pd.Series:
            """Extract a single k-mer at given position from each sequence."""
            import pandas as pd
            result = []
            for seq, pos in zip(sequences, positions):
                if seq and len(seq) >= pos + k:
                    kmer = seq[pos:pos+k].upper()
                    result.append(kmer)
                else:
                    result.append(None)
            return pd.Series(result)
        
        # Create a more memory-efficient approach:
        # 1. Add sequence ID and length
        # 2. Generate position array for each sequence
        # 3. Extract kmers at each position
        
        # For now, use a simpler but less memory-efficient approach
        # that's good enough for our 10k test dataset        
        schema = T.StructType([T.StructField("kmer", T.StringType(), False)])
        
        def extract_kmers_partition(iterator):
            """Process one partition at a time, yielding in batches."""
            import pandas as pd_local
            
            batch_size = 10000  # Yield every 10k k-mers to limit memory
            
            for pdf in iterator:
                kmers = []
                for seq in pdf['sequence']:
                    if not seq or len(seq) < k:
                        continue
                    seq_upper = str(seq).upper()
                    for i in range(len(seq_upper) - k + 1):
                        kmer = seq_upper[i:i+k]
                        if skip_n and 'N' in kmer:
                            continue
                        kmers.append((kmer,))
                        
                        # Yield batch to limit memory usage
                        if len(kmers) >= batch_size:
                            yield pd_local.DataFrame(kmers, columns=['kmer'])
                            kmers = []
                
                # Yield remaining k-mers from this partition
                if kmers:
                    yield pd_local.DataFrame(kmers, columns=['kmer'])
        
        kmer_df = df.mapInPandas(extract_kmers_partition, schema=schema)
        return kmer_df
    
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
