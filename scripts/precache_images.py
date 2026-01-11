#!/usr/bin/env python3
"""
Pre-cache one representative image per main character by scraping their
Big Bang Theory fandom page and saving the first suitable image into
`frontend/assets/remote/`.

Run from the repository root:
    python scripts/precache_images.py

This script requires `requests` and `beautifulsoup4` (in `requirements.txt`).
"""
import os
import re
import sys
import hashlib
import requests
from bs4 import BeautifulSoup

# Make the repository root importable so `from src...` works when running this
# script directly (e.g. `python scripts/precache_images.py`).
repo_root = os.path.dirname(os.path.dirname(__file__))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    from src.character_config import MAIN_CHARACTERS
except Exception:
    # Fallback: try to import from the src directory directly
    try:
        src_dir = os.path.join(repo_root, 'src')
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)
        from character_config import MAIN_CHARACTERS
    except Exception:
        # As a last resort, use a conservative default set
        MAIN_CHARACTERS = {
            "Sheldon", "Leonard", "Penny", "Howard",
            "Raj", "Amy", "Bernadette", "Stuart"
        }


def fetch_character_images_from_page(character_name, max_images=6):
    page_name = character_name.replace(' ', '_')
    url = f'https://bigbangtheory.fandom.com/wiki/{page_name}'

    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            print(f"Failed to fetch {url}: {resp.status_code}")
            return []

        soup = BeautifulSoup(resp.text, 'html.parser')

        imgs = []
        # Prefer JSON-LD and OpenGraph images when available
        try:
            for s in soup.find_all('script', type='application/ld+json'):
                try:
                    import json
                    jd = json.loads(s.string or '{}')
                    for key in ('image', 'thumbnailUrl'):
                        val = jd.get(key)
                        if isinstance(val, str) and val:
                            imgs.append(val)
                    me = jd.get('mainEntity') or jd.get('about')
                    if isinstance(me, dict):
                        iv = me.get('image')
                        if isinstance(iv, str) and iv:
                            imgs.append(iv)
                except Exception:
                    continue
        except Exception:
            pass

        og = soup.find('meta', property='og:image')
        if og and og.get('content'):
            imgs.append(og.get('content'))

        for img in soup.select('.mw-parser-output img, .article-table img, figure img'):
            src = img.get('data-src') or img.get('src') or ''
            if not src:
                srcset = img.get('srcset') or ''
                if srcset:
                    for part in srcset.split(','):
                        url = part.strip().split(' ')[0]
                        if url:
                            src = url
                            break
            if not src:
                continue

            if src.startswith('//'):
                src = 'https:' + src
            if src.startswith('/'):
                src = 'https://bigbangtheory.fandom.com' + src

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

            if re.search(r'\.(jpg|jpeg|png|gif|webp)(?:\?|$)', src, re.I):
                imgs.append(src)

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

        seen = set(); out = []
        for u in imgs:
            if u in seen: continue
            seen.add(u); out.append(u)
            if len(out) >= max_images: break

        return out
    except Exception as e:
        print(f"Error fetching images for {character_name}: {e}")
        return []


def download_image(url, character_name, dest_dir):
    try:
        r = requests.get(url, stream=True, timeout=15)
        if r.status_code != 200:
            print(f"Failed to download {url}: {r.status_code}")
            return None
    except Exception as e:
        print(f"Download error for {url}: {e}")
        return None

    raw = url.split('?')[0]
    _, ext = os.path.splitext(raw)
    if not re.search(r"\.(jpg|jpeg|png|gif)$", ext, re.I):
        ext = '.jpg'

    slug = re.sub(r'[^a-z0-9]+', '_', (character_name or 'char').lower())[:40]
    h = hashlib.md5(url.encode('utf-8')).hexdigest()[:8]
    fname = f"{slug}_{h}{ext}"
    out_path = os.path.join(dest_dir, fname)

    if os.path.exists(out_path):
        return out_path

    try:
        with open(out_path, 'wb') as f:
            for chunk in r.iter_content(1024):
                if not chunk:
                    break
                f.write(chunk)
        return out_path
    except Exception as e:
        print(f"Failed writing {out_path}: {e}")
        try:
            if os.path.exists(out_path):
                os.remove(out_path)
        except Exception:
            pass
        return None


def main():
    cwd = os.path.dirname(os.path.dirname(__file__))
    assets_remote = os.path.join(cwd, 'frontend', 'assets', 'remote')
    os.makedirs(assets_remote, exist_ok=True)

    print(f"Caching images into: {assets_remote}")

    for char in sorted(MAIN_CHARACTERS):
        print('\n==', char)
        imgs = fetch_character_images_from_page(char, max_images=4)
        if not imgs:
            print('  No images found')
            continue

        # Try the first images until one downloads
        downloaded = None
        for u in imgs:
            print('  trying', u)
            p = download_image(u, char, assets_remote)
            if p:
                print('  saved ->', p)
                downloaded = p
                break

        if not downloaded:
            print('  failed to download any candidate images')


if __name__ == '__main__':
    main()
