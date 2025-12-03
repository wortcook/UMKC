"""
FASTA to Parquet converter for genomic sequences.
"""

import gzip
import logging
from pathlib import Path
from typing import Optional, Dict, Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from Bio import SeqIO


logger = logging.getLogger(__name__)


class FASTAToParquetConverter:
    """Converts FASTA files to Parquet format for Spark processing."""
    
    def __init__(
        self,
        chunk_rows: int = 50_000,
        compression: str = "snappy",
        output_dir: Optional[Path] = None
    ):
        """
        Initialize FASTA to Parquet converter.
        
        Args:
            chunk_rows: Number of sequences per Parquet shard
            compression: Compression codec (snappy, gzip, zstd, none)
            output_dir: Output directory for Parquet files
        """
        self.chunk_rows = chunk_rows
        self.compression = compression
        self.output_dir = output_dir or Path("/data/parquet")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized converter: {chunk_rows} rows/shard, {compression} compression")
        logger.info(f"Output directory: {self.output_dir}")
    
    def convert(
        self,
        fasta_path: Path,
        source_name: str = "organelle",
        output_subdir: Optional[str] = None,
        max_sequences: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Convert FASTA file to Parquet shards.
        
        Args:
            fasta_path: Path to FASTA file (gzipped or plain)
            source_name: Source identifier for the sequences
            output_subdir: Optional subdirectory for output files
            max_sequences: Maximum number of sequences to process (for testing)
            
        Returns:
            Dict with conversion statistics:
                - total_sequences: Total number of sequences processed
                - total_shards: Number of Parquet shards created
                - output_path: Path to output directory
                - total_bases: Total number of bases processed
                
        Raises:
            RuntimeError: If conversion fails
        """
        output_path = self.output_dir
        if output_subdir:
            output_path = output_path / output_subdir
            output_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Converting {fasta_path} to Parquet")
        logger.info(f"Output: {output_path}")
        if max_sequences:
            logger.info(f"Max sequences: {max_sequences:,} (testing mode)")
        
        row_buffer = []
        shard_idx = 1
        total_sequences = 0
        total_bases = 0
        
        try:
            # Determine if file is gzipped
            is_gzipped = str(fasta_path).endswith('.gz')
            
            # Open file (gzipped or plain)
            if is_gzipped:
                file_handle = gzip.open(fasta_path, "rt")
            else:
                file_handle = open(fasta_path, "r")
            
            try:
                # Parse FASTA records
                for record in SeqIO.parse(file_handle, "fasta"):
                    sequence = str(record.seq)
                    seq_length = len(sequence)
                    
                    row_buffer.append({
                        "seq_id": record.id,
                        "description": record.description,
                        "length": seq_length,
                        "sequence": sequence,
                        "source": source_name
                    })
                    
                    total_sequences += 1
                    total_bases += seq_length
                    
                    # Check max sequences limit
                    if max_sequences and total_sequences >= max_sequences:
                        logger.info(f"Reached max sequences limit: {max_sequences:,}")
                        break
                    
                    # Flush chunk when buffer is full
                    if len(row_buffer) >= self.chunk_rows:
                        self._flush_chunk(row_buffer, output_path, shard_idx)
                        shard_idx += 1
                        row_buffer = []
                        
                        # Log progress every 10 shards
                        if (shard_idx - 1) % 10 == 0:
                            logger.info(
                                f"Processed {total_sequences:,} sequences "
                                f"({total_bases:,} bases) - {shard_idx - 1} shards"
                            )
                
                # Flush remaining records
                if row_buffer:
                    self._flush_chunk(row_buffer, output_path, shard_idx)
                
            finally:
                file_handle.close()
            
            total_shards = shard_idx if row_buffer else shard_idx - 1
            
            logger.info(f"Conversion complete:")
            logger.info(f"  Sequences: {total_sequences:,}")
            logger.info(f"  Total bases: {total_bases:,}")
            logger.info(f"  Shards: {total_shards}")
            logger.info(f"  Output: {output_path}")
            
            return {
                "total_sequences": total_sequences,
                "total_shards": total_shards,
                "output_path": str(output_path),
                "total_bases": total_bases
            }
            
        except Exception as e:
            logger.error(f"Conversion failed: {e}")
            raise RuntimeError(f"Failed to convert FASTA to Parquet: {e}") from e
    
    def _flush_chunk(
        self,
        rows: list,
        output_path: Path,
        shard_idx: int
    ) -> None:
        """
        Write a chunk of rows to a Parquet file.
        
        Args:
            rows: List of row dictionaries
            output_path: Directory to write Parquet file
            shard_idx: Shard index for filename
        """
        if not rows:
            return
        
        # Convert to pandas DataFrame
        df = pd.DataFrame(rows)
        
        # Convert to PyArrow table
        table = pa.Table.from_pandas(df, preserve_index=False)
        
        # Write to Parquet
        shard_filename = f"shard_{shard_idx:05d}.parquet"
        shard_path = output_path / shard_filename
        
        pq.write_table(
            table,
            str(shard_path),
            compression=self.compression,
            use_dictionary=True
        )
        
        logger.debug(f"Wrote {len(rows)} rows to {shard_filename}")
