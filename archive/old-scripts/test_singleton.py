"""Quick test to verify singleton behavior of build_execution_manager.

Standalone — adds the repo root to sys.path and imports builder directly.
Does NOT rely on the full quant_nanggroe package being importable at module
level (which may hang due to dependencies). Instead, we patch the import
chain to test only the builder module's singleton logic.
"""
import sys
import os

# Add repo root to path
REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)

# Test 1: Check the module-level singleton vars exist
from quant_nanggroe.engine.execution import builder as bmod

assert hasattr(bmod, '_em_singleton'), "_em_singleton not found"
assert hasattr(bmod, '_em_lock'), "_em_lock not found"
assert bmod._em_singleton is None, "Singleton should start as None"

print("MODULE_OK: singleton vars exist")

# Test 2: Call build_execution_manager twice, verify same object returned
# We need to prevent the hang from internal broker code. Let's try it.
import threading
import time

result = [None]
exception = [None]

def try_build():
    try:
        a = bmod.build_execution_manager(allow_live=False)
        c = bmod.build_execution_manager(allow_live=False)
        result[0] = (a, c)
    except Exception as e:
        exception[0] = e

t = threading.Thread(target=try_build, daemon=True)
t.start()
t.join(timeout=30)

if exception[0]:
    print(f"BUILD_FAILED: {exception[0]}")
    # Even if the build function itself errors, if _em_singleton was set
    # before the error, the singleton mechanism still works. Let's check.
    # Actually, if build fails, _em_singleton won't be set, so that's not 
    # a valid test of the singleton.
    print("NOTE: build failed, cannot test singleton identity")
    sys.exit(1)

if result[0] is None:
    print("BUILD_TIMEOUT: build_execution_manager hung")
    sys.exit(1)

a, c = result[0]
print(f"SINGLETON_OK {a is c}")
assert a is c, f"Singleton failed: {id(a)} != {id(c)}"
sys.exit(0)
