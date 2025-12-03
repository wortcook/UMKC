"""
OpenGenome2 - Distributed Genomic Sequence Analysis

A scalable, production-ready platform for processing large genomic datasets
using Apache Spark.
"""

__version__ = "0.1.0"
__author__ = "OpenGenome2 Team"

from opengenome.spark.session import get_spark_session, stop_spark_session

__all__ = [
    "get_spark_session",
    "stop_spark_session",
]
