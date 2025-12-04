"""
Sequence search functionality using Spark for distributed pattern matching.
"""

import logging
import re
from typing import Optional, Dict, Any, List
from pathlib import Path

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql import types as T


logger = logging.getLogger()


class SequenceSearcher:
    """Search for sequences containing a specific pattern using distributed processing."""
    
    # DNA complement mapping for reverse complement
    DNA_COMPLEMENT = str.maketrans('ACGTNacgtn', 'TGCANtgcan')
    
    def __init__(self, spark: SparkSession):
        """
        Initialize sequence searcher.
        
        Args:
            spark: Active Spark session
        """
        self.spark = spark
        logger.info("Initialized sequence searcher")
    
    @staticmethod
    def reverse_complement(sequence: str) -> str:
        """
        Generate reverse complement of a DNA sequence.
        
        Args:
            sequence: DNA sequence string
            
        Returns:
            Reverse complement of the sequence
        """
        return sequence.translate(SequenceSearcher.DNA_COMPLEMENT)[::-1]
    
    @staticmethod
    def validate_dna_pattern(pattern: str) -> None:
        """
        Validate that pattern contains only valid DNA characters.
        
        Args:
            pattern: Pattern to validate
            
        Raises:
            ValueError: If pattern contains invalid characters
        """
        if not pattern:
            raise ValueError("Search pattern cannot be empty")
        
        if not re.match(r'^[ACGTNacgtn]+$', pattern):
            invalid_chars = set(c for c in pattern if c not in 'ACGTNacgtn')
            raise ValueError(
                f"Pattern contains invalid DNA characters: {invalid_chars}. "
                "Only A, C, G, T, N are allowed."
            )
        
        if len(pattern) < 3:
            logger.warning(f"Short pattern ({len(pattern)} bp) may return many results")
        
        if len(pattern) > 100:
            logger.warning(f"Long pattern ({len(pattern)} bp) may have few or no matches")
    
    def search(
        self,
        input_path: str,
        pattern: str,
        output_path: Optional[str] = None,
        case_sensitive: bool = False,
        max_results: Optional[int] = None,
        search_reverse_complement: bool = False
    ) -> Dict[str, Any]:
        """
        Search for sequences containing the specified pattern.
        
        Args:
            input_path: Path to parquet files with sequence data
            pattern: DNA sequence pattern to search for (e.g., "ACGACGACGGGGACG")
            output_path: Optional path to save results as parquet
            case_sensitive: Whether to perform case-sensitive search (default: False)
            max_results: Maximum number of results to return (default: None for all)
            search_reverse_complement: Also search for reverse complement (default: False)
        
        Returns:
            Dictionary with search statistics and results
            
        Examples:
            >>> searcher = SequenceSearcher(spark)
            >>> results = searcher.search("/data/organelles", "ACGACG")
            >>> print(f"Found {results['matching_sequences']} matches")
        """
        logger.info(f"Searching for pattern '{pattern}' in {input_path}")
        
        # Validate and clean pattern
        pattern = pattern.strip()
        self.validate_dna_pattern(pattern)
        
        # Calculate reverse complement if needed
        rev_comp = None
        search_rev_comp = None
        if search_reverse_complement:
            rev_comp = self.reverse_complement(pattern)
            logger.info(f"Also searching for reverse complement: {rev_comp}")
        
        # Normalize pattern if case-insensitive
        search_pattern = pattern.upper() if not case_sensitive else pattern
        if rev_comp:
            search_rev_comp = rev_comp.upper() if not case_sensitive else rev_comp
        
        # Load sequence data
        try:
            df = self.spark.read.parquet(input_path)
            
            # Validate schema
            if 'sequence' not in df.columns:
                raise ValueError(f"Input data missing required 'sequence' column. Found: {df.columns}")
            
            total_sequences = df.count()
            logger.info(f"Loaded {total_sequences:,} sequences")
            
            if total_sequences == 0:
                logger.warning("No sequences found in input data")
                return {
                    'pattern': pattern,
                    'case_sensitive': case_sensitive,
                    'search_reverse_complement': search_reverse_complement,
                    'total_sequences_searched': 0,
                    'matching_sequences': 0,
                    'match_percentage': 0,
                    'pattern_length': len(pattern),
                    'output_path': output_path,
                    'sample_matches': []
                }
        except Exception as e:
            logger.error(f"Failed to load data from {input_path}: {e}")
            raise
        
        # Escape pattern for SQL (replace single quotes)
        escaped_pattern = search_pattern.replace("'", "''")
        escaped_rev_comp = search_rev_comp.replace("'", "''") if rev_comp else None
        
        # Prepare sequence column for searching
        if case_sensitive:
            search_col = F.col("sequence")
        else:
            search_col = F.upper(F.col("sequence"))
        
        # Filter sequences containing the pattern (or reverse complement)
        if search_reverse_complement and rev_comp:
            # Search for either pattern or its reverse complement
            filter_condition = (
                search_col.contains(escaped_pattern) | 
                search_col.contains(escaped_rev_comp)
            )
            matches = df.filter(filter_condition)
        else:
            matches = df.filter(search_col.contains(escaped_pattern))
        
        # Add match information for forward pattern
        seq_expr = 'sequence' if case_sensitive else 'upper(sequence)'
        matches = matches.withColumn(
            "match_position",
            F.expr(f"locate('{escaped_pattern}', {seq_expr})")
        ).withColumn(
            "match_count",
            F.expr(f"size(split({seq_expr}, '{escaped_pattern}')) - 1")
        )
        
        # Add reverse complement match info if requested
        if search_reverse_complement and rev_comp:
            matches = matches.withColumn(
                "rev_comp_position",
                F.expr(f"locate('{escaped_rev_comp}', {seq_expr})")
            ).withColumn(
                "rev_comp_count",
                F.expr(f"size(split({seq_expr}, '{escaped_rev_comp}')) - 1")
            ).withColumn(
                "total_match_count",
                F.col("match_count") + F.col("rev_comp_count")
            )
            sort_col = "total_match_count"
        else:
            sort_col = "match_count"
        
        # Add sequence length and match percentage
        matches = matches.withColumn(
            "sequence_length",
            F.length(F.col("sequence"))
        ).withColumn(
            "pattern_coverage",
            (F.col(sort_col) * F.lit(len(pattern))) / F.col("sequence_length") * 100
        )
        
        # Sort by match count (most matches first) and limit if requested
        matches = matches.orderBy(F.col(sort_col).desc(), F.col("sequence_length").desc())
        
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
        select_cols = [
            "sequence_id",
            "description", 
            "match_count",
            "match_position",
            "sequence_length",
            "pattern_coverage"
        ]
        
        if search_reverse_complement and rev_comp:
            select_cols.extend(["rev_comp_count", "rev_comp_position", "total_match_count"])
        
        sample_results = matches.limit(10).select(*select_cols).collect()
        
        # Build result dictionary
        sample_matches = []
        for row in sample_results:
            match_dict = {
                'sequence_id': row.sequence_id,
                'description': row.description,
                'match_count': row.match_count,
                'match_position': row.match_position,
                'sequence_length': row.sequence_length,
                'pattern_coverage': round(row.pattern_coverage, 2)
            }
            if search_reverse_complement and rev_comp:
                match_dict.update({
                    'rev_comp_count': row.rev_comp_count,
                    'rev_comp_position': row.rev_comp_position,
                    'total_match_count': row.total_match_count
                })
            sample_matches.append(match_dict)
        
        results = {
            'pattern': pattern,
            'case_sensitive': case_sensitive,
            'search_reverse_complement': search_reverse_complement,
            'total_sequences_searched': total_sequences,
            'matching_sequences': match_count,
            'match_percentage': round((match_count / total_sequences * 100) if total_sequences > 0 else 0, 2),
            'pattern_length': len(pattern),
            'output_path': output_path,
            'sample_matches': sample_matches
        }
        
        if rev_comp:
            results['reverse_complement_pattern'] = rev_comp
        
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
