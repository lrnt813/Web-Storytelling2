"""Compatibility entrypoint for the FastAPI app.

The implementation lives in backend.main. Keeping this file lets older commands
such as `uvicorn main:app` and `python main.py` continue to work.
"""

from backend.main import app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False, log_level="info", workers=1)
