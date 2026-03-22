"""
Seed Processor — Stage 1 of the MiroFish Pipeline

Handles: file upload → text extraction → preprocessing → chunking
This is the entry point of the kernel pipeline.
"""

from typing import List, Dict, Any, Optional
from ..tools.text_processor import TextProcessor, FileParser
from ..tools.logger import get_logger

logger = get_logger("mirofish.pipeline.seed")


class SeedProcessor:
    """
    Processes seed material (documents, text) into chunks 
    ready for ontology design and graph construction.
    """
    
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def process_files(
        self,
        file_paths: List[str],
        requirement: str = "",
    ) -> Dict[str, Any]:
        """
        Process seed files into structured output.
        
        Args:
            file_paths: Paths to seed documents (PDF, MD, TXT)
            requirement: User's prediction/simulation requirement
            
        Returns:
            {
                "raw_text": str,          # Full extracted text
                "chunks": List[str],       # Text chunks for graph building
                "stats": Dict,             # Text statistics
                "requirement": str,        # Passed through
            }
        """
        logger.info(f"Processing {len(file_paths)} seed file(s)...")
        
        # Extract text from all files
        raw_text = FileParser.extract_from_multiple(file_paths)
        
        return self._process_text(raw_text, requirement)
    
    def process_text(
        self,
        text: str,
        requirement: str = "",
    ) -> Dict[str, Any]:
        """
        Process raw text input (no files).
        
        Args:
            text: Raw seed text
            requirement: User's requirement
            
        Returns:
            Same structure as process_files
        """
        logger.info(f"Processing text input ({len(text)} chars)...")
        return self._process_text(text, requirement)
    
    def _process_text(self, raw_text: str, requirement: str) -> Dict[str, Any]:
        """Internal text processing pipeline."""
        # Preprocess
        cleaned = TextProcessor.preprocess(raw_text)
        
        # Get stats
        stats = TextProcessor.get_stats(cleaned)
        
        # Chunk
        chunks = TextProcessor.split_into_chunks(
            cleaned,
            chunk_size=self.chunk_size,
            overlap=self.chunk_overlap,
        )
        
        logger.info(
            f"Seed processed: {stats['total_chars']} chars → "
            f"{len(chunks)} chunks (size={self.chunk_size}, overlap={self.chunk_overlap})"
        )
        
        return {
            "raw_text": cleaned,
            "chunks": chunks,
            "stats": stats,
            "requirement": requirement,
        }
