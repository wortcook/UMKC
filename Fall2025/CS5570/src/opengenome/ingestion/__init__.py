"""
Data ingestion module for loading genomic data from various sources.
"""

from opengenome.ingestion.downloader import FASTADownloader
from opengenome.ingestion.converter import FASTAToParquetConverter

__all__ = ["FASTADownloader", "FASTAToParquetConverter"]
