# Wrapper for run_walkforward script – imports main function from scripts.
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.run_walkforward import main as walk_main

if __name__ == "__main__":
    walk_main()
