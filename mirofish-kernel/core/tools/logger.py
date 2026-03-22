"""
Logger — Structured logging for MiroFish Kernel
"""

import logging
import sys
from typing import Optional


_loggers = {}


def setup_logger(
    name: str = "mirofish",
    level: int = logging.INFO,
    fmt: str = "[%(asctime)s] %(name)s | %(levelname)s | %(message)s",
) -> logging.Logger:
    """
    Set up a named logger with console output.
    
    Args:
        name: Logger name (hierarchical, e.g., 'mirofish.pipeline')
        level: Logging level
        fmt: Log format string
        
    Returns:
        Configured logger
    """
    if name in _loggers:
        return _loggers[name]
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        handler.setFormatter(logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S"))
        logger.addHandler(handler)
    
    _loggers[name] = logger
    return logger


def get_logger(name: str = "mirofish") -> logging.Logger:
    """Get or create a logger by name."""
    if name in _loggers:
        return _loggers[name]
    return setup_logger(name)
