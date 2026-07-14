#!/usr/bin/env python3
"""
⚡ Quant Nanggroe AI — Legacy CLI Wrapper
═════════════════════════════════════════

This file is now a THIN WRAPPER that delegates to the unified launcher (qna.py).
The unified launcher is the single source of truth for all entry modes.

The legacy Click-based CLI is preserved under 'python cli.py legacy' for
backward compatibility.

Usage:
    python cli.py                → same as python qna.py (interactive CLI)
    python cli.py api            → same as python qna.py api
    python cli.py --version      → same as python qna.py --version
    python cli.py legacy start   → legacy Click-based CLI (preserved)

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
    from qna import build_parser, __version__
except ImportError as e:
    print(f"❌ Failed to load unified launcher (qna.py): {e}")
    print("   Ensure qna.py is in the project root directory.")
    sys.exit(1)


def main() -> int:
    """Legacy CLI entry point — delegates to qna.py."""
    parser = build_parser()
    args, remaining = parser.parse_known_args()

    # Handle --version
    if args.version:
        print(f"Quant Nanggroe AI v{__version__}")
        return 0

    # If 'legacy' mode requested, defer to old Click-based CLI
    if remaining and remaining[0] == "legacy":
        warnings.warn(
            "Legacy Click-based CLI is deprecated. Use 'python qna.py cli' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        _legacy_main()
        return 0

    # Delegate to qna.py's main
    warnings.warn(
        "cli.py is deprecated. Use 'python qna.py' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    from qna import main as qna_main
    return qna_main()


# ── Preserved legacy Click CLI for backward compatibility ───────────
# The following code is the original Click-based CLI, kept for reference.
# It is only activated when called directly as 'python cli.py legacy'.
# New code should use 'python qna.py cli' instead.

if __name__ == "__main__":
    # Check if 'legacy' was passed as first arg
    if len(sys.argv) > 1 and sys.argv[1] == "legacy":
        # Run legacy Click CLI (remove 'legacy' from argv)
        sys.argv.pop(1)
        # The legacy Click CLI is preserved at the bottom of this file
        _legacy_main()
    else:
        sys.exit(main())


# ══════════════════════════════════════════════════════════════════════
#  PRESERVED LEGACY CLI (Click-based, for backward compatibility)
# ══════════════════════════════════════════════════════════════════════

def _legacy_main():
    """Legacy Click CLI entry point."""
    print("⚠️  Legacy Click CLI is preserved for backward compatibility.")
    print("   Consider using 'python qna.py cli' instead.")
    print()
    from cli_click import cli
    cli()
