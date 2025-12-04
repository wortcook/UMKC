"""
Sequence search functionality using Spark for distributed pattern matching.
"""

import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql import types as T


logger = logging.getLogger(__name__)


class SequenceSearcher:
    """Search for sequences containing a specific pattern using distributed processing."""
    
    def __init__(self, spark: SparkSession):
        """
        Initialize sequence searcher.
        
        Args:
            spark: Active Spark session
        """
        self.spark = spark
        logger.info("Initialized sequence searcher")
    
    def search(
        self,
        input_path: str,
        pattern: str,
        output_path: Optional[str] = None,
        case_sensitive: bool = False,
        max_results: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Search for sequences containing the specified pattern.
        
        Args:
            input_path: Path to parquet files with sequence data
            pattern: DNA sequence pattern to search for (e.g., "ACGACGACGGGGACG")
            output_path: Optional path to save results as parquet
            case_sensitive: Whether to perform case-sensitive search (default: False)
            max_results: Maximum number of results to return (default: None for all)
        
        Returns:
            Dictionary with search statistics and results
        """
        logger.info(f"Searching for pattern '{pattern}' in {input_path}")
        
        # Validate pattern
        pattern = pattern.strip()
        if not pattern:
            raise ValueError("Search pattern cannot be empty")
        
        # Normalize pattern if case-insensitive
        search_pattern = pattern.upper() if not case_sensitive else pattern
        
        # Load sequence data
        try:
            df = self.spark.read.parquet(input_path)
            total_sequences = df.count()
            logger.info(f"Loaded {total_sequences:,} sequences")
        except Exception as e:
            logger.error(f"Failed to load data from {input_path}: {e}")
            raise
        
        # Prepare sequence column for searching
        if case_sensitive:
            search_col = F.col("sequence")
        else:
            search_col = F.upper(F.col("sequence"))
        
        # Filter sequences containing the pattern
        matches = df.filter(search_col.contains(search_pattern))
        
        # Add match position information
        matches = matches.withColumn(
            "match_position",
            F.expr(f"locate('{search_pattern}', {'sequence' if case_sensitive else 'upper(sequence)'})")
        )
        
        # Count occurrences of pattern in each sequence
        if case_sensitive:
            count_expr = f"size(split(sequence, '{search_pattern}')) - 1"
        else:
            count_expr = f"size(split(upper(sequence), '{search_pattern}')) - 1"
        
        matches = matches.withColumn(
            "match_count",
            F.expr(count_expr)
        )
        
        # Add sequence length and match percentage
        matches = matches.withColumn(
            "sequence_length",
            F.length(F.col("sequence"))
        ).withColumn(
            "pattern_coverage",
            (F.col("match_count") * F.lit(len(pattern))) / F.col("sequence_length") * 100
        )
        
        # Sort by match count (most matches first) and limit if requested
        matches = matches.orderBy(F.col("match_count").desc(), F.col("sequence_length").desc())
        
        if max_results:
            matches = matches.limit(max_results)
        
        # Collect statistics
        match_count = matches.count()
        
        # Save results if output path specified
        if output_path:
            output_path_obj = Path(output_path)
            output_path_obj.parent.mkdir(parents=True, exist_ok=True)
            matches.write.mode('overwrite').parquet(output_path)
            logger.info(f"Results saved to {output_path}")
        
        # Collect sample results for preview
        sample_results = matches.limit(10).select(
            "sequence_id",
            "description", 
            "match_count",
            "match_position",
            "sequence_length",
            "pattern_coverage"
        ).collect()
        
        results = {
            'pattern': pattern,
            'case_sensitive': case_sensitive,
            'total_sequences_searched': total_sequences,
            'matching_sequences': match_count,
            'match_percentage': round((match_count / total_sequences * 100) if total_sequences > 0 else 0, 2),
            'pattern_length': len(pattern),
            'output_path': output_path,
            'sample_matches': [
                {
                    'sequence_id': row.sequence_id,
                    'description': row.description,
                    'match_count': row.match_count,
                    'match_position': row.match_position,
                    'sequence_length': row.sequence_length,
                    'pattern_coverage': round(row.pattern_coverage, 2)
                }
                for row in sample_results
            ]
        }
        
        logger.info(
            f"Search complete: {match_count:,} matches out of {total_sequences:,} sequences "
            f"({results['match_percentage']}%)"
        )
        
        return results
    
    def search_multiple(
        self,
        input_path: str,
        patterns: List[str],
        output_path: Optional[str] = None,
        case_sensitive: bool = False
    ) -> Dict[str, Any]:
        """
        Search for multiple patterns in sequences.
        
        Args:
            input_path: Path to parquet files with sequence data
            patterns: List of DNA sequence patterns to search for
            output_path: Optional path to save results as parquet
            case_sensitive: Whether to perform case-sensitive search
        
        Returns:
            Dictionary with combined search results for all patterns
        """
        logger.info(f"Searching for {len(patterns)} patterns in {input_path}")
        
        results = {
            'patterns': patterns,
            'case_sensitive': case_sensitive,
            'pattern_results': []
        }
        
        for pattern in patterns:
            try:
                pattern_result = self.search(
                    input_path=input_path,
                    pattern=pattern,
                    output_path=None,  # Don't save individual results
                    case_sensitive=case_sensitive,
                    max_results=None
                )
                results['pattern_results'].append(pattern_result)
            except Exception as e:
                logger.error(f"Failed to search pattern '{pattern}': {e}")
                results['pattern_results'].append({
                    'pattern': pattern,
                    'error': str(e)
                })
        
        # Save combined results if output path specified
        if output_path and results['pattern_results']:
            # This would require combining all pattern results - simplified for now
            logger.info(f"Combined results would be saved to {output_path}")
        
        return results
