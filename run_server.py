"""QNA Server boot — standalone launcher."""
import os
import sys
import logging

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ".")

# ponytail: import once so all modules are cached
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("boot")
logger.info("Importing app module...")
from quant_nanggroe.api.app import app
logger.info("App module loaded. Starting uvicorn...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
