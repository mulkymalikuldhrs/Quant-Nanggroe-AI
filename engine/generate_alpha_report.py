# Wrapper for generate_alpha_report script – imports main function from scripts.
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.generate_alpha_report import main as report_main

if __name__ == "__main__":
    report_main()
