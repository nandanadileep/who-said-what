from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import re
import requests
from bs4 import BeautifulSoup
import random
from typing import Optional

# Import predict_character from the same package in a way that works
# whether this file is run as a module (e.g. `uvicorn src.server`) or
# executed directly (e.g. `python src/server.py`).
try:
    # When run as a package module (recommended)
    from .predict_character import predict_character
except Exception:
    # Fallback: add the src dir to sys.path and import as top-level module
    import sys
    src_dir = os.path.dirname(__file__)
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    from predict_character import predict_character

app = FastAPI(title="Who Said What - Y2K Frontend API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Note: static mount moved to the bottom of this file so API routes
# (e.g. POST /api/predict) are registered first and not intercepted by StaticFiles.


@app.post('/api/predict')
async def api_predict(payload: Request):
    data = await payload.json()
    query = data.get('query', '').strip()
    min_confidence = data.get('min_confidence', 0.25)

    if not query:
        return JSONResponse({"error": "Empty query"}, status_code=400)

    try:
        result = predict_character(query, k=20, score_method="reciprocal_rank_fusion", min_confidence=min_confidence)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    # Try to fetch representative images from fandom for the predicted character.
    def fetch_character_images(character_name, max_images=6):
        if not character_name:
            return []

        # Build wiki URL (common fandom layout)
        page_name = character_name.replace(' ', '_')
        url = f'https://bigbangtheory.fandom.com/wiki/{page_name}'

        try:
            resp = requests.get(url, timeout=8)
            if resp.status_code != 200:
                return []

            soup = BeautifulSoup(resp.text, 'html.parser')

            imgs = []
            # Prefer JSON-LD and OpenGraph images when available
            try:
                # JSON-LD
                for s in soup.find_all('script', type='application/ld+json'):
                    try:
                        import json
                        jd = json.loads(s.string or '{}')
                        for key in ('image', 'thumbnailUrl'):
                            val = jd.get(key)
                            if isinstance(val, str) and val:
                                imgs.append(val)
                        # nested mainEntity
                        me = jd.get('mainEntity') or jd.get('about')
                        if isinstance(me, dict):
                            iv = me.get('image')
                            if isinstance(iv, str) and iv:
                                imgs.append(iv)
                    except Exception:
                        continue

                # OpenGraph
                og = soup.find('meta', property='og:image')
                if og and og.get('content'):
                    imgs.append(og.get('content'))
            except Exception:
                pass
            # Look for images in the main content area and collect src/srcset
            for img in soup.select('.mw-parser-output img, .article-table img, figure img'):
                # prefer data-src (lazy-loaded images), then src
                src = img.get('data-src') or img.get('src') or ''
                if not src:
                    # check srcset for candidates
                    srcset = img.get('srcset') or ''
                    if srcset:
                        for part in srcset.split(','):
                            url = part.strip().split(' ')[0]
                            if url:
                                src = url
                                break
                if not src:
                    continue

                # Make absolute URLs
                if src.startswith('//'):
                    src = 'https:' + src
                if src.startswith('/'):
                    src = 'https://bigbangtheory.fandom.com' + src

                # If this is a Fandom thumbnail URL, try to reconstruct original image URL
                if '/thumb/' in src:
                    try:
                        prefix, tail = src.split('/thumb/', 1)
                        filename = tail.split('/')[-1].split('?')[0]
                        candidate = prefix + '/' + filename
                        if candidate.startswith('//'):
                            candidate = 'https:' + candidate
                        imgs.append(candidate)
                    except Exception:
                        pass

                # Always include the src itself if it looks like an image (include webp)
                if re.search(r'\.(jpg|jpeg|png|gif|webp)(?:\?|$)', src, re.I):
                    imgs.append(src)

                # Also consider srcset entries
                srcset = img.get('srcset') or ''
                if srcset:
                    for part in srcset.split(','):
                        url = part.strip().split(' ')[0]
                        if url.startswith('//'):
                            url = 'https:' + url
                        if url.startswith('/'):
                            url = 'https://bigbangtheory.fandom.com' + url
                        if re.search(r'\.(jpg|jpeg|png|gif|webp)(?:\?|$)', url, re.I):
                            imgs.append(url)

            # Deduplicate while preserving order
            seen = set(); out = []
            for u in imgs:
                if u in seen: continue
                seen.add(u); out.append(u)
                if len(out) >= max_images: break

            return out
        except Exception:
            return []

    images = []
    try:
        images = fetch_character_images(result.get('prediction'))
    except Exception:
        images = []

    # First, prefer curated local gallery images for the predicted character
    pred = result.get('prediction')
    try:
        if pred:
            slug = re.sub(r'[^a-z0-9]+', '_', pred.lower())[:60]
            chars_dir = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'assets', 'characters', slug)
            if os.path.isdir(chars_dir):
                files = [f for f in os.listdir(chars_dir) if os.path.isfile(os.path.join(chars_dir, f))]
                if files:
                    pick = random.choice(files)
                    result['local_image'] = f"/assets/characters/{slug}/{pick}"
    except Exception:
        pass

    # Add image results to response if available (from scraping)
    if images:
        result['image_urls'] = images
        result['image'] = images[0]

    # If still no local_image, attempt to download and cache the primary image locally for stability
    if not result.get('local_image') and images:
        try:
            cache_dir = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'assets', 'remote')
            os.makedirs(cache_dir, exist_ok=True)

            def download_and_cache_image(url, character_name):
                try:
                    r = requests.get(url, stream=True, timeout=12)
                    if r.status_code != 200:
                        return None
                except Exception:
                    return None

                # File extension heuristic
                raw = url.split('?')[0]
                _, ext = os.path.splitext(raw)
                if not re.search(r"\.(jpg|jpeg|png|gif|webp)$", ext, re.I):
                    ext = '.jpg'

                import hashlib
                slug = re.sub(r'[^a-z0-9]+', '_', (character_name or 'char').lower())[:40]
                h = hashlib.md5(url.encode('utf-8')).hexdigest()[:8]
                fname = f"{slug}_{h}{ext}"
                out_path = os.path.join(cache_dir, fname)

                # If already cached, return relative path
                if os.path.exists(out_path):
                    return f"/assets/remote/{fname}"

                try:
                    with open(out_path, 'wb') as f:
                        for chunk in r.iter_content(1024):
                            if not chunk:
                                break
                            f.write(chunk)
                    return f"/assets/remote/{fname}"
                except Exception:
                    # Clean up partial
                    try:
                        if os.path.exists(out_path):
                            os.remove(out_path)
                    except Exception:
                        pass
                    return None

            local = download_and_cache_image(images[0], result.get('prediction'))
            if local:
                result['local_image'] = local
        except Exception:
            pass

    # Return prediction and character name
    return JSONResponse(result)


