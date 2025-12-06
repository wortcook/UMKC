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
        chunk_rows: int = 50,
        max_shard_size: Optional[int] = None,
        compression: str = "snappy",
        output_dir: Optional[Path] = None
    ):
        """
        Initialize FASTA to Parquet converter.
        
        Args:
            chunk_rows: Maximum number of sequences per Parquet shard (deprecated, use max_shard_size)
            max_shard_size: Maximum total bytes per shard (e.g., 500000 = 500KB). Overrides chunk_rows.
            compression: Compression codec (snappy, gzip, zstd, none)
            output_dir: Output directory for Parquet files
        """
        self.chunk_rows = chunk_rows
        self.max_shard_size = max_shard_size
        self.compression = compression
        self.output_dir = output_dir or Path("/data/parquet")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        if max_shard_size:
            logger.info(f"Initialized converter: max {max_shard_size:,} bytes/shard, {compression} compression")
        else:
            logger.info(f"Initialized converter: {chunk_rows} rows/shard, {compression} compression")
        logger.info(f"Output directory: {self.output_dir}")
    
    def convert(
        self,
        fasta_path: Path,
        source_name: str = "organelle",
        output_subdir: Optional[str] = None,
        max_sequences: Optional[int] = None,
        append: bool = False
    ) -> Dict[str, Any]:
        """
        Convert FASTA file to Parquet shards.
        
        Args:
            fasta_path: Path to FASTA file (gzipped or plain)
            source_name: Source identifier for the sequences
            output_subdir: Optional subdirectory for output files
            max_sequences: Maximum number of sequences to process (for testing)
            append: If True, append to existing shards instead of overwriting
            
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
        
        # Detect existing shards if appending
        starting_shard_idx = 0
        if append:
            existing_shards = sorted(output_path.glob("shard_*.parquet"))
            if existing_shards:
                # Extract the highest shard number
                last_shard = existing_shards[-1]
                last_idx = int(last_shard.stem.split('_')[1])
                starting_shard_idx = last_idx + 1
                logger.info(f"Append mode: Found {len(existing_shards)} existing shards, starting at shard {starting_shard_idx}")
            else:
                logger.info(f"Append mode: No existing shards found, starting at shard 0")
        
        row_buffer = []
        current_shard_bytes = 0
        shard_idx = starting_shard_idx
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
                    current_shard_bytes += seq_length
                    
                    # Check max sequences limit
                    if max_sequences and total_sequences >= max_sequences:
                        logger.info(f"Reached max sequences limit: {max_sequences:,}")
                        break
                    
                    # Flush chunk based on size or row count
                    should_flush = False
                    if self.max_shard_size:
                        # Size-based sharding
                        should_flush = current_shard_bytes >= self.max_shard_size
                    else:
                        # Row-based sharding (legacy)
                        should_flush = len(row_buffer) >= self.chunk_rows
                    
                    if should_flush:
                        self._flush_chunk(row_buffer, output_path, shard_idx)
                        shard_idx += 1
                        row_buffer = []
                        current_shard_bytes = 0
                        
                        # Log progress every 10 shards
                        if shard_idx % 10 == 0:
                            logger.info(
                                f"Processed {total_sequences:,} sequences "
                                f"({total_bases:,} bases) - {shard_idx} shards"
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
                "total_shards": shard_idx - starting_shard_idx,
                "output_path": str(output_path),
                "total_bases": total_bases,
                "starting_shard": starting_shard_idx,
                "ending_shard": shard_idx - 1 if shard_idx > starting_shard_idx else starting_shard_idx
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
