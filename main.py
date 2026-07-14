"""
🧠 Quant Nanggroe AI — Legacy Main Entry Point
══════════════════════════════════════════════

This file is now a THIN WRAPPER that delegates to the unified launcher (qna.py).
The unified launcher is the single source of truth for all entry modes.

Usage:
    python main.py              → same as python qna.py (interactive CLI)
    python main.py api          → same as python qna.py api
    python main.py daemon       → same as python qna.py daemon

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import sys
import warnings
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

# Delegate to unified launcher
try:
    from qna import main as qna_main, build_parser, __version__
except ImportError as e:
    print(f"❌ Failed to load unified launcher (qna.py): {e}")
    print("   Ensure qna.py is in the project root directory.")
    sys.exit(1)


def main() -> int:
    """Legacy main entry point — delegates to qna.py."""
    warnings.warn(
        "main.py is deprecated. Use 'python qna.py' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return qna_main()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)
