#!/usr/bin/env python3
"""
OpenGenome2 CLI - Main entry point

Command-line interface for distributed genomic sequence analysis.
"""

import sys
import os
import logging
import click
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from opengenome import __version__
from opengenome.spark.session import stop_spark_session

# Configure logging
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version=__version__, prog_name="opengenome")
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.pass_context
def cli(ctx, debug):
    """
    OpenGenome2 - Distributed Genomic Sequence Analysis
    
    A scalable platform for processing large FASTA files using Apache Spark.
    
    \b
    Common workflows:
      1. Ingest data:     opengenome ingest --input data.fasta
      2. Analyze k-mers:  opengenome analyze kmer --k 6
      3. Visualize:       opengenome visualize --output results/
    
    For command-specific help: opengenome COMMAND --help
    """
    # Store debug flag in context
    ctx.ensure_object(dict)
    ctx.obj["DEBUG"] = debug
    
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")


@cli.command()
@click.pass_context
def version(ctx):
    """Show version and environment information."""
    from opengenome.spark.session import get_spark_session, stop_spark_session
    from py4j.protocol import Py4JNetworkError
    
    click.echo(f"OpenGenome2 version: {__version__}")
    click.echo(f"Python: {sys.version.split()[0]}")
    
    try:
        spark = get_spark_session(app_name="VersionCheck")
        click.echo(f"Spark version: {spark.version}")
        click.echo(f"Spark master: {spark.sparkContext.master}")
        click.echo(f"Workers available: {spark.sparkContext.defaultParallelism // 2}")
        stop_spark_session()
    except Py4JNetworkError:
        click.echo("Spark: Not connected (network error - is Spark master running?)", err=True)
    except Exception as e:
        click.echo(f"Spark: Error connecting ({type(e).__name__}: {e})", err=True)


@cli.command()
def config():
    """Show current configuration from environment."""
    config_vars = [
        "SPARK_DRIVER_MEMORY",
        "SPARK_EXECUTOR_MEMORY",
        "SPARK_WORKER_MEMORY",
        "DATA_DIR",
        "RESULTS_DIR",
        "CACHE_DIR",
        "HF_REPO",
        "LOG_LEVEL",
        "DEBUG",
        "SAMPLE_MODE",
    ]
    
    click.echo("Current Configuration:")
    click.echo("=" * 50)
    
    for var in config_vars:
        value = os.environ.get(var, "(not set)")
        click.echo(f"  {var:30s} = {value}")
    
    click.echo("=" * 50)


@cli.group()
def ingest():
    """Data ingestion commands."""
    pass


@ingest.command("organelle")
@click.option(
    "--output",
    type=click.Path(),
    default="/data/parquet/organelle",
    help="Output directory for Parquet files"
)
@click.option(
    "--chunk-size",
    type=int,
    default=50000,
    help="Sequences per Parquet shard"
)
@click.option(
    "--compression",
    type=click.Choice(["snappy", "gzip", "zstd", "none"]),
    default="snappy",
    help="Compression codec"
)
@click.option(
    "--max-sequences",
    type=int,
    default=None,
    help="Maximum sequences to process (for testing)"
)
@click.pass_context
def ingest_organelle(ctx, output, chunk_size, compression, max_sequences):
    """
    Ingest organelle sequences from HuggingFace.
    
    Downloads the organelle FASTA file from arcinstitute/opengenome2
    and converts it to Parquet shards for Spark processing.
    
    \b
    Example:
        opengenome ingest organelle
        opengenome ingest organelle --chunk-size 100000 --compression zstd
    """
    from opengenome.ingestion import FASTADownloader, FASTAToParquetConverter
    
    try:
        click.echo("=" * 60)
        click.echo("OpenGenome2 Data Ingestion: Organelle Sequences")
        click.echo("=" * 60)
        
        # Step 1: Download FASTA
        click.echo("\n[1/2] Downloading organelle sequences from HuggingFace...")
        downloader = FASTADownloader()
        fasta_path = downloader.download_organelle_sequences()
        click.echo(f"✓ Downloaded to: {fasta_path}")
        
        # Step 2: Convert to Parquet
        click.echo(f"\n[2/2] Converting FASTA to Parquet...")
        click.echo(f"  Chunk size: {chunk_size:,} sequences/shard")
        click.echo(f"  Compression: {compression}")
        click.echo(f"  Output: {output}")
        
        converter = FASTAToParquetConverter(
            chunk_rows=chunk_size,
            compression=compression,
            output_dir=Path(output).parent
        )
        
        stats = converter.convert(
            fasta_path=fasta_path,
            source_name="organelle",
            output_subdir=Path(output).name,
            max_sequences=max_sequences
        )
        
        # Display results
        click.echo("\n" + "=" * 60)
        click.echo("Ingestion Complete!")
        click.echo("=" * 60)
        click.echo(f"  Total sequences: {stats['total_sequences']:,}")
        click.echo(f"  Total bases: {stats['total_bases']:,}")
        click.echo(f"  Parquet shards: {stats['total_shards']}")
        click.echo(f"  Output path: {stats['output_path']}")
        click.echo("=" * 60)
        
        if ctx.obj.get("DEBUG"):
            click.echo("\nDebug info:")
            click.echo(f"  FASTA path: {fasta_path}")
            click.echo(f"  Avg sequence length: {stats['total_bases'] // stats['total_sequences']:,}")
        
    except Exception as e:
        click.echo(f"\n✗ Ingestion failed: {e}", err=True)
        if ctx.obj.get("DEBUG"):
            import traceback
            click.echo("\n" + traceback.format_exc(), err=True)
        sys.exit(1)


