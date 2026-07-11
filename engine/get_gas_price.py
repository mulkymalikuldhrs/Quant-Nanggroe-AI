# Wrapper for get_gas_price script – imports main function from scripts.
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.get_gas_price import main as gas_main

if __name__ == "__main__":
    gas_main()
