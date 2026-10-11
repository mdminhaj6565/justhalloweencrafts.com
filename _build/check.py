"""Quick quality check of the built site. Run after `python3 _build/build.py`.

    python3 _build/check.py            # whole site
    python3 _build/check.py /2026/11/x # also print a detailed report for these pages

Exit code 1 when something must be fixed before committing:
broken internal links or images, a page without exactly one H1, duplicate titles,
a new article (_build/content/new) outside 1,000-1,600 words, or invalid JSON-LD.
"""
import glob
import json
import os
import re
import sys
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEW_DIR = os.path.join(ROOT, '_build', 'content', 'new')


def exists(path):
    if path == '/':
        return os.path.exists(os.path.join(ROOT, 'index.html'))
    p = os.path.join(ROOT, path.lstrip('/'))
    return os.path.isfile(p) or os.path.isfile(p + '.html')


def words(html_text):
    return len(BeautifulSoup(html_text, 'html.parser').get_text(' ', strip=True).split())


problems, warnings = [], []
titles, pages, descs = {}, {}, {}
for f in glob.glob(os.path.join(ROOT, '**', '*.html'), recursive=True):
    rel = os.path.relpath(f, ROOT)
    if rel.startswith('_build') or rel.startswith('.git'):
        continue
    s = BeautifulSoup(open(f, encoding='utf-8').read(), 'html.parser')
    url = '/' + rel[:-5] if rel != 'index.html' else '/'
    pages[url] = s
    if len(s.find_all('h1')) != 1:
        problems.append(f'{url}: {len(s.find_all("h1"))} H1 tags')
    t = s.title.get_text() if s.title else ''
    titles.setdefault(t, []).append(url)
    robots = s.find('meta', attrs={'name': 'robots'})
    indexable = not (robots and 'noindex' in robots.get('content', ''))
    if indexable and rel not in ('404.html',):
        if len(t) > 65:
            warnings.append(f'{url}: title {len(t)} chars')
        md = s.find('meta', attrs={'name': 'description'})
        d = md['content'] if md else ''
        descs.setdefault(d, []).append(url)
        if not 70 <= len(d) <= 165:
            warnings.append(f'{url}: description {len(d)} chars')
    for sc in s.find_all('script', type='application/ld+json'):
        try:
            json.loads(sc.string or '')
        except Exception as e:  # noqa: BLE001
            problems.append(f'{url}: invalid JSON-LD ({e})')
    for tag, attr in (('a', 'href'), ('img', 'src'), ('link', 'href'), ('script', 'src')):
        for el in s.find_all(tag):
            v = el.get(attr)
            if not v:
                continue
            u = urlparse(v)
            if u.scheme in ('http', 'https'):
                if 'justhalloweencrafts.com' not in u.netloc:
                    continue
            elif u.scheme:
                continue
            path = unquote(u.path)
            if not path:
                continue
            if not path.startswith('/'):
                path = os.path.normpath(os.path.join('/', os.path.dirname(rel), path))
            if not exists(path):
                problems.append(f'{url}: broken {tag} -> {path}')

for t, urls in titles.items():
    if len(urls) > 1:
        problems.append(f'duplicate title "{t}" on {urls[:4]}')

for d, urls in descs.items():
    if len(urls) > 1:
        problems.append(f'duplicate description on {urls[:4]}')

for fn in sorted(os.listdir(NEW_DIR)):
    if not fn.endswith('.html'):
        continue
    raw = open(os.path.join(NEW_DIR, fn), encoding='utf-8').read()
    m = re.match(r'\s*<!--\s*(\{.*?\})\s*-->\s*', raw, re.S)
    if not m:
        problems.append(f'{fn}: missing JSON header')
        continue
    try:
        meta = json.loads(m.group(1))
    except Exception as e:  # noqa: BLE001
        problems.append(f'{fn}: bad JSON header ({e})')
        continue
    n = words(raw[m.end():])
    if not 1000 <= n <= 1600:
        problems.append(f'{fn}: {n} words (needs 1,000-1,600)')
    if meta.get('url') not in pages:
        problems.append(f'{fn}: page {meta.get("url")} was not built')

sitemap = open(os.path.join(ROOT, 'sitemap.xml'), encoding='utf-8').read()
for url in sys.argv[1:]:
    s = pages.get(url)
    if not s:
        problems.append(f'{url}: not found')
        continue
    body = s.find('article') or s
    print(f'\n== {url}')
    print('title      :', s.title.get_text() if s.title else '')
    md = s.find('meta', attrs={'name': 'description'})
    print('description:', md['content'] if md else '')
    print('h1         :', s.h1.get_text(strip=True) if s.h1 else '')
    print('words      :', len(body.get_text(' ', strip=True).split()))
    print('in sitemap :', f'<loc>https://www.justhalloweencrafts.com{url}</loc>' in sitemap)
    print('internal links:', len([a for a in body.find_all('a', href=True) if a['href'].startswith('/')]))

print(f'\nchecked {len(pages)} pages')
for w in warnings[:40]:
    print('WARN', w)
for p in problems:
    print('PROBLEM', p)
print('OK' if not problems else f'{len(problems)} problem(s) to fix')
sys.exit(1 if problems else 0)
