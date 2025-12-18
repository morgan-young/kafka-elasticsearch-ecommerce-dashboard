#!/usr/bin/env python3
"""Script to start clickstream generator."""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.clickstream_generator import ClickstreamGenerator
from src.config import config

if __name__ == "__main__":
    generator = ClickstreamGenerator()
    events_per_sec = int(sys.argv[1]) if len(sys.argv) > 1 else config.EVENTS_PER_SECOND
    generator.run(events_per_second=events_per_sec)

