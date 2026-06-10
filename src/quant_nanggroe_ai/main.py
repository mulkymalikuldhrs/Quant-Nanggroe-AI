"""
Quant-Nanggroe-AI — Application Entry Point
=============================================
Uvicorn entry point for the FastAPI application.

Usage::

    poetry run uvicorn quant_nanggroe_ai.main:app --host 0.0.0.0 --port 8000 --reload

Or programmatically::

    from quant_nanggroe_ai.main import app
"""

from quant_nanggroe_ai.api.app import create_app

# Create the FastAPI application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "quant_nanggroe_ai.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
