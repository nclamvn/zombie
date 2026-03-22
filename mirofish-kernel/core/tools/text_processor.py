"""
Text Processor — File Parsing, Chunking, Preprocessing

Enhanced from MiroFish's text_processor + file_parser.
Supports: PDF, Markdown, TXT with smart encoding detection.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional


def _read_text_with_fallback(file_path: str) -> str:
    """
    Read a text file with multi-level encoding fallback.
    
    Strategy:
    1. Try UTF-8
    2. charset_normalizer detection
    3. chardet detection
    4. UTF-8 with error replacement
    """
    data = Path(file_path).read_bytes()
    
    # Try UTF-8 first (most common)
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        pass
    
    # Try charset_normalizer
    encoding = None
    try:
        from charset_normalizer import from_bytes
        best = from_bytes(data).best()
        if best and best.encoding:
            encoding = best.encoding
    except Exception:
        pass
    
    # Fallback to chardet
    if not encoding:
        try:
            import chardet
            result = chardet.detect(data)
            encoding = result.get("encoding") if result else None
        except Exception:
            pass
    
    # Ultimate fallback
    return data.decode(encoding or "utf-8", errors="replace")


class FileParser:
    """
    Multi-format file parser.
    
    Extracts text from PDF, Markdown, TXT files.
    Extensible: add new formats by implementing _extract_from_<ext> methods.
    """
    
    SUPPORTED_EXTENSIONS = {".pdf", ".md", ".markdown", ".txt", ".text"}
    
    @classmethod
    def extract_text(cls, file_path: str) -> str:
        """Extract text content from a file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        suffix = path.suffix.lower()
        if suffix not in cls.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file format: {suffix}")
        
        if suffix == ".pdf":
            return cls._extract_from_pdf(file_path)
        return _read_text_with_fallback(file_path)
    
    @staticmethod
    def _extract_from_pdf(file_path: str) -> str:
        """Extract text from PDF using PyMuPDF."""
        try:
            import fitz
        except ImportError:
            raise ImportError("PyMuPDF required: pip install PyMuPDF")
        
        text_parts = []
        with fitz.open(file_path) as doc:
            for page in doc:
                text = page.get_text()
                if text.strip():
                    text_parts.append(text)
        return "\n\n".join(text_parts)
    
    @classmethod
    def extract_from_multiple(cls, file_paths: List[str]) -> str:
        """Extract and merge text from multiple files."""
        all_texts = []
        for i, file_path in enumerate(file_paths, 1):
            try:
                text = cls.extract_text(file_path)
                filename = Path(file_path).name
                all_texts.append(f"=== Document {i}: {filename} ===\n{text}")
            except Exception as e:
                all_texts.append(f"=== Document {i}: {file_path} (extraction failed: {e}) ===")
        return "\n\n".join(all_texts)


class TextProcessor:
    """
    Text processing utilities for the kernel pipeline.
    
    Handles: file extraction, preprocessing, chunking, stats.
    """
    
    @staticmethod
    def extract_from_files(file_paths: List[str]) -> str:
        """Extract text from multiple files."""
        return FileParser.extract_from_multiple(file_paths)
    
    @staticmethod
    def preprocess(text: str) -> str:
        """
        Clean and normalize text.
        
        - Normalize line endings
        - Remove excessive blank lines
        - Strip line whitespace
        """
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"\n{3,}", "\n\n", text)
        lines = [line.strip() for line in text.split("\n")]
        return "\n".join(lines).strip()
    
    @staticmethod
    def split_into_chunks(
        text: str,
        chunk_size: int = 500,
        overlap: int = 50,
        sentence_boundaries: bool = True,
    ) -> List[str]:
        """
        Split text into overlapping chunks.
        
        Enhanced with:
        - Smart sentence boundary detection (CJK + Latin)
        - Minimum chunk size enforcement
        - Configurable overlap
        
        Args:
            text: Input text
            chunk_size: Target characters per chunk
            overlap: Overlap between adjacent chunks
            sentence_boundaries: Try to split at sentence boundaries
            
        Returns:
            List of text chunks
        """
        if len(text) <= chunk_size:
            return [text] if text.strip() else []
        
        # Sentence boundary markers (CJK-aware)
        BOUNDARIES = ["。", "！", "？", ".\n", "!\n", "?\n", "\n\n", ". ", "! ", "? "]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to split at sentence boundary
            if sentence_boundaries and end < len(text):
                for sep in BOUNDARIES:
                    last_sep = text[start:end].rfind(sep)
                    if last_sep != -1 and last_sep > chunk_size * 0.3:
                        end = start + last_sep + len(sep)
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap if end < len(text) else len(text)
        
        return chunks
    
    @staticmethod
    def get_stats(text: str) -> Dict[str, Any]:
        """Get text statistics."""
        return {
            "total_chars": len(text),
            "total_lines": text.count("\n") + 1,
            "total_words": len(text.split()),
            "estimated_tokens": len(text) // 4,  # Rough estimate
        }
