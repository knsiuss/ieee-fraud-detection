"""Hugging Face Spaces entry point for IEEE-CIS Fraud Decisioning Platform.

Runs the ML API backend on Hugging Face Spaces (Free Tier).
Provides inference, simulation, SHAP forensic analysis, and audit streaming endpoints.
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
from fastapi.middleware.cors import CORSMiddleware
from api.main import app as fastapi_app, _seed_initial_decisions

with gr.Blocks(
    title="SENTINEL // ML Engine & API",
    theme=gr.themes.Monochrome(),
    fill_height=True,
) as demo:
    gr.HTML(
        """
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 24px; max-width: 900px; margin: 0 auto; color: #f4f4f5;">
            <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 24px; border-bottom: 1px solid #27272a; padding-bottom: 16px;">
                <div style="background: #10b981; width: 14px; height: 14px; border-radius: 50%; box-shadow: 0 0 12px #10b981;"></div>
                <h1 style="margin: 0; font-size: 24px; font-weight: 700; letter-spacing: -0.5px;">SENTINEL // Fraud ML Decisioning Backend</h1>
                <span style="background: #18181b; border: 1px solid #27272a; padding: 4px 10px; border-radius: 9999px; font-size: 12px; color: #10b981; font-weight: 600;">● SERVICE ONLINE</span>
            </div>
            
            <p style="color: #a1a1aa; line-height: 1.6; font-size: 15px;">
                This Hugging Face Space hosts the high-performance <strong>LightGBM 4.0 + SHAP TreeExplainer + FastAPI</strong> backend engine for the IEEE-CIS Fraud Detection System.
            </p>
            
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin: 24px 0;">
                <div style="background: #18181b; border: 1px solid #27272a; padding: 16px; border-radius: 8px;">
                    <div style="color: #a1a1aa; font-size: 12px; text-transform: uppercase; font-weight: 600;">API Base URL</div>
                    <div style="font-size: 14px; font-weight: 600; margin-top: 6px; word-break: break-all; color: #38bdf8;">https://p-quincy-fraud-detection-dashboard-simulation.hf.space</div>
                </div>
                <div style="background: #18181b; border: 1px solid #27272a; padding: 16px; border-radius: 8px;">
                    <div style="color: #a1a1aa; font-size: 12px; text-transform: uppercase; font-weight: 600;">Model Performance</div>
                    <div style="font-size: 14px; font-weight: 600; margin-top: 6px; color: #34d399;">ROC-AUC: 0.9223 (400 Features)</div>
                </div>
                <div style="background: #18181b; border: 1px solid #27272a; padding: 16px; border-radius: 8px;">
                    <div style="color: #a1a1aa; font-size: 12px; text-transform: uppercase; font-weight: 600;">CORS Policy</div>
                    <div style="font-size: 14px; font-weight: 600; margin-top: 6px; color: #fbbf24;">Enabled (Public Access)</div>
                </div>
            </div>

            <div style="margin-top: 24px;">
                <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 12px;">Quick Interactive Links:</h3>
                <ul style="list-style: none; padding: 0; display: flex; flex-direction: column; gap: 8px;">
                    <li><a href="/docs" target="_blank" style="color: #60a5fa; text-decoration: none;">📘 <strong>Interactive Swagger API Docs (/docs)</strong></a> — Test endpoints live</li>
                    <li><a href="/api/health" target="_blank" style="color: #60a5fa; text-decoration: none;">🩺 <strong>System Health Status (/api/health)</strong></a> — Check service health</li>
                    <li><a href="/api/model" target="_blank" style="color: #60a5fa; text-decoration: none;">🧠 <strong>Active Model Metadata (/api/model)</strong></a> — View serving model details</li>
                    <li><a href="/openapi.json" target="_blank" style="color: #60a5fa; text-decoration: none;">📄 <strong>OpenAPI Schema (/openapi.json)</strong></a> — Download specification</li>
                </ul>
            </div>
        </div>
        """
    )

# Add CORS and include all FastAPI routes on demo.app
demo.app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
demo.app.include_router(fastapi_app.router)
demo.app.on_event("startup")(_seed_initial_decisions)

if __name__ == "__main__":
    demo.launch()
