#!/usr/bin/env python3
"""Static site generator for justhalloweencrafts.com.

Usage (from the repository root):
    python3 _build/build.py

Reads content from _build/content/ and writes the public website into the
repository root (index.html, blog.html, 2016/03/post.html, search/label/*.html,
sitemap.xml, feed.xml, robots.txt ...). Images under /images and /img are the
original site images and are never modified; thumbnails and social cards are
generated into /images/thumbs and /images/cards.
"""
import datetime as dt
import html
import json
import os
import re
import shutil
from email.utils import format_datetime

from bs4 import BeautifulSoup

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except ImportError:  # thumbnails are optional when Pillow is missing
    Image = None

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SRC = os.path.join(ROOT, '_build')
CONTENT = os.path.join(SRC, 'content')
SITE = 'https://www.justhalloweencrafts.com'
NAME = 'Just Halloween Crafts'
TAGLINE = 'DIY Halloween crafts, costumes, printables and party treats'
GA_ID = 'G-34D5HXD2C1'
TODAY = dt.date.today()
LOGO = '/images/just-halloween-crafts-logo.png'
DEFAULT_OG = '/images/just-halloween-crafts-og.jpg'
ASSET_VER = '20261011'

NAV = [
    ('/', 'Home'),
    ('/blog', 'Blog'),
    ('/search/label/Papercraft', 'Paper Crafts'),
    ('/search/label/FeltandFabricCrafts', 'Fabric Crafts'),
    ('/search/label/CostumeAccessories', 'Costumes'),
    ('/search/label/FreePrintables', 'Free Printables'),
    ('/search/label/HalloweenFood', 'Food'),
    ('/p/about-marie', 'About'),
]
# Categories shown on the home page, in this order
HOME_CATS = ['CostumeAccessories', 'FreePrintables', 'Decorations', 'CraftsforKids', 'Papercraft',
             'FeltandFabricCrafts', 'HalloweenFood', 'Wreaths', 'PerlerBeads', 'Pumpkins', 'Witches', 'Quotations']
# Most visited tutorials according to Google Search Console (last 3 months)
POPULAR = ['/2016/03/luna-lovegood-quotes-books-harry-potter', '/2016/01/how-to-make-hood-for-cloak-or-cape',
           '/2015/07/how-to-sew-hood-onto-cape', '/2016/02/severus-snape-quotes-for-halloween',
           '/2015/08/how-to-sew-cloak-without-pattern', '/2015/05/free-printable-crow-silhouettes',
           '/2015/09/how-to-make-witch-spell-book-tutorial', '/2015/08/free-printable-butterfly-silhouette']

esc = html.escape


def load(name):
    with open(os.path.join(CONTENT, name), encoding='utf-8') as fh:
        return json.load(fh)


def write(rel, text):
    path = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(text)


def url_to_file(url):
    if url == '/':
        return 'index.html'
    return url.strip('/') + '.html'


def parse_date(s):
    if not s:
        return None
    s = s.strip()
    try:
        return dt.datetime.fromisoformat(s.replace('Z', '+00:00'))
    except ValueError:
        return dt.datetime.combine(dt.date.fromisoformat(s[:10]), dt.time(12), dt.timezone.utc)


def nice_date(d):
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def iso(d):
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d.isoformat(timespec='seconds')


def words_of(html_text):
    return len(BeautifulSoup(html_text, 'html.parser').get_text(' ', strip=True).split())


# ---------------------------------------------------------------- content load
posts = load('posts.json')
pages = load('pages.json')
labels = load('labels.json')
archives = load('archives.json')
overrides = load('overrides.json')

# new articles: _build/content/new/*.html with a JSON header in an HTML comment
NEW_DIR = os.path.join(CONTENT, 'new')
for fn in sorted(os.listdir(NEW_DIR)) if os.path.isdir(NEW_DIR) else []:
    if not fn.endswith('.html'):
        continue
    raw = open(os.path.join(NEW_DIR, fn), encoding='utf-8').read()
    m = re.match(r'\s*<!--\s*(\{.*?\})\s*-->\s*', raw, re.S)
    meta = json.loads(m.group(1))
    body = raw[m.end():].strip()
    meta.setdefault('modified', meta['published'])
    meta.update({'body': body, 'first_image': '', 'og_image': '', 'new': True,
                 'author': meta.get('author', NAME)})
    meta['label_names'] = [labels[s]['name'] for s in meta['labels'] if s in labels]
    posts.append(meta)

