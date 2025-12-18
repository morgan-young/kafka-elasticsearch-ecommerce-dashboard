#!/usr/bin/env python3
"""Script to start stream processor."""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.stream_processor import StreamProcessor

if __name__ == "__main__":
    processor = StreamProcessor()
    processor.run()

