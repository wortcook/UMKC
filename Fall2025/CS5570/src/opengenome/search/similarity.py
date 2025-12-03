"""
Sequence search module for k-mer-based similarity search.

This module implements TF-IDF vectorization and cosine similarity search
for finding similar sequences based on k-mer composition.
"""

import logging
from typing import Optional, Dict, Tuple
from collections import Counter

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql import types as T

logger = logging.getLogger(__name__)


class SequenceSearcher:
    """
    K-mer based sequence similarity search using TF-IDF and cosine similarity.
    
    This class builds an index of k-mer term frequencies for sequences and
    enables similarity search using cosine similarity on TF-IDF vectors.
    """
    
    def __init__(self, spark: SparkSession, k: int = 6):
        """
        Initialize sequence searcher.
        
        Args:
            spark: Active Spark session
            k: K-mer length (default: 6)
        """
        self.spark = spark
        self.k = k
        self.tf_counts = None  # Per-sequence k-mer term frequencies
        self.idf_values = None  # Inverse document frequencies
        self.seq_norms = None  # L2 norms for normalization
        logger.info(f"Initialized SequenceSearcher with k={k}")
    
    def build_index(
        self,
        input_path: str,
        skip_n: bool = True,
        max_sequences: Optional[int] = None
    ) -> None:
        """
        Build search index from sequence data.
        
        This extracts k-mers from sequences, computes term frequencies (TF),
        document frequencies (DF), and inverse document frequencies (IDF).
        
        Args:
            input_path: Path to sequence data (Parquet)
            skip_n: Skip k-mers containing 'N'
            max_sequences: Limit number of sequences to index
        """
        try:
            logger.info(f"Building search index from {input_path}")
            
            # Load sequences
            df = self.spark.read.parquet(input_path)
            if max_sequences:
                df = df.limit(max_sequences)
                logger.info(f"Limited to {max_sequences} sequences")
            
            # Extract k-mers per sequence with counts (TF)
            logger.info("Extracting k-mers and computing term frequencies...")
            self.tf_counts = self._extract_kmer_tf(df, skip_n)
            
            # Compute document frequency (DF) - number of sequences containing each k-mer
            logger.info("Computing document frequencies...")
            total_docs = df.count()
            df_counts = (
                self.tf_counts
                .groupBy("kmer")
                .agg(F.countDistinct("seq_id").alias("doc_freq"))
            )
            
            # Compute IDF: log(total_docs / doc_freq)
            logger.info("Computing inverse document frequencies...")
            self.idf_values = (
                df_counts
                .withColumn(
                    "idf",
                    F.log((F.lit(total_docs) / F.col("doc_freq")))
                )
                .select("kmer", "idf")
            )
            
            # Compute L2 norms for TF-IDF vectors (for cosine similarity)
            logger.info("Computing vector norms...")
            tf_idf = (
                self.tf_counts
                .join(self.idf_values, on="kmer", how="left")
                .withColumn("tf_idf", F.col("count") * F.col("idf"))
            )
            
            self.seq_norms = (
                tf_idf
                .groupBy("seq_id")
                .agg(
                    F.sqrt(F.sum(F.col("tf_idf") * F.col("tf_idf"))).alias("norm")
                )
            )
            
            # Cache for repeated searches
            self.tf_counts.cache()
            self.idf_values.cache()
            self.seq_norms.cache()
            
            logger.info(f"✓ Index built: {total_docs} sequences, "
                       f"{self.idf_values.count()} unique k-mers")
            
        except Exception as e:
            logger.error(f"Failed to build search index: {e}")
            raise RuntimeError(f"Index building failed: {e}") from e
    
    def _extract_kmer_tf(self, df: DataFrame, skip_n: bool) -> DataFrame:
        """
        Extract k-mers from sequences and compute term frequencies.
        
        Args:
            df: DataFrame with sequence column
            skip_n: Skip k-mers containing 'N'
            
        Returns:
            DataFrame with columns: seq_id, kmer, count
        """
        k = self.k
        schema = T.StructType([
            T.StructField("seq_id", T.StringType(), False),
            T.StructField("kmer", T.StringType(), False),
            T.StructField("count", T.LongType(), False)
        ])
        
        def extract_kmers_partition(iterator):
            """Extract k-mers from sequences in partition."""
            import pandas as pd_local
            from collections import Counter
            
            for pdf in iterator:
                results = []
                for seq_id, sequence in zip(pdf['seq_id'], pdf['sequence']):
                    if not sequence or len(sequence) < k:
                        continue
                    
                    seq_upper = str(sequence).upper()
                    kmer_counts = Counter()
                    
                    # Extract k-mers
                    for i in range(len(seq_upper) - k + 1):
                        kmer = seq_upper[i:i+k]
                        # Skip if contains non-standard bases
                        if skip_n and not all(base in 'ATGC' for base in kmer):
                            continue
                        kmer_counts[kmer] += 1
                    
                    # Emit (seq_id, kmer, count) tuples
                    for kmer, count in kmer_counts.items():
                        results.append((seq_id, kmer, count))
                
                if results:
                    yield pd_local.DataFrame(results, columns=['seq_id', 'kmer', 'count'])
        
        return df.mapInPandas(extract_kmers_partition, schema=schema)
    
    def search(
        self,
        query_sequence: str,
        top_n: int = 20,
        use_idf: bool = True,
        skip_n: bool = True
    ) -> DataFrame:
        """
        Search for sequences similar to query using cosine similarity.
        
        Args:
            query_sequence: Query sequence string
            top_n: Number of top results to return
            use_idf: Use IDF weighting (TF-IDF vs just TF)
            skip_n: Skip query k-mers containing 'N'
            
        Returns:
            DataFrame with columns: seq_id, similarity, rank
            
        Raises:
            RuntimeError: If index not built
        """
        if self.tf_counts is None:
            raise RuntimeError("Index not built. Call build_index() first.")
        
        try:
            logger.info(f"Searching for top {top_n} similar sequences...")
            
            # Extract k-mers from query
            query_kmers = self._query_to_kmers(query_sequence, skip_n)
            if not query_kmers:
                logger.warning("No valid k-mers in query")
                return self.spark.createDataFrame(
                    [],
                    schema=T.StructType([
                        T.StructField("seq_id", T.StringType(), False),
                        T.StructField("similarity", T.FloatType(), False),
                        T.StructField("rank", T.IntegerType(), False)
                    ])
                )
            
            # Convert to DataFrame
            query_df = self.spark.createDataFrame(
                [(kmer, count) for kmer, count in query_kmers.items()],
                schema=T.StructType([
                    T.StructField("kmer", T.StringType(), False),
                    T.StructField("q_count", T.LongType(), False)
                ])
            )
            
            # Apply IDF if requested
            if use_idf and self.idf_values is not None:
                query_df = (
                    query_df
                    .join(self.idf_values, on="kmer", how="left")
                    .fillna(0.0, subset=["idf"])
                    .withColumn("q_weight", F.col("q_count") * F.col("idf"))
                )
            else:
                query_df = query_df.withColumn("q_weight", F.col("q_count").cast("double"))
            
            # Compute query norm
            query_norm = query_df.agg(
                F.sqrt(F.sum(F.col("q_weight") * F.col("q_weight"))).alias("q_norm")
            ).first()["q_norm"]
            
            if query_norm == 0:
                logger.warning("Query vector has zero norm")
                return self.spark.createDataFrame([], schema="seq_id string, similarity float, rank int")
            
            # Join with document k-mers
            doc_query = (
                self.tf_counts
                .join(query_df.select("kmer", "q_weight"), on="kmer", how="inner")
            )
            
            # Apply IDF to document k-mers if requested
            if use_idf and self.idf_values is not None:
                doc_query = (
                    doc_query
                    .join(self.idf_values, on="kmer", how="left")
                    .fillna(0.0, subset=["idf"])
                    .withColumn("d_weight", F.col("count") * F.col("idf"))
                )
            else:
                doc_query = doc_query.withColumn("d_weight", F.col("count").cast("double"))
            
            # Compute dot products
            dot_products = (
                doc_query
                .groupBy("seq_id")
                .agg(F.sum(F.col("d_weight") * F.col("q_weight")).alias("dot_product"))
            )
            
            # Compute cosine similarity
            similarities = (
                dot_products
                .join(self.seq_norms, on="seq_id", how="left")
                .fillna(1.0, subset=["norm"])  # Handle sequences with zero norm
                .withColumn(
                    "similarity",
                    F.col("dot_product") / (F.col("norm") * F.lit(query_norm))
                )
                .select("seq_id", "similarity")
                .orderBy(F.desc("similarity"))
                .limit(top_n)
            )
            
            # Add rank
            result = similarities.withColumn(
                "rank",
                F.row_number().over(F.Window.orderBy(F.desc("similarity")))
            )
            
            logger.info(f"✓ Search complete, returning top {top_n} results")
            return result
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise RuntimeError(f"Search failed: {e}") from e
    
    def _query_to_kmers(self, query_sequence: str, skip_n: bool) -> Dict[str, int]:
        """
        Extract k-mers from query sequence.
        
        Args:
            query_sequence: Query sequence string
            skip_n: Skip k-mers containing 'N'
            
        Returns:
            Dictionary of k-mer -> count
        """
        if not query_sequence:
            return {}
        
        seq_upper = query_sequence.upper()
        kmer_counts = Counter()
        
        for i in range(len(seq_upper) - self.k + 1):
            kmer = seq_upper[i:i+self.k]
            # Skip if contains non-standard bases
            if skip_n and not all(base in 'ATGC' for base in kmer):
                continue
            kmer_counts[kmer] += 1
        
        return dict(kmer_counts)
    
    def get_statistics(self) -> Optional[Dict[str, int]]:
        """
        Get index statistics.
        
        Returns:
            Dictionary with index statistics or None if not built
        """
        if self.tf_counts is None:
            return None
        
        try:
            num_sequences = self.seq_norms.count() if self.seq_norms else 0
            num_kmers = self.idf_values.count() if self.idf_values else 0
            
            return {
                "num_sequences": num_sequences,
                "num_unique_kmers": num_kmers,
                "k": self.k
            }
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return None