for p in posts + pages:
    ov = overrides.get(p['url'], {})
    for key in ('title', 'description', 'h1', 'modified', 'image_alt'):
        if key in ov:
            p[key] = ov[key]
    for old, new in ov.get('replace', []):
        if old not in p['body']:
            print('WARN replace target not found', p['url'], old[:60])
        p['body'] = p['body'].replace(old, new)
    if ov.get('prepend'):
        p['body'] = ov['prepend'] + '\n' + p['body']
    if ov.get('append'):
        p['body'] = p['body'] + '\n' + ov['append']
    if ov.get('add_labels'):
        for s in ov['add_labels']:
            if s not in p['labels']:
                p['labels'].append(s)
    p['words'] = words_of(p['body'])
    p['pub'] = parse_date(p.get('published')) or dt.datetime(2015, 1, 1, tzinfo=dt.timezone.utc)
    p['mod'] = parse_date(p.get('modified')) or p['pub']
    if p['mod'] < p['pub']:
        p['mod'] = p['pub']

COMMENT_RE = re.compile(r'[^.!?<>]*\b(?:in the comments? below|leave (?:any |a )?comments? below|comments? below|comment section below)[^.!?<>]*[.!?]\s*', re.I)


def strip_comment_prompts(body):
    """Comments were a Blogger feature and no longer exist, so drop sentences asking for them."""
    body = COMMENT_RE.sub('', body)
    return re.sub(r'<p>\s*</p>\s*', '', body)


for p in posts + pages:
    p['body'] = strip_comment_prompts(p['body'])
    p['words'] = words_of(p['body'])

# ---------------------------------------------------------------- entities (about / mentions)
def load_entities():
    """Rows of _build/entity-map.md: (name, [match words], wikipedia url or '')."""
    path = os.path.join(SRC, 'entity-map.md')
    out = []
    if not os.path.exists(path):
        return out
    for line in open(path, encoding='utf-8'):
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) != 3 or cells[0] in ('Entity', '---') or set(cells[0]) <= set('-: '):
            continue
        words = [w.strip().lower() for w in cells[1].split(',') if w.strip()]
        out.append((cells[0], words, cells[2]))
    return out


ENTITIES = load_entities()


def entity_ref(name, url):
    e = {'@type': 'Thing', 'name': name}
    if url:
        e['sameAs'] = url
    return e


def find_entities(post):
    """Primary entity = the one named first in the H1 (Halloween only when nothing else is);
    mentions = up to six other entities that appear in the article text, most frequent first."""
    def pattern(words):
        return re.compile(r"(?<![\w-])(?:" + '|'.join(re.escape(w) for w in words) + r")(?![\w-])", re.I)
    h1 = post['h1']
    text = BeautifulSoup(post['body'], 'html.parser').get_text(' ', strip=True)
    first, counts = [], []
    for name, words, url in ENTITIES:
        if not words:
            continue
        rx = pattern(words)
        m = rx.search(h1)
        if m:
            first.append((m.start(), name == 'Halloween', name, url))
        n = len(rx.findall(text))
        if n:
            counts.append((n, name, url))
    first.sort(key=lambda t: (t[1], t[0]))
    about = [entity_ref(n, u) for _, _, n, u in first[:1]]
    taken = {e['name'] for e in about}
    counts.sort(key=lambda t: -t[0])
    mentions = [entity_ref(n, u) for _, n, u in counts if n not in taken][:6]
    return about, mentions


for p in posts:
    p['about'], p['mentions'] = find_entities(p)

posts.sort(key=lambda x: x['pub'], reverse=True)
by_url = {p['url']: p for p in posts}
for sl, lab in labels.items():
    lab['posts'] = [p for p in posts if sl in p['labels']]


# ---------------------------------------------------------------- images
def img_size(path):
    if Image is None:
        return None
    fp = os.path.join(ROOT, path.lstrip('/'))
    try:
        with Image.open(fp) as im:
            return im.size
    except Exception:
        return None


def font(size, display=False):
    cand = [os.path.join(SRC, 'fonts', 'FontdinerSwanky.ttf')] if display else [os.path.join(SRC, 'fonts', 'Atkinson-700-normal.ttf')]
    cand += ['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
             '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf']
    for c in cand:
        if os.path.exists(c):
            return ImageFont.truetype(c, size)
    return ImageFont.load_default()