@ingest.command("custom")
@click.option(
    "--filename",
    required=True,
    help="Filename within HuggingFace dataset"
)
@click.option(
    "--output",
    type=click.Path(),
    required=True,
    help="Output directory for Parquet files"
)
@click.option(
    "--source-name",
    default="custom",
    help="Source identifier for sequences"
)
@click.option(
    "--chunk-size",
    type=int,
    default=50000,
    help="Sequences per Parquet shard"
)
@click.option(
    "--compression",
    type=click.Choice(["snappy", "gzip", "zstd", "none"]),
    default="snappy",
    help="Compression codec"
)
@click.pass_context
def ingest_custom(ctx, filename, output, source_name, chunk_size, compression):
    """
    Ingest custom FASTA file from HuggingFace.
    
    \b
    Example:
        opengenome ingest custom \\
            --filename fasta/bacteria/ecoli.fasta.gz \\
            --output /data/parquet/ecoli \\
            --source-name ecoli
    """
    from opengenome.ingestion import FASTADownloader, FASTAToParquetConverter
    
    try:
        click.echo("=" * 60)
        click.echo(f"OpenGenome2 Data Ingestion: {filename}")
        click.echo("=" * 60)
        
        # Step 1: Download FASTA
        click.echo("\n[1/2] Downloading from HuggingFace...")
        downloader = FASTADownloader()
        fasta_path = downloader.download_custom_fasta(filename)
        click.echo(f"✓ Downloaded to: {fasta_path}")
        
        # Step 2: Convert to Parquet
        click.echo(f"\n[2/2] Converting FASTA to Parquet...")
        click.echo(f"  Source name: {source_name}")
        click.echo(f"  Chunk size: {chunk_size:,} sequences/shard")
        click.echo(f"  Compression: {compression}")
        click.echo(f"  Output: {output}")
        
        converter = FASTAToParquetConverter(
            chunk_rows=chunk_size,
            compression=compression,
            output_dir=Path(output).parent
        )
        
        stats = converter.convert(
            fasta_path=fasta_path,
            source_name=source_name,
            output_subdir=Path(output).name
        )
        
        # Display results
        click.echo("\n" + "=" * 60)
        click.echo("Ingestion Complete!")
        click.echo("=" * 60)
        click.echo(f"  Total sequences: {stats['total_sequences']:,}")
        click.echo(f"  Total bases: {stats['total_bases']:,}")
        click.echo(f"  Parquet shards: {stats['total_shards']}")
        click.echo(f"  Output path: {stats['output_path']}")
        click.echo("=" * 60)
        
    except Exception as e:
        click.echo(f"\n✗ Ingestion failed: {e}", err=True)
        if ctx.obj.get("DEBUG"):
            import traceback
            click.echo("\n" + traceback.format_exc(), err=True)
        sys.exit(1)


