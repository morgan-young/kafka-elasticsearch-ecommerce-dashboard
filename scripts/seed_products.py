#!/usr/bin/env python3
"""Script to seed products."""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.product_seeder import seed_products
from src.config import config

if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else config.PRODUCT_COUNT
    seed_products(count)

