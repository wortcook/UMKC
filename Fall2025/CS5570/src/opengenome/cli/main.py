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


@cli.group()
def analyze():
    """Analysis commands (k-mer, codon, statistics)."""
    pass


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
