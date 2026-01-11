# Who Said What — Character Predictor

Simple web UI and FastAPI backend to predict which Big Bang Theory character likely said a short line or matches a small context.

Quick start
1. Create and activate a Python virtualenv (recommended).
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Ensure you have built the embedding index (the project includes `src/build_index.py`). If you have a prebuilt index it can be placed in `data/index/faiss`.

4. Run the backend (serves API + frontend static files):

```bash
uvicorn src.server:app --reload --host 0.0.0.0 --port 8000
```

5. Open http://localhost:8000 in your browser. Type a short quote or a personality/vibe and click "Predict".

Notes
- The frontend is in the `frontend/` folder. The prediction endpoint is `POST /api/predict` and expects JSON `{ "query": "...", "min_confidence": 0.25 }`.
- Preview images for characters are served from `frontend/assets/characters` when available, otherwise the server will attempt to fetch and cache an image from fandom.
- If you get errors about missing NLP/embedding packages, ensure `sentence-transformers` and `faiss-cpu` are installed and that `data/index/faiss/index.faiss` exists.

Troubleshooting
- If you see `No documents retrieved` or low confidence, build the index with more data using `src/build_index.py` and the dataset in `data/raw`.
