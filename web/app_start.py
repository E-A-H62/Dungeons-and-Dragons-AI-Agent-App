import os
import sys

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from core.db import ensure_indexes

if __name__ == "__main__":
    success = ensure_indexes()
    if success:
        print("MongoDB indexes ensured. Ready to go.")
    else:
        print("Index creation skipped (permissions issue).")
        print("You can create indexes manually through MongoDB Atlas UI if needed.")