@ingest.command("local")
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True),
    help="Path to local FASTA file (gzipped or plain)"
)
@click.option(
    "--output",
    type=click.Path(),
    required=True,
    help="Output directory for Parquet files"
)
@click.option(
    "--source-name",
    default="local",
    help="Source identifier for sequences"
)
@click.option(
    "--chunk-size",
    type=int,
    default=50000,
    help="Sequences per Parquet shard"
)
@click.option(
    "--compression",
    type=click.Choice(["snappy", "gzip", "zstd", "none"]),
    default="snappy",
    help="Compression codec"
)
@click.option(
    "--max-sequences",
    type=int,
    default=None,
    help="Maximum sequences to process (for testing)"
)
@click.option(
    "--append",
    is_flag=True,
    help="Append to existing shards instead of overwriting"
)
@click.pass_context
def ingest_local(ctx, input_path, output, source_name, chunk_size, compression, max_sequences, append):
    """
    Ingest local FASTA file.
    
    Converts a local FASTA file (gzipped or plain) to Parquet shards
    for Spark processing. Useful for custom datasets not on HuggingFace.
    
    \b
    Examples:
        opengenome ingest local \\
            --input data/raw/bacteria.fasta.gz \\
            --output /data/parquet/bacteria \\
            --source-name bacteria \\
            --max-sequences 1000
        
        # Append multiple files to same directory
        opengenome ingest local \\
            --input file1.fasta \\
            --output /data/parquet/combined \\
            --source-name combined
        opengenome ingest local \\
            --input file2.fasta \\
            --output /data/parquet/combined \\
            --source-name combined \\
            --append
    """
    from opengenome.ingestion import FASTAToParquetConverter
    
    try:
        input_file = Path(input_path)
        
        click.echo("=" * 60)
        click.echo(f"OpenGenome2 Data Ingestion: Local File")
        click.echo("=" * 60)
        click.echo(f"  Input: {input_file}")
        click.echo(f"  Source: {source_name}")
        
        # Validate file exists and is readable
        if not input_file.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        if not input_file.is_file():
            raise ValueError(f"Input path is not a file: {input_file}")
        
        # Validate it's a FASTA file (basic check)
        valid_extensions = ['.fasta', '.fa', '.fna', '.ffn', '.faa', '.frn', '.gz']
        if not any(str(input_file).endswith(ext) for ext in valid_extensions):
            click.echo(f"\n⚠️  Warning: File extension not recognized as FASTA", err=True)
        
        click.echo(f"  Output: {output}")
        if max_sequences:
            click.echo(f"  Max sequences: {max_sequences:,} (testing mode)")
        if append:
            click.echo(f"  Mode: APPEND (will continue from existing shards)")
        
        file_size = input_file.stat().st_size
        click.echo(f"  File size: {file_size:,} bytes ({file_size / (1024**2):.2f} MB)")
        
        # Create converter
        converter = FASTAToParquetConverter(
            chunk_rows=chunk_size,
            compression=compression
        )
        
        # Convert to Parquet
        stats = converter.convert(
            fasta_path=input_file,
            source_name=source_name,
            output_subdir=Path(output).name,
            max_sequences=max_sequences,
            append=append
        )
        
        # Display results
        click.echo("\n" + "=" * 60)
        click.echo("Ingestion Complete!")
        click.echo("=" * 60)
        click.echo(f"  Total sequences: {stats['total_sequences']:,}")
        click.echo(f"  Total bases: {stats['total_bases']:,}")
        click.echo(f"  Avg sequence length: {stats['total_bases'] // stats['total_sequences']:,}")
        click.echo(f"  Parquet shards: {stats['total_shards']}")
        click.echo(f"  Output path: {stats['output_path']}")
        click.echo("=" * 60)
        
        # Usage tip
        click.echo(f"\n💡 To analyze:")
        click.echo(f"   opengenome analyze kmer --input {stats['output_path']}")
        click.echo(f"   opengenome analyze codon --input {stats['output_path']}")
        
    except FileNotFoundError as e:
        click.echo(f"\n✗ File not found: {e}", err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(f"\n✗ Invalid input: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"\n✗ Ingestion failed: {e}", err=True)
        if ctx.obj.get("DEBUG"):
            import traceback
            click.echo("\n" + traceback.format_exc(), err=True)
        sys.exit(1)


@cli.group()
def analyze():
    """Analysis commands (k-mer, codon, statistics)."""
    pass


@analyze.command("kmer")
@click.option(
    "--input",
    type=click.Path(exists=False),
    default="/data/parquet/organelle/*.parquet",
    help="Input Parquet file pattern"
)
@click.option(
    "--output",
    type=click.Path(),
    default="/results/kmer",
    help="Output directory for results"
)
@click.option(
    "--k",
    type=int,
    default=6,
    help="K-mer length (typically 6-8)"
)
@click.option(
    "--skip-n/--no-skip-n",
    default=True,
    help="Skip k-mers containing N (ambiguous base)"
)
@click.option(
    "--min-count",
    type=int,
    default=1,
    help="Minimum frequency threshold"
)
@click.option(
    "--top",
    type=int,
    default=20,
    help="Number of top k-mers to display"
)
@click.pass_context
def analyze_kmer(ctx, input, output, k, skip_n, min_count, top):
    """
    Perform k-mer frequency analysis.
    
    Uses MapReduce to count k-mer occurrences across all sequences.
    Results are saved as Parquet and top k-mers are displayed.
    
    \b
    Example:
        opengenome analyze kmer --k 6
        opengenome analyze kmer --k 8 --min-count 10 --top 50
    """
    from opengenome.analysis import KmerAnalyzer
    from opengenome.spark.session import get_spark_session, stop_spark_session
    
    try:
        click.echo("=" * 60)
        click.echo(f"K-mer Frequency Analysis (k={k})")
        click.echo("=" * 60)
        
        # Start Spark session
        click.echo("\n[1/4] Initializing Spark session...")
        spark = get_spark_session(app_name=f"KmerAnalysis-k{k}")
        click.echo(f"✓ Spark {spark.version} ready")
        
        # Initialize analyzer
        click.echo(f"\n[2/4] Loading sequences from {input}")
        analyzer = KmerAnalyzer(spark, k=k)
        
        # Run analysis
        click.echo(f"\n[3/4] Running MapReduce k-mer analysis...")
        click.echo(f"  Parameters:")
        click.echo(f"    k-mer length: {k}")
        click.echo(f"    Skip N: {skip_n}")
        click.echo(f"    Min count: {min_count}")
        
        kmer_df = analyzer.analyze(
            input_path=input,
            output_path=output,
            skip_n=skip_n,
            min_count=min_count
        )
        
        # Display results
        click.echo(f"\n[4/4] Results:")
        click.echo("=" * 60)
        
        # Statistics
        stats = analyzer.get_statistics(kmer_df)
        click.echo(f"\nStatistics:")
        click.echo(f"  Unique k-mers: {stats['total_kmers']:,}")
        click.echo(f"  Total occurrences: {stats['total_count']:,}")
        click.echo(f"  Mean frequency: {stats['mean_count']:.2f}")
        click.echo(f"  Max frequency: {stats['max_count']:,}")
        click.echo(f"  Min frequency: {stats['min_count']:,}")
        
        # Top k-mers
        click.echo(f"\nTop {top} k-mers:")
        click.echo(f"{'K-mer':<{k+2}} {'Count':>12}")
        click.echo("-" * (k + 16))
        
        top_kmers = analyzer.get_top_kmers(kmer_df, n=top)
        for kmer, count in top_kmers:
            click.echo(f"{kmer:<{k+2}} {count:>12,}")
        
        click.echo("\n" + "=" * 60)
        click.echo(f"Results saved to: {output}")
        click.echo("=" * 60)
        
        # Cleanup
        stop_spark_session()
        
    except Exception as e:
        click.echo(f"\n✗ K-mer analysis failed: {e}", err=True)
        if ctx.obj.get("DEBUG"):
            import traceback
            click.echo("\n" + traceback.format_exc(), err=True)
        sys.exit(1)


@analyze.command("codon")
@click.pass_context
@click.option(
    "--input",
    required=True,
    help="Input Parquet path (e.g., /data/parquet/organelle/*.parquet)"
)
@click.option(
    "--output",
    default="/results/codon",
    help="Output directory for results (default: /results/codon)"
)
@click.option(
    "--frame",
    type=click.IntRange(0, 2),
    default=0,
    help="Reading frame (0, 1, or 2, default: 0)"
)
@click.option(
    "--skip-n",
    is_flag=True,
    default=True,
    help="Skip codons containing N (default: True)"
)
@click.option(
    "--skip-stops",
    is_flag=True,
    default=False,
    help="Exclude stop codons from analysis"
)
@click.option(
    "--min-count",
    type=int,
    default=1,
    help="Minimum codon count to include (default: 1)"
)
@click.option(
    "--rscu",
    is_flag=True,
    default=False,
    help="Calculate RSCU (Relative Synonymous Codon Usage)"
)
@click.option(
    "--top",
    type=int,
    default=30,
    help="Number of top codons to display (default: 30)"
)
def analyze_codon(ctx, input, output, frame, skip_n, skip_stops, min_count, rscu, top):
    """
    Analyze codon usage patterns in sequences.
    
    Performs MapReduce codon counting and optional RSCU calculation.
    
    Example:
        ./opengenome analyze codon --input /data/parquet/organelle/*.parquet
        ./opengenome analyze codon --frame 0 --skip-stops --rscu --top 20
    """
    from opengenome.spark.session import get_spark_session
    from opengenome.analysis import CodonAnalyzer
    
    try:
        # Display header
        click.echo("=" * 60)
        click.echo(" " * 20 + f"Codon Usage Analysis (frame={frame})")
        click.echo("=" * 60)
        click.echo()
        
        # Initialize Spark
        click.echo("[1/4] Initializing Spark session...")
        spark = get_spark_session(
            app_name=f"CodonAnalysis-frame{frame}",
            master=None  # Uses SPARK_MASTER from env
        )
        
        # Initialize analyzer
        click.echo(f"[2/4] Loading sequences from {input}")
        analyzer = CodonAnalyzer(spark, frame=frame)
        
        # Run analysis
        click.echo(f"\n[3/4] Running MapReduce codon analysis...")
        click.echo("  Parameters:")
        click.echo(f"    Reading frame: {frame}")
        click.echo(f"    Skip N: {skip_n}")
        click.echo(f"    Skip stops: {skip_stops}")
        click.echo(f"    Min count: {min_count}")
        
        codon_df = analyzer.analyze(
            input_path=input,
            output_path=output,
            skip_n=skip_n,
            skip_stops=skip_stops,
            min_count=min_count
        )
        
        # Get statistics
        stats = analyzer.get_statistics(codon_df)
        
        # Calculate RSCU if requested
        if rscu:
            click.echo("\n  Calculating RSCU...")
            rscu_df = analyzer.calculate_rscu(codon_df)
            rscu_output = output + "_rscu"
            rscu_df.write.mode("overwrite").parquet(rscu_output)
            click.echo(f"  RSCU results saved to: {rscu_output}")
        
        # Display results
        click.echo("\n[4/4] Results:")
        click.echo("=" * 60)
        click.echo("\nStatistics:")
        click.echo(f"  Unique codons: {stats['unique_codons']:,}")
        click.echo(f"  Total occurrences: {stats['total_count']:,}")
        click.echo(f"  Mean frequency: {stats['mean_freq']:.6f}")
        click.echo(f"  Max frequency: {stats['max_freq']:.6f}")
        click.echo(f"  Min frequency: {stats['min_freq']:.6f}")
        
        # Display top codons
        click.echo(f"\nTop {top} codons:")
        click.echo(f"{'Codon':<8}{'Count':>15}{'AA':>6}{'Frequency':>12}")
        click.echo("-" * 41)
        
        top_codons = analyzer.get_top_codons(codon_df, n=top)
        for codon, count, aa in top_codons:
            freq = count / stats['total_count']
            click.echo(f"{codon:<8}{count:>15,}{aa:>6}{freq:>12.4%}")
        
        # Display RSCU info if calculated
        if rscu:
            preferred = analyzer.get_preferred_codons(rscu_df, threshold=1.0)
            click.echo(f"\nPreferred codons (RSCU > 1.0): {len(preferred)}")
            click.echo(f"{'Codon':<8}{'RSCU':>10}{'AA':>6}")
            click.echo("-" * 24)
            for codon, rscu_val, aa in preferred[:20]:
                click.echo(f"{codon:<8}{rscu_val:>10.3f}{aa:>6}")
        
        click.echo("\n" + "=" * 60)
        click.echo(f"Results saved to: {output}")
        click.echo("=" * 60)
        
    except Exception as e:
        click.echo(f"\n✗ Codon analysis failed: {e}", err=True)
        if ctx.obj.get("DEBUG"):
            import traceback
            click.echo("\n" + traceback.format_exc(), err=True)
        sys.exit(1)


@analyze.command("search")
@click.option(
    "--input",
    type=click.Path(exists=False),
    default="/data/parquet/organelle/*.parquet",
    help="Input Parquet file pattern"
)
@click.option(
    "--output",
    type=click.Path(),
    default="/results/search",
    help="Output directory for results"
)
@click.option(
    "--pattern",
    type=str,
    required=True,
    help="DNA sequence pattern to search for (e.g., ACGACGACGGGGACG)"
)
@click.option(
    "--case-sensitive",
    is_flag=True,
    help="Perform case-sensitive search"
)
@click.option(
    "--reverse-complement",
    is_flag=True,
    help="Also search for reverse complement of the pattern"
)
@click.option(
    "--max-results",
    type=int,
    default=None,
    help="Maximum number of results to return (default: all)"
)
@click.pass_context
def search_sequences(ctx, input, output, pattern, case_sensitive, reverse_complement, max_results):
    """Search for sequences containing a specific pattern."""
    from opengenome.spark.session import get_spark_session, stop_spark_session
    from opengenome.analysis.sequence_search import SequenceSearcher
    from datetime import datetime
    
    try:
        click.echo()
        click.echo(" " * 20 + "Sequence Pattern Search")
        click.echo("=" * 60)
        click.echo()
        
        # Initialize Spark
        click.echo("[1/3] Initializing Spark session...")
        spark = get_spark_session(
            app_name="SequenceSearch",
            master=None  # Uses SPARK_MASTER from env
        )
        
        # Initialize searcher
        click.echo(f"[2/3] Searching for pattern in {input}")
        searcher = SequenceSearcher(spark)
        
        # Display search parameters
        click.echo(f"\n  Parameters:")
        click.echo(f"    Pattern: {pattern}")
        click.echo(f"    Pattern length: {len(pattern)}")
        click.echo(f"    Case sensitive: {case_sensitive}")
        click.echo(f"    Reverse complement: {reverse_complement}")
        if max_results:
            click.echo(f"    Max results: {max_results:,}")
        
        # Create timestamped output path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{output}/search_{timestamp}.parquet"
        
        # Run search
        click.echo(f"\n[3/3] Running distributed pattern search...")
        results = searcher.search(
            input_path=input,
            pattern=pattern,
            output_path=output_file,
            case_sensitive=case_sensitive,
            max_results=max_results,
            search_reverse_complement=reverse_complement
        )
        
        # Display results
        click.echo("\nResults:")
        click.echo("=" * 60)
        click.echo(f"  Total sequences searched: {results['total_sequences_searched']:,}")
        click.echo(f"  Matching sequences: {results['matching_sequences']:,}")
        click.echo(f"  Match percentage: {results['match_percentage']:.2f}%")
        
        if results['sample_matches']:
            click.echo(f"\n  Top matches:")
            click.echo(f"  {'Sequence ID':<20}{'Matches':>10}{'Coverage':>12}{'Length':>12}")
            click.echo("  " + "-" * 54)
            
            for match in results['sample_matches'][:10]:
                click.echo(
                    f"  {match['sequence_id']:<20}"
                    f"{match['match_count']:>10,}"
                    f"{match['pattern_coverage']:>11.2f}%"
                    f"{match['sequence_length']:>12,}"
                )
        
        click.echo("\n" + "=" * 60)
        click.echo(f"Results saved to: {output_file}")
        click.echo("=" * 60)
        
    except Exception as e:
        click.echo(f"\n✗ Sequence search failed: {e}", err=True)
        if ctx.obj.get("DEBUG"):
            import traceback
            click.echo("\n" + traceback.format_exc(), err=True)
        sys.exit(1)


@cli.group()
def visualize():
    """Visualization commands."""
    pass


@cli.group()
def visualize():
    """
    Create visualizations from analysis results.
    
    \b
    Examples:
      # K-mer distribution
      opengenome visualize kmer --input /results/kmer --output /results/figs/kmers.png
      
      # Codon usage
      opengenome visualize codon --input /results/codon --output /results/figs/codons.png
      
      # GC content
      opengenome visualize gc --input /data/parquet/organelle --output /results/figs/gc.png
    """
    pass


@visualize.command()
@click.option("--input", required=True, help="Input Parquet path (k-mer results)")
@click.option("--output", required=True, help="Output PNG file path")
@click.option("--top", default=20, help="Number of top k-mers to display")
@click.option("--title", default=None, help="Custom chart title")
@click.option("--color", default="skyblue", help="Bar color")
@click.option("--dpi", default=200, help="Output DPI")
@click.option("--width", default=12, help="Figure width in inches")
@click.option("--height", default=7, help="Figure height in inches")
@click.pass_context
def kmer(ctx, input, output, top, title, color, dpi, width, height):
    """Create k-mer frequency distribution bar chart."""
    from opengenome.spark.session import get_spark_session, stop_spark_session
    from opengenome.visualization.plots import plot_kmer_distribution
    
    debug = ctx.obj.get("DEBUG", False)
    
    try:
        click.echo("[1/3] Initializing Spark session...")
        spark = get_spark_session(app_name="VisualizeKmer")
        
        click.echo(f"[2/3] Loading k-mer data from {input}...")
        click.echo(f"[3/3] Creating visualization...")
        
        output_path = plot_kmer_distribution(
            input_path=input,
            output_path=output,
            top_n=top,
            figsize=(width, height),
            dpi=dpi,
            title=title,
            color=color
        )
        
        click.echo("=" * 60)
        click.echo(f"✓ Visualization saved to: {output_path}")
        click.echo("=" * 60)
        
        stop_spark_session()
        
    except Exception as e:
        click.echo(f"Error: K-mer visualization failed: {e}", err=True)
        if debug:
            import traceback
            traceback.print_exc()
        stop_spark_session()
        sys.exit(1)


@visualize.command()
@click.option("--input", required=True, help="Input Parquet path (codon results)")
@click.option("--output", required=True, help="Output PNG file path")
@click.option("--top", default=30, help="Number of top codons to display")
@click.option("--title", default=None, help="Custom chart title")
@click.option("--color", default="lightcoral", help="Bar color")
@click.option("--show-aa", is_flag=True, default=True, help="Show amino acid labels")
@click.option("--dpi", default=200, help="Output DPI")
@click.option("--width", default=14, help="Figure width in inches")
@click.option("--height", default=7, help="Figure height in inches")
@click.pass_context
def codon(ctx, input, output, top, title, color, show_aa, dpi, width, height):
    """Create codon usage frequency bar chart."""
    from opengenome.spark.session import get_spark_session, stop_spark_session
    from opengenome.visualization.plots import plot_codon_usage
    
    debug = ctx.obj.get("DEBUG", False)
    
    try:
        click.echo("[1/3] Initializing Spark session...")
        spark = get_spark_session(app_name="VisualizeCodon")
        
        click.echo(f"[2/3] Loading codon data from {input}...")
        click.echo(f"[3/3] Creating visualization...")
        
        output_path = plot_codon_usage(
            input_path=input,
            output_path=output,
            top_n=top,
            figsize=(width, height),
            dpi=dpi,
            title=title,
            color=color,
            show_amino_acids=show_aa
        )
        
        click.echo("=" * 60)
        click.echo(f"✓ Visualization saved to: {output_path}")
        click.echo("=" * 60)
        
        stop_spark_session()
        
    except Exception as e:
        click.echo(f"Error: Codon visualization failed: {e}", err=True)
        if debug:
            import traceback
            traceback.print_exc()
        stop_spark_session()
        sys.exit(1)


@visualize.command()
@click.option("--input", required=True, help="Input Parquet path (sequence data)")
@click.option("--output", required=True, help="Output PNG file path")
@click.option("--bins", default=50, help="Number of histogram bins")
@click.option("--title", default=None, help="Custom chart title")
@click.option("--color", default="mediumseagreen", help="Histogram color")
@click.option("--dpi", default=200, help="Output DPI")
@click.option("--width", default=12, help="Figure width in inches")
@click.option("--height", default=7, help="Figure height in inches")
@click.pass_context
def gc(ctx, input, output, bins, title, color, dpi, width, height):
    """Create GC content distribution histogram."""
    from opengenome.spark.session import get_spark_session, stop_spark_session
    from opengenome.visualization.plots import plot_gc_content
    
    debug = ctx.obj.get("DEBUG", False)
    
    try:
        click.echo("[1/3] Initializing Spark session...")
        spark = get_spark_session(app_name="VisualizeGC")
        
        click.echo(f"[2/3] Loading sequence data from {input}...")
        click.echo(f"[3/3] Creating visualization...")
        
        output_path = plot_gc_content(
            input_path=input,
            output_path=output,
            bins=bins,
            figsize=(width, height),
            dpi=dpi,
            title=title,
            color=color
        )
        
        click.echo("=" * 60)
        click.echo(f"✓ Visualization saved to: {output_path}")
        click.echo("=" * 60)
        
        stop_spark_session()
        
    except Exception as e:
        click.echo(f"Error: GC content visualization failed: {e}", err=True)
        if debug:
            import traceback
            traceback.print_exc()
        stop_spark_session()
        sys.exit(1)


@visualize.command()
@click.option("--input", required=True, help="Input Parquet path (sequence data)")
@click.option("--output", required=True, help="Output PNG file path")
@click.option("--bins", default=50, help="Number of histogram bins")
@click.option("--title", default=None, help="Custom chart title")
@click.option("--color", default="mediumpurple", help="Histogram color")
@click.option("--dpi", default=200, help="Output DPI")
@click.option("--width", default=12, help="Figure width in inches")
@click.option("--height", default=7, help="Figure height in inches")
@click.pass_context
def length(ctx, input, output, bins, title, color, dpi, width, height):
    """Create sequence length distribution histogram."""
    from opengenome.spark.session import get_spark_session, stop_spark_session
    from opengenome.visualization.plots import plot_sequence_length_distribution
    
    debug = ctx.obj.get("DEBUG", False)
    
    try:
        click.echo("[1/3] Initializing Spark session...")
        spark = get_spark_session(app_name="VisualizeLength")
        
        click.echo(f"[2/3] Loading sequence data from {input}...")
        click.echo(f"[3/3] Creating visualization...")
        
        output_path = plot_sequence_length_distribution(
            input_path=input,
            output_path=output,
            bins=bins,
            figsize=(width, height),
            dpi=dpi,
            title=title,
            color=color
        )
        
        click.echo("=" * 60)
        click.echo(f"✓ Visualization saved to: {output_path}")
        click.echo("=" * 60)
        
        stop_spark_session()
        
    except Exception as e:
        click.echo(f"Error: Length distribution visualization failed: {e}", err=True)
        if debug:
            import traceback
            traceback.print_exc()
        stop_spark_session()
        sys.exit(1)


@cli.command()
@click.option("--spark-ui", is_flag=True, help="Show Spark UI URL")
def info(spark_ui):
    """Show cluster information and status."""
    from opengenome.spark.session import get_spark_session, is_spark_session_active, stop_spark_session
    from py4j.protocol import Py4JNetworkError
    
    try:
        spark = get_spark_session(app_name="ClusterInfo")
        
        click.echo("Cluster Status:")
        click.echo("=" * 50)
        click.echo(f"  Spark Version: {spark.version}")
        click.echo(f"  Master URL: {spark.sparkContext.master}")
        click.echo(f"  App Name: {spark.sparkContext.appName}")
        click.echo(f"  App ID: {spark.sparkContext.applicationId}")
        click.echo(f"  Default Parallelism: {spark.sparkContext.defaultParallelism}")
        click.echo(f"  Active: {is_spark_session_active()}")
        
        if spark_ui:
            ui_url = spark.sparkContext.uiWebUrl
            if ui_url:
                click.echo(f"  Spark UI: {ui_url}")
        
        click.echo("=" * 50)
        
        stop_spark_session()
    
    except Py4JNetworkError:
        click.echo("Error: Cannot connect to Spark master", err=True)
        click.echo("Ensure the cluster is running: make up", err=True)
        sys.exit(1)
    except ConnectionRefusedError:
        click.echo("Error: Connection refused by Spark master", err=True)
        click.echo("Check if spark-master container is running: docker ps", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: Unexpected failure connecting to Spark", err=True)
        click.echo(f"Details: {type(e).__name__}: {e}", err=True)
        sys.exit(1)


@cli.group()
def search():
    """
    Sequence similarity search commands.
    
    Build an index and search for similar sequences using k-mer-based
    TF-IDF vectorization and cosine similarity.
    """
    pass


@search.command("build-index")
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True),
    help="Input sequence data (Parquet)",
)
@click.option(
    "--k",
    default=6,
    type=int,
    help="K-mer length (default: 6)",
    show_default=True,
)
@click.option(
    "--skip-n",
    is_flag=True,
    default=True,
    help="Skip k-mers containing 'N' or non-ATGC bases (default: True)",
    show_default=True,
)
@click.option(
    "--max-sequences",
    type=int,
    help="Limit number of sequences to index (for testing)",
)
def search_build_index(input_path, k, skip_n, max_sequences):
    """
    Build search index from sequence data.
    
    This extracts k-mers from all sequences and computes TF-IDF weights
    and vector norms for fast similarity search.
    
    Example:
        opengenome search build-index --input /data/sequences.parquet --k 6
    """
    from opengenome.search import SequenceSearcher
    from opengenome.spark.session import get_spark_session
    from py4j.protocol import Py4JNetworkError
    
    try:
        click.echo("=" * 60)
        click.echo("Building Sequence Search Index")
        click.echo("=" * 60)
        
        # Progress indicator
        click.echo("\n[1/4] Connecting to Spark cluster...")
        spark = get_spark_session(
            app_name="opengenome-search-build",
            master="spark://spark-master:7077"
        )
        
        click.echo(f"[2/4] Initializing searcher (k={k})...")
        searcher = SequenceSearcher(spark, k=k)
        
        click.echo("[3/4] Building index (this may take several minutes)...")
        click.echo(f"  Input: {input_path}")
        click.echo(f"  K-mer size: {k}")
        click.echo(f"  Skip non-ATGC: {skip_n}")
        if max_sequences:
            click.echo(f"  Max sequences: {max_sequences}")
        
        searcher.build_index(
            input_path=input_path,
            skip_n=skip_n,
            max_sequences=max_sequences
        )
        
        click.echo("[4/4] Retrieving statistics...")
        stats = searcher.get_statistics()
        
        if stats:
            click.echo("\n" + "=" * 60)
            click.echo("Index Statistics:")
            click.echo("=" * 60)
            click.echo(f"  Sequences indexed: {stats['num_sequences']:,}")
            click.echo(f"  Unique k-mers: {stats['num_unique_kmers']:,}")
            click.echo(f"  K-mer size: {stats['k']}")
        
        click.echo("\n✓ Index built successfully!")
        click.echo("\nUse 'opengenome search query' to search for similar sequences.")
        
        stop_spark_session()
    
    except Py4JNetworkError:
        click.echo("Error: Cannot connect to Spark master", err=True)
        click.echo("Ensure the cluster is running: make up", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: Failed to build index", err=True)
        click.echo(f"Details: {type(e).__name__}: {e}", err=True)
        logger.error("Index building failed", exc_info=True)
        sys.exit(1)


@search.command("query")
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True),
    help="Input sequence data (Parquet) - must be indexed first",
)
@click.option(
    "--query",
    "query_sequence",
    required=True,
    type=str,
    help="Query sequence (DNA string)",
)
@click.option(
    "--k",
    default=6,
    type=int,
    help="K-mer length (must match index)",
    show_default=True,
)
@click.option(
    "--top",
    "top_n",
    default=20,
    type=int,
    help="Number of top results to return",
    show_default=True,
)
@click.option(
    "--use-idf",
    is_flag=True,
    default=True,
    help="Use IDF weighting (TF-IDF vs TF only)",
    show_default=True,
)
@click.option(
    "--skip-n",
    is_flag=True,
    default=True,
    help="Skip query k-mers containing 'N' or non-ATGC",
    show_default=True,
)
@click.option(
    "--show-details",
    is_flag=True,
    help="Show detailed sequence information for results",
)
def search_query(input_path, query_sequence, k, top_n, use_idf, skip_n, show_details):
    """
    Search for sequences similar to query.
    
    Uses k-mer-based TF-IDF vectorization and cosine similarity to find
    the most similar sequences to the query.
    
    Example:
        opengenome search query --input /data/sequences.parquet \\
            --query "ATGCGATCGATCG..." --top 10
    """
    from opengenome.search import SequenceSearcher
    from opengenome.spark.session import get_spark_session
    from py4j.protocol import Py4JNetworkError
    
    try:
        click.echo("=" * 60)
        click.echo("Sequence Similarity Search")
        click.echo("=" * 60)
        
        # Progress indicator
        click.echo("\n[1/5] Connecting to Spark cluster...")
        spark = get_spark_session(
            app_name="opengenome-search-query",
            master="spark://spark-master:7077"
        )
        
        click.echo(f"[2/5] Initializing searcher (k={k})...")
        searcher = SequenceSearcher(spark, k=k)
        
        click.echo("[3/5] Building index...")
        click.echo(f"  Input: {input_path}")
        searcher.build_index(input_path=input_path, skip_n=skip_n)
        
        click.echo(f"[4/5] Processing query...")
        click.echo(f"  Query length: {len(query_sequence)} bases")
        click.echo(f"  K-mer size: {k}")
        click.echo(f"  Use IDF: {use_idf}")
        click.echo(f"  Top N: {top_n}")
        
        results = searcher.search(
            query_sequence=query_sequence,
            top_n=top_n,
            use_idf=use_idf,
            skip_n=skip_n
        )
        
        click.echo("[5/5] Retrieving results...")
        results_list = results.collect()
        
        click.echo("\n" + "=" * 60)
        click.echo(f"Top {len(results_list)} Similar Sequences:")
        click.echo("=" * 60)
        
        if not results_list:
            click.echo("No results found.")
        else:
            # Display results
            for row in results_list:
                click.echo(f"\n#{row['rank']}: {row['seq_id']}")
                click.echo(f"  Similarity: {row['similarity']:.4f}")
                
                if show_details:
                    # Load sequence details
                    seq_df = spark.read.parquet(input_path)
                    seq_info = seq_df.filter(seq_df.seq_id == row['seq_id']).first()
                    if seq_info:
                        click.echo(f"  Description: {seq_info['description'][:80]}...")
                        click.echo(f"  Length: {seq_info['length']:,} bases")
                        click.echo(f"  Source: {seq_info['source']}")
        
        click.echo("\n✓ Search complete!")
        
        stop_spark_session()
    
    except Py4JNetworkError:
        click.echo("Error: Cannot connect to Spark master", err=True)
        click.echo("Ensure the cluster is running: make up", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: Search failed", err=True)
        click.echo(f"Details: {type(e).__name__}: {e}", err=True)
        logger.error("Search query failed", exc_info=True)
        sys.exit(1)


def main():
    """Main entry point with cleanup."""
    try:
        cli(obj={})
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Ensure Spark session is stopped on exit
        try:
            stop_spark_session()
        except:
            pass


if __name__ == "__main__":
    main()