def wrap(draw, text, fnt, width):
    lines, cur = [], ''
    for w in text.split():
        t = (cur + ' ' + w).strip()
        if draw.textlength(t, font=fnt) <= width:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def make_card(post, W=1200, H=630, folder='cards', ext='jpg'):
    """Title card for new articles (no stock photos): 1200x630 for social sharing,
    600x400 for listing thumbnails. Drawn in the site colors."""
    rel = f"/images/{folder}/{post['url'].strip('/').replace('/', '-')}.{ext}"
    out = os.path.join(ROOT, rel.lstrip('/'))
    if os.path.exists(out) or Image is None:
        return rel
    os.makedirs(os.path.dirname(out), exist_ok=True)
    k = W / 1200
    im = Image.new('RGB', (W, H), (43, 27, 61))
    d = ImageDraw.Draw(im)
    # paper-cut moon, bats and hills
    mx = W - 340 * k
    d.ellipse((mx, -120 * k, mx + 460 * k, 340 * k), fill=(247, 197, 72))
    d.ellipse((mx - 60 * k, -150 * k, mx + 360 * k, 270 * k), fill=(43, 27, 61))
    base = H - 70 * k
    hills = [(0, base), (W * .15, base - 60 * k), (W * .32, base - 15 * k), (W * .5, base - 70 * k), (W * .68, base - 20 * k),
             (W * .87, base - 65 * k), (W, base - 30 * k), (W, H), (0, H)]
    d.polygon(hills, fill=(232, 113, 28))
    for bx, by, sc in ((W - 270 * k, 140 * k, 1.0), (W - 160 * k, 230 * k, 0.7), (W - 350 * k, 260 * k, 0.55)):
        pts = [(0, 0), (-30, -14), (-55, -4), (-42, 4), (-58, 14), (-30, 10), (0, 22), (30, 10), (58, 14), (42, 4), (55, -4), (30, -14)]
        d.polygon([(bx + x * sc * 1.6 * k, by + y * sc * 1.6 * k) for x, y in pts], fill=(24, 15, 34))
    margin = 70 * k if W >= 1000 else 34
    label = (post.get('label_names') or ['Halloween craft'])[0]
    d.text((margin, margin), label, font=font(int(30 * max(k, .75))), fill=(247, 197, 72))
    title = post['h1']
    width = W - margin * 2 - (300 * k if W >= 1000 else 40)
    size = int(76 * k) if W >= 1000 else 46
    while size > 22:
        ft = font(size)
        lines = wrap(d, title, ft, width)
        if len(lines) <= 4 and all(d.textlength(l, font=ft) <= width for l in lines):
            break
        size -= 2
    y = margin + (60 * k if W >= 1000 else 42)
    for ln in lines:
        d.text((margin, y), ln, font=ft, fill=(255, 255, 255))
        y += int(size * 1.18)
    d.text((margin, H - 55 * k if W >= 1000 else H - 44), NAME, font=font(int(40 * k) if W >= 1000 else 24, display=True), fill=(43, 27, 61))
    if ext == 'webp':
        im.save(out, 'WEBP', quality=80, method=6)
    else:
        im.save(out, 'JPEG', quality=86, optimize=True, progressive=True)
    return rel


