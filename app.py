"""Hugging Face Spaces entry point for IEEE-CIS Fraud Decisioning Platform.

Runs natively with Gradio 5 SDK on Hugging Face Spaces (Free Tier).
Embeds the React SPA and mounts the FastAPI backend endpoints under /api.
"""

import os
import subprocess
import sys
from pathlib import Path

# Ensure 'src' is on sys.path
ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Handle Hugging Face ZeroGPU if space requested ZeroGPU hardware
try:
    import spaces
    @spaces.GPU
    def _zero_gpu_init():
        return True
    _zero_gpu_init()
except Exception:
    pass

# Bootstrap model from sample if not present
MODEL_DIR = ROOT_DIR / "data" / "models" / "current"
MODEL_FILE = MODEL_DIR / "model.joblib"
if not MODEL_FILE.exists():
    print("Bootstrapping serving model from sample dataset...")
    train_script = ROOT_DIR / "scripts" / "train_model.py"
    subprocess.run([sys.executable, str(train_script)], check=False)

import gradio as gr
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from api.main import app as fastapi_app

DIST_DIR = ROOT_DIR / "web" / "dist"
INDEX_FILE = DIST_DIR / "index.html"
ASSETS_DIR = DIST_DIR / "assets"

with gr.Blocks(title="LEDGER // Fraud Decision Console", fill_height=True) as demo:
    gr.HTML(
        """
        <style>
            footer {visibility: hidden !important;}
            .gradio-container {max-width: 100% !important; padding: 0 !important; margin: 0 !important;}
        </style>
        <div style="width: 100%; height: 96vh; margin: 0; padding: 0; overflow: hidden; border-radius: 8px;">
            <iframe src="/app-view" style="width: 100%; height: 100%; border: none; display: block;"></iframe>
        </div>
        """
    )

# Mount endpoints on Gradio's internal FastAPI app
if ASSETS_DIR.exists():
    demo.app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")

@demo.app.get("/app-view", include_in_schema=False)
async def serve_app_view():
    if INDEX_FILE.exists():
        return FileResponse(str(INDEX_FILE))
    return {"error": "Frontend bundle not found. Run npm run build in web/."}

# Mount FastAPI backend under /api
demo.app.mount("/api", fastapi_app)

if __name__ == "__main__":
    demo.launch()
