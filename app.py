"""Hugging Face Spaces entry point for IEEE-CIS Fraud Decisioning Platform.

Compatible with Hugging Face Spaces (Gradio SDK - Free Tier, no credit card required).
Mounts the FastAPI application which serves both the React SPA at / and API endpoints at /api.
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

# Bootstrap model from sample if not present
MODEL_DIR = ROOT_DIR / "data" / "models" / "current"
MODEL_FILE = MODEL_DIR / "model.joblib"
if not MODEL_FILE.exists():
    print("Bootstrapping serving model from sample dataset...")
    train_script = ROOT_DIR / "scripts" / "train_model.py"
    subprocess.run([sys.executable, str(train_script)], check=False)

import gradio as gr
from api.main import app as fastapi_app

# Gradio interface for HF Spaces discovery
demo = gr.Blocks(title="LEDGER // Fraud Decision Console")
with demo:
    gr.HTML('<iframe src="/" style="width: 100%; height: 95vh; border: none; border-radius: 8px;"></iframe>')

# Mount Gradio sub-app at /gradio so HF detects the Gradio SDK while FastAPI serves root / and /api
app = gr.mount_gradio_app(fastapi_app, demo, path="/gradio")
demo.app = app

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
