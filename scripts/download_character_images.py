#!/usr/bin/env python3
"""Download up to N images per character from Big Bang Theory fandom pages.

Saves images into frontend/assets/remote/ as <slug>_<idx>.<ext>
"""
import os
import re
import time
import hashlib
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT_DIR = os.path.join(ROOT, 'frontend', 'assets', 'remote')
os.makedirs(OUT_DIR, exist_ok=True)

CANONICAL = [
    "Sheldon",
    "Leonard",
    "Penny",
    "Howard",
    "Raj",
    "Amy",
    "Bernadette",
    "Stuart",
    "Mary Cooper",
    "Beverly Hofstadter",
    "Debbie Wolowitz",
    "Wyatt",
    "Susan",
]

HEADERS = {
    'User-Agent': 'who-said-what-bot/1.0 (+https://example.invalid)'
}

def slug(name):
    return re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')[:60]

def gather_image_urls(page_text, base_url):
    soup = BeautifulSoup(page_text, 'html.parser')
    imgs = []

    # JSON-LD and OpenGraph
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
        og = soup.find('meta', property='og:image')
        if og and og.get('content'):
            imgs.append(og.get('content'))
    except Exception:
        pass

    # Collect images from content areas
    for img in soup.select('.mw-parser-output img, .article-table img, figure img, .thumbimage'):
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
            src = urljoin('https://bigbangtheory.fandom.com', src)

        # attempt to convert thumb URLs to original
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

        imgs.append(src)

        srcset = img.get('srcset') or ''
        if srcset:
            for part in srcset.split(','):
                url = part.strip().split(' ')[0]
                if url.startswith('//'):
                    url = 'https:' + url
                if url.startswith('/'):
                    url = urljoin('https://bigbangtheory.fandom.com', url)
                imgs.append(url)

    # filter and dedupe
    out = []
    seen = set()
    for u in imgs:
        if not u or not re.search(r'\.(jpg|jpeg|png|gif|webp)(?:\?|$)', u, re.I):
            continue
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out

def download(url, out_path):
    try:
        with requests.get(url, stream=True, headers=HEADERS, timeout=12) as r:
            if r.status_code != 200:
                return False
            with open(out_path, 'wb') as f:
                for chunk in r.iter_content(1024):
                    if not chunk:
                        break
                    f.write(chunk)
        return True
    except Exception:
        return False

def ext_from_url(u):
    import os
    raw = u.split('?')[0]
    _, ext = os.path.splitext(raw)
    if re.search(r'\.(jpg|jpeg|png|gif|webp)$', ext, re.I):
        return ext
    return '.jpg'

def main():
    per_char = 5
    for name in CANONICAL:
        page_name = name.replace(' ', '_')
        url = f'https://bigbangtheory.fandom.com/wiki/{page_name}'
        print(f'Fetching {name} → {url}')
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code != 200:
                print(f'  WARN: status {r.status_code} for {url}')
                time.sleep(1)
                continue
            urls = gather_image_urls(r.text, url)
            # Fallback: try MediaWiki API to list images on the page
            if not urls:
                try:
                    api_urls = []
                    api_ep = 'https://bigbangtheory.fandom.com/api.php'
                    params = {
                        'action': 'query',
                        'titles': page_name,
                        'prop': 'images',
                        'format': 'json',
                        'imlimit': 'max'
                    }
                    resp = requests.get(api_ep, params=params, headers=HEADERS, timeout=10)
                    j = resp.json()
                    pages = j.get('query', {}).get('pages', {})
                    image_titles = []
                    for p in pages.values():
                        for im in p.get('images', []) if p.get('images') else []:
                            image_titles.append(im.get('title'))

                    # For each image title, fetch imageinfo (direct url)
                    for it in image_titles:
                        q = {
                            'action': 'query',
                            'titles': it,
                            'prop': 'imageinfo',
                            'iiprop': 'url',
                            'format': 'json'
                        }
                        r2 = requests.get(api_ep, params=q, headers=HEADERS, timeout=10)
                        j2 = r2.json()
                        for p2 in j2.get('query', {}).get('pages', {}).values():
                            ii = p2.get('imageinfo')
                            if ii and isinstance(ii, list):
                                url_img = ii[0].get('url')
                                if url_img:
                                    api_urls.append(url_img)

                    # dedupe/preserve order
                    seen = set(); out = []
                    for u in api_urls:
                        if u in seen: continue
                        seen.add(u); out.append(u)
                    if out:
                        urls = out
                except Exception:
                    pass
            # Additional fallback: search File namespace for filenames containing the character name
            if not urls:
                try:
                    api_ep = 'https://bigbangtheory.fandom.com/api.php'
                    params = {
                        'action': 'query',
                        'list': 'search',
                        'srsearch': page_name,
                        'srnamespace': '6',
                        'format': 'json',
                        'srlimit': '50'
                    }
                    resp = requests.get(api_ep, params=params, headers=HEADERS, timeout=10)
                    j = resp.json()
                    file_titles = [item.get('title') for item in j.get('query', {}).get('search', []) if item.get('title')]
                    api_urls = []
                    for it in file_titles:
                        q = {
                            'action': 'query',
                            'titles': it,
                            'prop': 'imageinfo',
                            'iiprop': 'url',
                            'format': 'json'
                        }
                        r2 = requests.get(api_ep, params=q, headers=HEADERS, timeout=10)
                        j2 = r2.json()
                        for p2 in j2.get('query', {}).get('pages', {}).values():
                            ii = p2.get('imageinfo')
                            if ii and isinstance(ii, list):
                                url_img = ii[0].get('url')
                                if url_img:
                                    api_urls.append(url_img)

                    # dedupe/preserve order
                    seen = set(); out = []
                    for u in api_urls:
                        if u in seen: continue
                        seen.add(u); out.append(u)
                    if out:
                        urls = out
                except Exception:
                    pass
            if not urls:
                print('  No images found on page')
                time.sleep(1)
                continue

            saved = 0
            s = slug(name)
            for u in urls:
                if saved >= per_char:
                    break
                e = ext_from_url(u)
                # create deterministic filename based on url hash to avoid duplicates
                h = hashlib.md5(u.encode('utf-8')).hexdigest()[:8]
                fname = f"{s}_{h}{e}"
                out_path = os.path.join(OUT_DIR, fname)
                if os.path.exists(out_path):
                    print(f'  already have {fname} (skipping)')
                    saved += 1
                    continue
                print(f'  Downloading {u} -> {fname}')
                ok = download(u, out_path)
                if ok:
                    saved += 1
                else:
                    print('    failed')
                time.sleep(0.6)

            print(f'  Saved {saved}/{per_char} images for {name}')
        except Exception as e:
            print('  error', e)
        # be polite
        time.sleep(1.2)

    print('Done')

if __name__ == '__main__':
    main()
