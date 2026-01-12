# app.py - Entry point for HuggingFace Spaces
import os
os.system("uvicorn src.server:app --host 0.0.0.0 --port 7860")