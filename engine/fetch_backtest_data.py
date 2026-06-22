# Wrapper for fetch_backtest_data script – imports main function from scripts.
import sys
from pathlib import Path

# Ensure repository root is on sys.path
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.fetch_backtest_data import main as fetch_main

if __name__ == "__main__":
    fetch_main()