@app.post('/api/predict_demo')
async def api_predict_demo(payload: Request):
    """Lightweight demo prediction that doesn't require the embedding index.

    Useful for local development when the vector index or heavy deps are unavailable.
    """
    data = await payload.json()
    query = (data.get('query') or '').strip()
    if not query:
        return JSONResponse({"error": "Empty query"}, status_code=400)

    # Simple heuristic: match character name in query, otherwise pick random main character
    try:
        from .character_config import MAIN_CHARACTERS
    except Exception:
        from character_config import MAIN_CHARACTERS

    ql = query.lower()
    chosen: Optional[str] = None
    for c in MAIN_CHARACTERS:
        if c.lower() in ql:
            chosen = c
            confidence = 0.92
            break

    if not chosen:
        chosen = random.choice(list(MAIN_CHARACTERS))
        confidence = round(random.uniform(0.45, 0.85), 2)

    # build scores: chosen gets majority, others small probs
    others = [c for c in MAIN_CHARACTERS if c != chosen]
    base = 1.0
    scores = {chosen: round(0.6 + (confidence - 0.5) * 0.6, 3)}
    rem = 1.0 - scores[chosen]
    if others:
        per = rem / len(others)
        for o in others:
            scores[o] = round(per, 3)

    # Attempt to locate a local image in assets (remote cache or curated characters)
    local_image = None
    try:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend', 'assets'))
        slug = re.sub(r'[^a-z0-9]+', '_', chosen.lower())[:60]

        # Check curated character folder
        char_dir = os.path.join(base_dir, 'characters', slug)
        if os.path.isdir(char_dir):
            files = [f for f in os.listdir(char_dir) if os.path.isfile(os.path.join(char_dir, f))]
            if files:
                local_image = f"/assets/characters/{slug}/{random.choice(files)}"

        # Check remote cache
        if not local_image:
            remote_files = [f for f in os.listdir(os.path.join(base_dir, 'remote')) if f.lower().startswith(slug + '_')]
            if remote_files:
                local_image = f"/assets/remote/{random.choice(remote_files)}"

        # Check single SVG fallback
        if not local_image:
            svg_path = os.path.join(base_dir, f"{slug}.svg")
            if os.path.exists(svg_path):
                local_image = f"/assets/{slug}.svg"
    except Exception:
        local_image = None

    result = {
        'prediction': chosen,
        'confidence': confidence,
        'all_scores': scores,
        'image': None,
        'local_image': local_image,
        'method': 'demo',
    }

    return JSONResponse(result)


# Serve the frontend from the 'frontend' directory (mount after API routes)
frontend_dir = os.path.join(os.path.dirname(__file__), '..', 'frontend')
frontend_dir = os.path.abspath(frontend_dir)

if os.path.isdir(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


if __name__ == '__main__':
    # Now the frontend is registered BEFORE the server starts
    uvicorn.run("src.server:app", host="0.0.0.0", port=8000, log_level="info")