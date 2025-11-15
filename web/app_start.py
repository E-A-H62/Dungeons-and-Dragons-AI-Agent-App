"""
Database initialization script.

This script sets up MongoDB indexes for optimal query performance.
Run this once after setting up your MongoDB connection to ensure indexes exist.
"""

import os
import sys

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from core.db import ensure_indexes

if __name__ == "__main__":
    # Create indexes for dungeons, rooms, items, and characters collections
    # These indexes ensure uniqueness and improve query performance
    success = ensure_indexes()
    if success:
        print("MongoDB indexes ensured. Ready to go.")
    else:
        print("Index creation skipped (permissions issue).")
        print("You can create indexes manually through MongoDB Atlas UI if needed.")

