"""
FASTA file downloader from HuggingFace Hub.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from huggingface_hub import hf_hub_download


logger = logging.getLogger(__name__)


class FASTADownloader:
    """Downloads FASTA files from HuggingFace datasets."""
    
    def __init__(
        self,
        repo_id: str = "arcinstitute/opengenome2",
        cache_dir: Optional[Path] = None
    ):
        """
        Initialize FASTA downloader.
        
        Args:
            repo_id: HuggingFace dataset repository ID
            cache_dir: Local cache directory for downloaded files
        """
        self.repo_id = repo_id
        self.cache_dir = cache_dir or Path("/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized downloader for {repo_id}")
        logger.info(f"Cache directory: {self.cache_dir}")
    
    def download_organelle_sequences(self) -> Path:
        """
        Download organelle sequences FASTA file.
        
        Returns:
            Path: Local path to downloaded gzipped FASTA file
            
        Raises:
            RuntimeError: If download fails
        """
        filename = "fasta/organelles/organelle_sequences.fasta.gz"
        
        logger.info(f"Downloading {filename} from {self.repo_id}")
        
        try:
            local_path = hf_hub_download(
                repo_id=self.repo_id,
                filename=filename,
                repo_type="dataset",
                cache_dir=str(self.cache_dir)
            )
            
            path = Path(local_path)
            if not path.exists():
                raise RuntimeError(f"Downloaded file not found: {path}")
            
            file_size = path.stat().st_size
            logger.info(f"Downloaded {filename} ({file_size:,} bytes) to {path}")
            
            return path
            
        except Exception as e:
            logger.error(f"Failed to download {filename}: {e}")
            raise RuntimeError(f"Download failed: {e}") from e
    
    def download_custom_fasta(self, filename: str) -> Path:
        """
        Download a custom FASTA file from the dataset.
        
        Args:
            filename: Relative path within the dataset repository
            
        Returns:
            Path: Local path to downloaded file
            
        Raises:
            RuntimeError: If download fails
        """
        logger.info(f"Downloading {filename} from {self.repo_id}")
        
        try:
            local_path = hf_hub_download(
                repo_id=self.repo_id,
                filename=filename,
                repo_type="dataset",
                cache_dir=str(self.cache_dir)
            )
            
            path = Path(local_path)
            if not path.exists():
                raise RuntimeError(f"Downloaded file not found: {path}")
            
            file_size = path.stat().st_size
            logger.info(f"Downloaded {filename} ({file_size:,} bytes) to {path}")
            
            return path
            
        except Exception as e:
            logger.error(f"Failed to download {filename}: {e}")
            raise RuntimeError(f"Download failed: {e}") from e
