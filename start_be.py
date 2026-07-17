"""Minimal backend launcher — write log to file, retry on fail."""
import os, sys, time

os.environ["QNAI_JWT_SECRET"] = "dhaher-qna-valetax-2026-jwt-secret-killswitch-ready"
os.environ["QNAI_API_KEY"] = "qna-SCnDKQ0Tiwo9sTuaiMCrJattmfhMuJlc"
os.environ["PYTHONPATH"] = "."

sys.path.insert(0, ".")
from quant_nanggroe.api.app import create_app

if __name__ == "__main__":
    import uvicorn
    app = create_app()
    with open("backend_8001v2.log", "w") as f:
        f.write(f"APP_CREATED at {time.time()}\n")
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info", workers=1)
