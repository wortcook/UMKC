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


@cli.group()
def visualize():
    """Visualization commands."""
    pass


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
