"""
Spark session management for OpenGenome2.

Provides centralized Spark session creation, configuration, and lifecycle management.
"""

import os
import logging
from typing import Optional
from pyspark.sql import SparkSession
from pyspark import SparkConf
from py4j.protocol import Py4JNetworkError

from opengenome.utils.config import validate_memory_string

logger = logging.getLogger(__name__)

# Global Spark session instance
_spark_session: Optional[SparkSession] = None


def get_spark_session(
    app_name: str = "OpenGenome2",
    master: Optional[str] = None,
    config: Optional[dict] = None,
) -> SparkSession:
    """
    Get or create a Spark session with OpenGenome2 configuration.
    
    Args:
        app_name: Name of the Spark application
        master: Spark master URL (defaults to env SPARK_MASTER or spark://spark-master:7077)
        config: Additional Spark configuration as key-value pairs
    
    Returns:
        SparkSession: Configured Spark session
    
    Example:
        >>> spark = get_spark_session(app_name="MyAnalysis")
        >>> df = spark.read.parquet("/data/parquet/sequences.parquet")
    """
    global _spark_session
    
    # Check if existing session is still alive
    if _spark_session is not None:
        try:
            # Try to access the SparkContext to verify it's alive
            if not _spark_session.sparkContext._jsc.sc().isStopped():
                logger.debug(f"Reusing existing Spark session: {_spark_session.sparkContext.appName}")
                return _spark_session
            else:
                logger.info("Existing Spark session is stopped, creating new one")
                _spark_session = None
        except Exception as e:
            logger.warning(f"Existing Spark session is invalid ({e}), creating new one")
            _spark_session = None
    
    # Determine master URL
    if master is None:
        master = os.environ.get("SPARK_MASTER", "spark://spark-master:7077")
    
    logger.info(f"Creating new Spark session: {app_name} on {master}")
    
    # Build Spark configuration
    spark_conf = SparkConf()
    
    # Set defaults from environment variables
    spark_conf.set("spark.app.name", app_name)
    spark_conf.set("spark.master", master)
    
    # Memory configuration with validation
    driver_memory = os.environ.get("SPARK_DRIVER_MEMORY", "3g")
    executor_memory = os.environ.get("SPARK_EXECUTOR_MEMORY", "5g")
    
    if not validate_memory_string(driver_memory):
        logger.warning(f"Invalid driver memory format '{driver_memory}', using default '3g'")
        driver_memory = "3g"
    
    if not validate_memory_string(executor_memory):
        logger.warning(f"Invalid executor memory format '{executor_memory}', using default '5g'")
        executor_memory = "5g"
    
    spark_conf.set("spark.driver.memory", driver_memory)
    spark_conf.set("spark.executor.memory", executor_memory)
    
    # Memory overhead to prevent OOM (conservative for 4GB workers)
    spark_conf.set("spark.executor.memoryOverhead", "256m")
    spark_conf.set("spark.driver.memoryOverhead", "256m")
    
    # Memory fraction for execution/storage (conservative settings)
    spark_conf.set("spark.memory.fraction", "0.6")
    spark_conf.set("spark.memory.storageFraction", "0.3")
    
    # Performance tuning
    if os.environ.get("ENABLE_ADAPTIVE_EXECUTION", "true").lower() == "true":
        spark_conf.set("spark.sql.adaptive.enabled", "true")
        spark_conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
    
    # Executor cores (limit to match worker availability)
    executor_cores = os.environ.get("SPARK_EXECUTOR_CORES", "1")
    spark_conf.set("spark.executor.cores", executor_cores)
    
    # Shuffle partitions (must be integer, not "auto")
    shuffle_partitions = os.environ.get("SPARK_SQL_SHUFFLE_PARTITIONS", "200")
    try:
        # Validate it's a valid integer
        int(shuffle_partitions)
    except ValueError:
        logger.warning(f"Invalid shuffle partitions '{shuffle_partitions}', using default '200'")
        shuffle_partitions = "200"
    
    # Set max partition bytes to create smaller file reading tasks
    # Default is 128MB, reduce to 32MB for better parallelism with many small files
    spark_conf.set("spark.sql.files.maxPartitionBytes", "33554432")  # 32MB
    spark_conf.set("spark.sql.shuffle.partitions", shuffle_partitions)
    
    # Network configuration
    network_timeout = os.environ.get("SPARK_NETWORK_TIMEOUT", "300s")
    spark_conf.set("spark.network.timeout", network_timeout)
    
    # Apply custom configuration
    if config:
        for key, value in config.items():
            spark_conf.set(key, str(value))
            logger.debug(f"Set custom config: {key} = {value}")
    
    # Create Spark session
    builder = SparkSession.builder.config(conf=spark_conf)
    
    _spark_session = builder.getOrCreate()
    
    # Set log level
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    _spark_session.sparkContext.setLogLevel(log_level)
    
    logger.info(f"Spark session created successfully")
    logger.info(f"  - Version: {_spark_session.version}")
    logger.info(f"  - Master: {_spark_session.sparkContext.master}")
    logger.info(f"  - App ID: {_spark_session.sparkContext.applicationId}")
    logger.info(f"[MEMORY CONFIG] Driver: {driver_memory}, Executor: {executor_memory}, Overhead: 256m")
    logger.info(f"[MEMORY CONFIG] Memory fraction: 0.6, Storage fraction: 0.3")
    
    return _spark_session


def stop_spark_session() -> None:
    """
    Stop the global Spark session and release resources.
    
    Example:
        >>> stop_spark_session()
    """
    global _spark_session
    
    if _spark_session is not None:
        logger.info("Stopping Spark session")
        _spark_session.stop()
        _spark_session = None
        logger.info("Spark session stopped")
    else:
        logger.debug("No active Spark session to stop")


def get_spark_context():
    """
    Get the SparkContext from the current session.
    
    Returns:
        SparkContext: The active Spark context
    
    Raises:
        RuntimeError: If no Spark session exists
    """
    if _spark_session is None:
        raise RuntimeError("No active Spark session. Call get_spark_session() first.")
    return _spark_session.sparkContext


def is_spark_session_active() -> bool:
    """
    Check if a Spark session is currently active.
    
    Returns:
        bool: True if session exists and is active
    """
    return _spark_session is not None and not _spark_session.sparkContext._jsc.sc().isStopped()