def make_thumb(post):
    src = post.get('og_image') or post.get('first_image') or post.get('card')
    rel = f"/images/thumbs/{post['url'].strip('/').replace('/', '-')}.webp"
    out = os.path.join(ROOT, rel.lstrip('/'))
    if Image is None or not src:
        return src
    if not os.path.exists(out):
        try:
            with Image.open(os.path.join(ROOT, src.lstrip('/'))) as im:
                im = im.convert('RGB')
                tw, th = 600, 400
                r = max(tw / im.width, th / im.height)
                im = im.resize((max(tw, round(im.width * r)), max(th, round(im.height * r))), Image.LANCZOS)
                left = (im.width - tw) // 2
                top = max(0, (im.height - th) // 3)
                im = im.crop((left, top, left + tw, top + th))
                os.makedirs(os.path.dirname(out), exist_ok=True)
                im.save(out, 'WEBP', quality=74, method=6)
        except Exception as e:
            print('thumb failed', post['url'], e)
            return src
    return rel


for p in posts:
    if p.get('new'):
        p['card'] = make_card(p)
        p['og_image'] = p['card']
        p['thumb'] = make_card(p, 600, 400, 'thumbs', 'webp')
    else:
        p['thumb'] = make_thumb(p)
    p['image'] = p.get('og_image') or p.get('first_image') or DEFAULT_OG


# ---------------------------------------------------------------- html parts
def head(title, desc, url, *, og_image=DEFAULT_OG, og_type='website', robots='index, follow, max-image-preview:large',
         schema=None, extra=''):
    canonical = SITE + url
    img_abs = SITE + og_image if og_image.startswith('/') else og_image
    sz = img_size(og_image) if og_image.startswith('/') else None
    tags = [
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f'<title>{esc(title)}</title>',
        f'<meta name="description" content="{esc(desc)}">',
        f'<meta name="robots" content="{robots}">',
        f'<link rel="canonical" href="{canonical}">',
        f'<link rel="preload" href="/assets/fonts/atkinson-hyperlegible-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>',
        f'<link rel="preload" href="/assets/fonts/fontdiner-swanky.woff2" as="font" type="font/woff2" crossorigin>',
        f'<link rel="stylesheet" href="/assets/css/style.css?v={ASSET_VER}">',
        '<link rel="icon" href="/favicon.ico" sizes="any">',
        '<link rel="icon" href="/icon.svg" type="image/svg+xml">',
        '<link rel="apple-touch-icon" href="/apple-touch-icon.png">',
        '<link rel="manifest" href="/site.webmanifest">',
        '<meta name="theme-color" content="#2b1b3d">',
        f'<link rel="alternate" type="application/rss+xml" title="{NAME}" href="{SITE}/feed.xml">',
        '<meta property="og:locale" content="en_US">',
        f'<meta property="og:site_name" content="{NAME}">',
        f'<meta property="og:type" content="{og_type}">',
        f'<meta property="og:url" content="{canonical}">',
        f'<meta property="og:title" content="{esc(title)}">',
        f'<meta property="og:description" content="{esc(desc)}">',
        f'<meta property="og:image" content="{img_abs}">',
    ]
    if sz:
        tags += [f'<meta property="og:image:width" content="{sz[0]}">', f'<meta property="og:image:height" content="{sz[1]}">']
    tags += [
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{esc(title)}">',
        f'<meta name="twitter:description" content="{esc(desc)}">',
        f'<meta name="twitter:image" content="{img_abs}">',
    ]
    if extra:
        tags.append(extra)
    if schema:
        tags.append('<script type="application/ld+json">' + json.dumps(schema, ensure_ascii=False, indent=1).replace('</', '<\\/') + '</script>')
    tags.append(f'<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>')
    tags.append("<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}"
                f"gtag('js',new Date());gtag('config','{GA_ID}');</script>")
    return '\n'.join(tags)


def header(current):
    links = []
    for href, label in NAV:
        cur = ' aria-current="page"' if href == current else ''
        links.append(f'<li><a href="{href}"{cur}>{label}</a></li>')
    return f'''<a class="skip" href="#main">Skip to main content</a>
<header class="site-header">
 <div class="wrap header-inner">
  <a class="wordmark" href="/">Just Halloween Crafts</a>
  <p class="tagline">Handmade Halloween ideas since 2015</p>
 </div>
 <nav class="site-nav" aria-label="Main">
  <ul class="wrap">{''.join(links)}</ul>
 </nav>
</header>'''


def footer():
    cats = ''.join(f'<li><a href="{labels[s]["url"]}">{esc(labels[s]["name"])}</a></li>' for s in HOME_CATS if s in labels)
    return f'''<footer class="site-footer">
 <div class="wrap footer-grid">
  <section>
   <p class="footer-mark">Just Halloween Crafts</p>
   <p>Step-by-step Halloween craft tutorials, costume accessories, free printables and party food ideas to make at home in the run up to October 31st.</p>
  </section>
  <section>
   <h2>Browse by category</h2>
   <ul class="footer-cats">{cats}</ul>
  </section>
  <section>
   <h2>About this site</h2>
   <ul>
    <li><a href="/p/about-marie">About Marie</a></li>
    <li><a href="/blog">All articles</a></li>
    <li><a href="/p/privacy-policy">Privacy and cookies policy</a></li>
    <li><a href="/p/ftc-disclosure">Affiliate disclosure</a></li>
    <li><a href="/feed.xml">RSS feed</a></li>
   </ul>
  </section>
 </div>
 <div class="wrap footer-legal">
  <p>Some links on this site are affiliate links. If you buy through them, the site may earn a small commission at no extra cost to you. As an Amazon Associate the site earns from qualifying purchases. <a href="/p/ftc-disclosure">Read the full disclosure</a>.</p>
  <p>&copy; 2015&ndash;{TODAY.year} JustHalloweenCrafts.com. Photos are the author's own unless credited.</p>
 </div>
</footer>
<div class="cookie" id="cookie" hidden>
 <p>This site uses cookies for analytics and affiliate links. <a href="/p/privacy-policy">Learn more</a></p>
 <button type="button" id="cookie-ok">OK</button>
</div>
<script src="/assets/js/site.js?v={ASSET_VER}" defer></script>'''


def page(title, desc, url, body, current='', **kw):
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
{head(title, desc, url, **kw)}
</head>
<body>
{header(current)}
<main id="main" class="wrap">
{body}
</main>
{footer()}
</body>
</html>
'''


def breadcrumb_html(items):
    parts = []
    for i, (name, url) in enumerate(items):
        if i == len(items) - 1:
            parts.append(f'<li aria-current="page">{esc(name)}</li>')
        else:
            parts.append(f'<li><a href="{url}">{esc(name)}</a></li>')
    return f'<nav class="crumbs" aria-label="Breadcrumb"><ol>{"".join(parts)}</ol></nav>'


def breadcrumb_schema(items):
    return {'@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': i + 1, 'name': n, 'item': SITE + u} for i, (n, u) in enumerate(items)]}


def org_schema():
    return {'@type': 'Organization', '@id': SITE + '/#org', 'name': NAME, 'url': SITE + '/',
            'logo': {'@type': 'ImageObject', 'url': SITE + LOGO, 'width': 600, 'height': 60}}


def card(p, heading='h3', eager=False):
    thumb = p.get('thumb') or p['image']
    loading = 'eager" fetchpriority="high' if eager else 'lazy'
    label = p['label_names'][0] if p.get('label_names') else ''
    return f'''<article class="card">
 <a class="card-img" href="{p["url"]}" tabindex="-1" aria-hidden="true"><img src="{thumb}" alt="{esc(p["h1"])}" width="600" height="400" loading="{loading}" decoding="async"></a>
 <div class="card-body">
  {f'<p class="card-cat">{esc(label)}</p>' if label else ''}
  <{heading} class="card-title"><a href="{p["url"]}">{esc(p["h1"])}</a></{heading}>
  <p class="card-text">{esc(p["description"])}</p>
 </div>
</article>'''


def grid(items, heading='h3', eager_first=False):
    return '<div class="grid">' + '\n'.join(card(p, heading, eager_first and i < 2) for i, p in enumerate(items)) + '</div>'


def primary_label(p):
    order = ['CostumeAccessories', 'FreePrintables', 'HalloweenFood', 'Quotations', 'PerlerBeads', 'Wreaths',
             'Pumpkins', 'CraftKits', 'CraftsforKids', 'FeltandFabricCrafts', 'Papercraft', 'Decorations', 'CraftTutorial']
    for o in order:
        if o in p['labels']:
            return o
    return p['labels'][0] if p['labels'] else None


def related(p, n=3):
    scores = []
    for q in posts:
        if q is p:
            continue
        shared = len(set(q['labels']) & set(p['labels']))
        if shared:
            scores.append((shared, q['pub'], q))
    scores.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [x[2] for x in scores[:n]]


# ---------------------------------------------------------------- post pages
def build_post(p):
    pl = primary_label(p)
    crumbs = [('Home', '/')]
    if pl and pl in labels:
        crumbs.append((labels[pl]['name'], labels[pl]['url']))
    crumbs.append((p['h1'], p['url']))
    updated = p['mod'].date() > p['pub'].date() + dt.timedelta(days=30)
    meta = f'By <span class="author">{esc(p["author"])}</span>. Published <time datetime="{p["pub"].date()}">{nice_date(p["pub"])}</time>'
    if updated:
        meta += f'. Updated <time datetime="{p["mod"].date()}">{nice_date(p["mod"])}</time>'
    hero = ''
    if p.get('new') and p.get('card'):
        alt = p.get('image_alt') or p['h1']
        hero = f'<figure class="post-hero"><img src="{p["card"]}" alt="{esc(alt)}" width="1200" height="630" fetchpriority="high" decoding="async"></figure>'
    body = p['body']
    # first in-body image loads eagerly (likely LCP)
    body = body.replace('loading="lazy"', 'fetchpriority="high"', 1) if not hero else body
    has_aff = 'sponsored' in body
    disclosure = ('<p class="disclosure">This post contains affiliate links. If you buy through them, the site may earn a small commission at no extra cost to you. '
                  '<a href="/p/ftc-disclosure">Disclosure</a>.</p>') if has_aff else ''
    tags = ''.join(f'<li><a href="{labels[s]["url"]}">{esc(labels[s]["name"])}</a></li>' for s in p['labels'] if s in labels)
    rel = related(p)
    rel_html = f'<section class="related" aria-labelledby="rel-h"><h2 id="rel-h">You might also like</h2>{grid(rel)}</section>' if rel else ''
    author_box = ('<aside class="author-box"><p><strong>About the author.</strong> Marie (M. W. Johnstone) is a freelance writer and lifelong crafter who started Just Halloween Crafts in 2015 to share '
                  'her Halloween tutorials, printables and party ideas. <a href="/p/about-marie">More about Marie</a>.</p></aside>') if 'Johnstone' in p['author'] else \
        ('<aside class="author-box"><p><strong>About this guide.</strong> Written by the Just Halloween Crafts team for families and grown-up crafters who want simple, budget-friendly Halloween projects. '
         '<a href="/p/about-marie">About the site</a>.</p></aside>')
    article = f'''{breadcrumb_html(crumbs)}
<article class="post">
 <header class="post-header">
  <h1>{esc(p["h1"])}</h1>
  <p class="post-meta">{meta}</p>
 </header>
 {hero}
 {disclosure}
 <div class="post-body">
{body}
 </div>
 <footer class="post-footer">
  {f'<ul class="tags" aria-label="Categories">{tags}</ul>' if tags else ''}
  {author_box}
 </footer>
</article>
{rel_html}'''
    image_abs = SITE + p['image']
    schema = {'@context': 'https://schema.org', '@graph': [
        {'@type': 'BlogPosting', '@id': SITE + p['url'] + '#article', 'mainEntityOfPage': SITE + p['url'],
         'headline': p['h1'][:110], 'description': p['description'], 'image': [image_abs],
         'datePublished': iso(p['pub']), 'dateModified': iso(p['mod']), 'wordCount': p['words'],
         'inLanguage': 'en',
         'author': ({'@type': 'Person', 'name': p['author'], 'url': SITE + '/p/about-marie'} if 'Johnstone' in p['author']
                    else {'@type': 'Organization', 'name': NAME, 'url': SITE + '/'}),
         'publisher': {'@id': SITE + '/#org'},
         'articleSection': p['label_names'][:3] if p.get('label_names') else [],
         **({'about': p['about']} if p.get('about') else {}),
         **({'mentions': p['mentions']} if p.get('mentions') else {})},
        breadcrumb_schema(crumbs), org_schema()]}
    extra = (f'<meta property="article:published_time" content="{iso(p["pub"])}">\n'
             f'<meta property="article:modified_time" content="{iso(p["mod"])}">')
    return page(p['title'], p['description'], p['url'], article, og_image=p['image'], og_type='article',
                schema=schema, extra=extra)


# ---------------------------------------------------------------- list pages
def itemlist(items):
    return {'@type': 'ItemList', 'itemListElement': [
        {'@type': 'ListItem', 'position': i + 1, 'url': SITE + p['url'], 'name': p['h1']} for i, p in enumerate(items)]}


def build_label(sl):
    lab = labels[sl]
    crumbs = [('Home', '/'), ('Blog', '/blog'), (lab['h1'], lab['url'])]
    intro = ''.join(f'<p>{esc(t)}</p>' for t in lab['intro'])
    others = ''.join(f'<li><a href="{labels[s]["url"]}">{esc(labels[s]["name"])}</a> <span>{len(labels[s]["posts"])}</span></li>'
                     for s in sorted(labels, key=lambda s: labels[s]['name']) if s != sl and labels[s]['posts'])
    body = f'''{breadcrumb_html(crumbs)}
<header class="list-header">
 <h1>{esc(lab["h1"])}</h1>
 {intro}
 <p class="count">{len(lab["posts"])} {'article' if len(lab["posts"]) == 1 else 'articles'} in this category</p>
</header>
<h2 class="visually-hidden">Articles</h2>
{grid(lab["posts"], eager_first=True)}
<section class="cat-list" aria-labelledby="cat-h"><h2 id="cat-h">More categories</h2><ul>{others}</ul></section>'''
    schema = {'@context': 'https://schema.org', '@graph': [
        {'@type': 'CollectionPage', '@id': SITE + lab['url'], 'url': SITE + lab['url'], 'name': lab['h1'],
         'description': lab['description'], 'isPartOf': {'@type': 'WebSite', '@id': SITE + '/#website'},
         'mainEntity': itemlist(lab['posts'])},
        breadcrumb_schema(crumbs)]}
    current = lab['url'] if lab['url'] in dict(NAV) else ''
    robots = 'noindex, follow' if is_thin_label(sl) else 'index, follow, max-image-preview:large'
    return page(lab['title'], lab['description'], lab['url'], body, current=current, schema=schema, robots=robots)


def is_thin_label(sl):
    """Categories with only one or two articles are thin listing pages: keep them for visitors
    but ask search engines not to index them (links are still followed)."""
    return len(labels[sl]['posts']) < 3


def build_archive(url):
    y, m = url.strip('/').split('/')
    month = dt.date(int(y), int(m), 1)
    items = [p for p in posts if p['pub'].year == month.year and p['pub'].month == month.month]
    name = f"{month.strftime('%B')} {month.year}"
    crumbs = [('Home', '/'), ('Blog', '/blog'), (f'{name} archive', url)]
    lis = ''.join(f'<li><a href="{p["url"]}">{esc(p["h1"])}</a> <time datetime="{p["pub"].date()}">{nice_date(p["pub"])}</time></li>' for p in items)
    body = f'''{breadcrumb_html(crumbs)}
<header class="list-header"><h1>Halloween crafts published in {name}</h1>
<p>{len(items)} {'article was' if len(items) == 1 else 'articles were'} published on Just Halloween Crafts in {name}. Browse the <a href="/blog">full blog</a> for every tutorial sorted by category.</p></header>
<ul class="archive-list">{lis}</ul>'''
    schema = {'@context': 'https://schema.org', '@graph': [
        {'@type': 'CollectionPage', '@id': SITE + url, 'url': SITE + url, 'name': f'{name} archive', 'mainEntity': itemlist(items)},
        breadcrumb_schema(crumbs)]}
    return page(f'{name} Archive | {NAME}', f'Halloween craft articles published on {NAME} in {name}.', url, body,
                robots='noindex, follow', schema=schema)


def build_blog():
    crumbs = [('Home', '/'), ('Blog', '/blog')]
    cats = ''.join(f'<li><a href="{labels[s]["url"]}">{esc(labels[s]["name"])}</a> <span>{len(labels[s]["posts"])}</span></li>'
                   for s in sorted(labels, key=lambda s: labels[s]['name']) if labels[s]['posts'])
    months = {}
    for p in posts:
        months.setdefault((p['pub'].year, p['pub'].month), 0)
        months[(p['pub'].year, p['pub'].month)] += 1
    arch = ''.join(f'<li><a href="/{y}/{m:02d}">{dt.date(y, m, 1).strftime("%B %Y")}</a> <span>{n}</span></li>' for (y, m), n in sorted(months.items(), reverse=True))
    body = f'''{breadcrumb_html(crumbs)}
<header class="list-header">
 <h1>Halloween Craft Blog: All Articles</h1>
 <p>Every tutorial, free printable and party food idea on Just Halloween Crafts, newest first. Looking for something specific? Jump straight to a category below.</p>
</header>
<section class="cat-list" aria-labelledby="cats-h"><h2 id="cats-h">Categories</h2><ul>{cats}</ul></section>
<h2 class="section-title">Latest articles</h2>
{grid(posts, eager_first=True)}
<section class="cat-list" aria-labelledby="arch-h"><h2 id="arch-h">Archive by month</h2><ul>{arch}</ul></section>'''
    schema = {'@context': 'https://schema.org', '@graph': [
        {'@type': 'CollectionPage', '@id': SITE + '/blog', 'url': SITE + '/blog', 'name': 'Halloween Craft Blog: All Articles',
         'isPartOf': {'@type': 'WebSite', '@id': SITE + '/#website'}, 'mainEntity': itemlist(posts)},
        breadcrumb_schema(crumbs)]}
    return page('Halloween Craft Blog: All Articles | Just Halloween Crafts',
                'Every Halloween craft tutorial, free printable and party food idea on Just Halloween Crafts, newest first and sorted by category.',
                '/blog', body, current='/blog', schema=schema)


def build_home():
    newest = posts[:6]
    popular = [by_url[u] for u in POPULAR if u in by_url]
    cats = ''.join(f'''<li><a href="{labels[s]["url"]}"><span class="cat-name">{esc(labels[s]["name"])}</span>
 <span class="cat-count">{len(labels[s]["posts"])} articles</span></a></li>''' for s in HOME_CATS if s in labels)
    older = [p for p in posts if p not in newest and p not in popular][:9]
    body = f'''<section class="hero" aria-labelledby="hero-h">
 <div class="hero-text">
  <h1 id="hero-h">Halloween crafts, costumes and printables to make at home</h1>
  <p>Step-by-step tutorials for cloaks and hoods, spell books, wreaths and paper decorations, plus free printables and spooky party food. Most projects use everyday supplies and suit both grown-up crafters and families.</p>
  <p class="hero-links"><a class="btn" href="/blog">Browse all {len(posts)} articles</a> <a class="btn btn-ghost" href="/search/label/FreePrintables">Free printables</a></p>
 </div>
 <div class="countdown" id="countdown" aria-live="polite">
  <span class="count-num" id="count-num">&nbsp;</span>
  <span class="count-label" id="count-label">days until Halloween</span>
 </div>
</section>
<section aria-labelledby="new-h">
 <h2 id="new-h" class="section-title">New this season</h2>
 {grid(newest, eager_first=True)}
</section>
<section aria-labelledby="pop-h">
 <h2 id="pop-h" class="section-title">Reader favorites</h2>
 {grid(popular)}
</section>
<section class="cats" aria-labelledby="cat-h">
 <h2 id="cat-h" class="section-title">Find a project by category</h2>
 <ul class="cat-tiles">{cats}</ul>
</section>
<section aria-labelledby="more-h">
 <h2 id="more-h" class="section-title">More from the archive</h2>
 {grid(older)}
 <p class="more"><a class="btn" href="/blog">See every article</a></p>
</section>'''
    schema = {'@context': 'https://schema.org', '@graph': [
        {'@type': 'WebSite', '@id': SITE + '/#website', 'url': SITE + '/', 'name': NAME,
         'description': TAGLINE, 'inLanguage': 'en', 'publisher': {'@id': SITE + '/#org'}},
        org_schema()]}
    return page('Just Halloween Crafts | DIY Halloween Craft Ideas',
                'Halloween craft ideas and DIY tutorials: costume cloaks and hoods, decorations, free printables, wreaths, Perler bead patterns and spooky party food.',
                '/', body, current='/', schema=schema)


def build_static(p):
    crumbs = [('Home', '/'), (p['h1'], p['url'])]
    body = f'''{breadcrumb_html(crumbs)}
<article class="post page">
 <header class="post-header"><h1>{esc(p["h1"])}</h1></header>
 <div class="post-body">
{p["body"]}
 </div>
</article>'''
    typ = 'AboutPage' if 'about' in p['url'] else 'WebPage'
    schema = {'@context': 'https://schema.org', '@graph': [
        {'@type': typ, '@id': SITE + p['url'], 'url': SITE + p['url'], 'name': p['h1'], 'description': p['description']},
        breadcrumb_schema(crumbs)]}
    current = p['url'] if p['url'] in dict(NAV) else ''
    return page(p['title'], p['description'], p['url'], body, current=current, schema=schema)


def build_404():
    cats = ''.join(f'<li><a href="{labels[s]["url"]}">{esc(labels[s]["name"])}</a></li>' for s in HOME_CATS if s in labels)
    body = f'''<header class="list-header"><h1>We could not find that page</h1>
<p>The link may be old, or the page may have moved when the site was updated. Every tutorial is still here: try the <a href="/blog">full list of articles</a>, go back to the <a href="/">home page</a>, or pick a category.</p></header>
<section class="cat-list"><h2>Popular categories</h2><ul>{cats}</ul></section>
<h2 class="section-title">Reader favorites</h2>
{grid([by_url[u] for u in POPULAR[:6] if u in by_url])}'''
    return page(f'Page not found | {NAME}', 'The page you were looking for could not be found.', '/404', body,
                robots='noindex, follow')


# ---------------------------------------------------------------- feeds etc.
def build_sitemap(entries):
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">']
    for url, lastmod, images in entries:
        out.append(' <url>')
        out.append(f'  <loc>{SITE}{url}</loc>')
        out.append(f'  <lastmod>{lastmod}</lastmod>')
        for im in images[:20]:
            out.append(f'  <image:image><image:loc>{esc(SITE + im if im.startswith("/") else im)}</image:loc></image:image>')
        out.append(' </url>')
    out.append('</urlset>')
    return '\n'.join(out) + '\n'


def build_feed():
    items = []
    for p in posts[:25]:
        items.append(f'''<item>
 <title>{esc(p["h1"])}</title>
 <link>{SITE}{p["url"]}</link>
 <guid isPermaLink="true">{SITE}{p["url"]}</guid>
 <pubDate>{format_datetime(p["pub"])}</pubDate>
 <description>{esc(p["description"])}</description>
</item>''')
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
 <title>{NAME}</title>
 <link>{SITE}/</link>
 <description>{TAGLINE}</description>
 <language>en</language>
 <atom:link href="{SITE}/feed.xml" rel="self" type="application/rss+xml"/>
{chr(10).join(items)}
</channel>
</rss>
'''


def body_images(p):
    s = BeautifulSoup(p['body'], 'html.parser')
    out = []
    if p.get('card'):
        out.append(p['card'])
    for im in s.find_all('img'):
        src = im.get('src', '')
        if src.startswith('/images') or src.startswith('/img'):
            if src not in out:
                out.append(src)
    return out


def main():
    # clean previously generated html (never touches images or _build)
    for d in [str(y) for y in range(2015, 2031)] + ['search', 'p']:
        path = os.path.join(ROOT, d)
        if os.path.isdir(path):
            for r, ds, fs in os.walk(path):
                for f in fs:
                    if f.endswith('.html'):
                        os.remove(os.path.join(r, f))
    for p in posts:
        write(url_to_file(p['url']), build_post(p))
    for sl in labels:
        if labels[sl]['posts']:
            write(url_to_file(labels[sl]['url']), build_label(sl))
    months = sorted({f"/{p['pub'].year}/{p['pub'].month:02d}" for p in posts})
    for u in months:
        write(url_to_file(u), build_archive(u))
    for p in pages:
        write(url_to_file(p['url']), build_static(p))
    write('blog.html', build_blog())
    write('index.html', build_home())
    write('404.html', build_404())
    write('feed.xml', build_feed())
    newest = max(p['mod'] for p in posts).date().isoformat()
    entries = [('/', newest, [DEFAULT_OG]), ('/blog', newest, [])]
    for p in posts:
        entries.append((p['url'], p['mod'].date().isoformat(), body_images(p)))
    for sl in sorted(labels):
        if labels[sl]['posts'] and not is_thin_label(sl):
            entries.append((labels[sl]['url'], max(q['mod'] for q in labels[sl]['posts']).date().isoformat(), []))
    for p in pages:
        entries.append((p['url'], p['mod'].date().isoformat(), []))
    write('sitemap.xml', build_sitemap(entries))
    stats = {'posts': len(posts), 'new_posts': sum(1 for p in posts if p.get('new')), 'labels': sum(1 for s in labels if labels[s]['posts']),
             'archives': len(months), 'sitemap_urls': len(entries)}
    print(json.dumps(stats))


if __name__ == '__main__':
    main()
