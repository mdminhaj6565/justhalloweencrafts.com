"""ONE-TIME MIGRATION SCRIPT (kept for reference; not needed for normal builds).
It was run once on 11 Oct 2026 against a full copy of the old Blogger mirror, which is
not part of this repository.

Turns the mirrored Blogger HTML into clean content JSON.
Input : raw/pages/*.html, raw/files/** (original images), data_site.json
Output: _build/content/posts.json, labels.json, pages.json, extract_log.json
"""
import json, re, os
from bs4 import BeautifulSoup, NavigableString, Tag
from urllib.parse import urljoin, urlparse, unquote
from PIL import Image

W = os.environ.get('MIGRATION_DIR', '/home/claude/work')
SITE = 'https://www.justhalloweencrafts.com'
FILES = f'{W}/raw/files'
DEAD_DOMAINS = {'craftymarie.com', 'halloweenangel.com'}
DEAD_YT = {'E2Nd_II2Iz4', 'VSubfrlEyl4', 'uvPygS4AHlA', 'ISs6KuGgeB0', 'ry8YZjRY5TU', 'iN5h_S6x75Q'}
AFFIL = re.compile(r'(amazon\.|amzn\.|awin1\.com|zazzle\.com|etsy\.com)', re.I)
log = {'unwrapped_dead_links': [], 'removed_videos': [], 'missing_images': [], 'affiliate_links': 0,
       'external_links': 0, 'product_boxes': 0, 'lazy_images': 0, 'removed_updated_notes': 0}

d = json.load(open(f'{W}/data_site.json'))
dims_cache = {}

def img_dims(path):
    if path in dims_cache: return dims_cache[path]
    fp = FILES + path
    try:
        with Image.open(fp) as im: dims_cache[path] = im.size
    except Exception:
        dims_cache[path] = None
    return dims_cache[path]

def norm_internal(path):
    path = unquote(path)
    path = re.sub(r'\.html?$', '', path)
    path = re.sub(r'(_m-1)?(-spref-pi|_spref-pi)?(_m-1)?$', '', path)
    if path.startswith('/search/label/'):
        path = path.replace(' ', '')
    if path in ('/index', ''):
        path = '/'
    if len(path) > 1:
        path = path.rstrip('/')
    return path

def cdn_for(path):
    if path.startswith('/images/I/') or path.startswith('/images/G/'):
        return 'https://m.media-amazon.com' + path
    if re.match(r'^/\d+/', path):
        return 'https://i.etsystatic.com' + path
    return None

def is_img_path(p):
    return bool(re.search(r'\.(jpe?g|png|gif|webp)$', p, re.I))

def _sib(node, attr):
    x = getattr(node, attr)
    while x is not None and isinstance(x, NavigableString) and not x.strip():
        x = getattr(x, attr)
    return x

def drop_or_unwrap(a):
    """A dead link that stands on its own line (link lists, related boxes) is removed with its
    line break; a dead link inside running text keeps its words but loses the link."""
    prev, nxt = _sib(a, 'previous_sibling'), _sib(a, 'next_sibling')
    def is_break(x):
        return x is None or (isinstance(x, Tag) and x.name == 'br')
    own_line = is_break(prev) and is_break(nxt)
    parent_li = a.parent if a.parent is not None and a.parent.name == 'li' and a.parent.get_text(strip=True) == a.get_text(strip=True) else None
    if parent_li is not None:
        parent_li.decompose(); return
    if own_line and a.find('img') is None:
        if isinstance(nxt, Tag) and nxt.name == 'br':
            nxt.decompose()
        elif isinstance(prev, Tag) and prev.name == 'br':
            prev.decompose()
        a.decompose(); return
    a.unwrap()

def clean_body(html, page_url):
    s = BeautifulSoup(html, 'html.parser')
    base = SITE + page_url
    # remove "more" anchors and "Page Last Updated" notes
    for a in s.find_all('a', attrs={'name': True}):
        if not a.get('href'): a.decompose()
    for t in s.find_all('time'):
        em = t.find_parent(['em', 'i', 'span', 'p', 'div'])
        if em and 'Updated' in em.get_text():
            nxt = em.next_sibling
            em.decompose(); log['removed_updated_notes'] += 1
    # iframes (YouTube)
    for f in s.find_all('iframe'):
        src = f.get('src', '')
        m = re.search(r'youtube\.com/embed/([\w-]{11})', src)
        if m and m.group(1) not in DEAD_YT:
            vid = m.group(1)
            div = s.new_tag('div', attrs={'class': 'yt', 'data-id': vid})
            btn = s.new_tag('button', attrs={'type': 'button', 'class': 'yt-play', 'aria-label': 'Play video'})
            img = s.new_tag('img', attrs={'src': f'https://i.ytimg.com/vi/{vid}/hqdefault.jpg', 'alt': 'Video thumbnail',
                                         'width': '480', 'height': '360', 'loading': 'lazy', 'decoding': 'async'})
            btn.append(img)
            div.append(btn)
            f.replace_with(div)
        else:
            log['removed_videos'].append([page_url, src]); f.decompose()
    # product boxes
    for span in s.find_all('span', class_='prthmb'):
        a = span.find_parent('a')
        if not a or a.get('data-done'): continue
        box = a.parent
        if box is None or box.parent is None: continue
        cards = []
        for pa in box.find_all('a'):
            th = pa.find('span', class_='prthmb')
            if not th: continue
            im = th.find('img')
            title = pa.get('title') or (im.get('alt') if im else '') or 'View product'
            src = urljoin(base, im.get('src')) if im else ''
            p = unquote(urlparse(src).path)
            cdn = cdn_for(p) or src
            cards.append((pa.get('href'), title, cdn))
            pa['data-done'] = '1'
        if not cards: continue
        newbox = s.new_tag('div', attrs={'class': 'products'})
        for href, title, img in cards:
            store = 'Amazon' if 'amazon' in (href or '') else ('Etsy' if 'etsy' in (href or '') else 'store')
            ca = s.new_tag('a', attrs={'class': 'product', 'href': href, 'rel': 'sponsored nofollow noopener', 'target': '_blank'})
            ci = s.new_tag('img', attrs={'src': img, 'alt': title, 'loading': 'lazy', 'decoding': 'async', 'width': '250', 'height': '250'})
            sp = s.new_tag('span', attrs={'class': 'product-name'}); sp.string = title
            bt = s.new_tag('span', attrs={'class': 'product-cta'}); bt.string = f'View on {store}'
            ca.append(ci); ca.append(sp); ca.append(bt)
            newbox.append(ca)
        box.replace_with(newbox)
        log['product_boxes'] += 1
    # links
    for a in s.find_all('a', href=True):
        if 'product' in (a.get('class') or []): 
            log['affiliate_links'] += 1
            continue
        href = a['href'].strip()
        if href.startswith(('mailto:', 'tel:', 'javascript:', '#')):
            continue
        absu = urljoin(base, href.replace('&amp;', '&'))
        pu = urlparse(absu)
        host = pu.netloc.lower().replace('www.', '')
        if host == 'justhalloweencrafts.com' or host == '':
            p = unquote(pu.path)
            if is_img_path(p):
                # link to a (larger) image: keep only if we have the file
                if os.path.exists(FILES + p):
                    a['href'] = p
                else:
                    log.setdefault('missing_link_images', []).append([page_url, p])
                    a.unwrap(); continue
            else:
                a['href'] = norm_internal(p) + (('#' + pu.fragment) if pu.fragment else '')
            for k in ('target', 'rel', 'imageanchor', 'style'):
                a.attrs.pop(k, None)
            continue
        if any(host == dd or host.endswith('.' + dd) for dd in DEAD_DOMAINS):
            log['unwrapped_dead_links'].append([page_url, absu, a.get_text(' ', strip=True)[:60]])
            drop_or_unwrap(a); continue
        m = re.search(r'(?:v=|youtu\.be/)([\w-]{11})', absu)
        if 'youtube' in host or 'youtu.be' in host:
            if m and m.group(1) in DEAD_YT:
                log['unwrapped_dead_links'].append([page_url, absu, a.get_text(' ', strip=True)[:60]])
                drop_or_unwrap(a); continue
        a['href'] = absu.replace('http://www.flickr.com', 'https://www.flickr.com').replace('http://pixabay.com', 'https://pixabay.com')
        if AFFIL.search(host):
            a['rel'] = 'sponsored nofollow noopener'; log['affiliate_links'] += 1
        else:
            a['rel'] = 'noopener'; log['external_links'] += 1
        a['target'] = '_blank'
        a.attrs.pop('style', None)
    # images
    for im in s.find_all('img'):
        if im.find_parent(class_='products') or im.find_parent(class_='yt'): continue
        src = im.get('src', '')
        absu = urljoin(base, src)
        p = unquote(urlparse(absu).path)
        cdn = cdn_for(p)
        w0 = im.get('width')
        alt = (im.get('alt') or im.get('title') or '').strip()
        for k in list(im.attrs):
            if k not in ('alt',): del im[k]
        if cdn:
            im['src'] = cdn
            if 'buy1' in p:  # Amazon buy button gif -> drop
                im.decompose(); continue
        elif os.path.exists(FILES + p):
            im['src'] = p
            dm = img_dims(p)
            if dm:
                w, h = dm
                try:
                    w0 = int(str(w0).replace('px', '')) if w0 else None
                except ValueError:
                    w0 = None
                if w0 and w0 < w:
                    h = round(h * w0 / w); w = w0
                im['width'] = str(w); im['height'] = str(h)
        else:
            log['missing_images'].append([page_url, p]); im['src'] = p
        im['alt'] = alt
        im['loading'] = 'lazy'; im['decoding'] = 'async'
        log['lazy_images'] += 1
    # styled boxes and spans
    for t in s.find_all(True):
        st = (t.get('style') or '').lower()
        cls = t.get('class') or []
        newcls = [c for c in cls if c in ('separator', 'products', 'product', 'product-name', 'product-cta', 'yt', 'yt-play')]
        if 'lightyellow' in st or 'background-color: yellow' in st:
            newcls.append('callout')
        if 'dotted 3px' in st:
            newcls.append('callout'); newcls.append('callout-alt')
        if t.name == 'span' and ('8pt' in st or 'x-small' in st or 'font-size: small' in st):
            newcls.append('credit')
        if t.name == 'span' and 'font-size: large' in st:
            t.name = 'strong'; newcls.append('large')
        if 'tr-caption-container' in cls: newcls.append('caption-table')
        if 'tr-caption' in cls: newcls.append('caption')
        if 'tr_bq' in cls: pass
        if t.name == 'div' and 'text-align: center' in st and 'separator' not in newcls and 'callout' not in newcls:
            newcls.append('center')
        t.attrs.pop('style', None)
        for k in ('border', 'cellpadding', 'cellspacing', 'align', 'imageanchor', 'id', 'face', 'color', 'size'):
            t.attrs.pop(k, None)
        if newcls: t['class'] = sorted(set(newcls), key=newcls.index)
        else: t.attrs.pop('class', None)
    for t in s.find_all(['span', 'font']):
        if not t.attrs: t.unwrap()
    for t in s.find_all(['b', 'strong', 'i', 'em', 'u']):
        if not t.get_text(strip=True) and not t.find('img'): t.decompose()
    return paragraphize(s)

BLOCK = {'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'table', 'blockquote', 'p', 'figure', 'hr', 'iframe'}

def paragraphize(s):
    out = BeautifulSoup('', 'html.parser')
    nodes = list(s.contents)
    buf = []
    def flush():
        # trim leading/trailing br and whitespace
        while buf and (isinstance(buf[0], Tag) and buf[0].name == 'br' or isinstance(buf[0], NavigableString) and not buf[0].strip()):
            buf.pop(0)
        while buf and (isinstance(buf[-1], Tag) and buf[-1].name == 'br' or isinstance(buf[-1], NavigableString) and not buf[-1].strip()):
            buf.pop()
        if buf:
            p = out.new_tag('p')
            for n in buf: p.append(n)
            out.append(p); out.append('\n')
        buf.clear()
    i = 0
    while i < len(nodes):
        n = nodes[i]
        n = n.extract() if hasattr(n, 'extract') else n
        if isinstance(n, Tag) and n.name in BLOCK:
            flush()
            if n.name == 'p' and not n.get_text(strip=True) and not n.find('img'):
                pass
            else:
                out.append(n); out.append('\n')
        elif isinstance(n, Tag) and n.name == 'br':
            # double br => paragraph break
            j = i + 1
            while j < len(nodes) and isinstance(nodes[j], NavigableString) and not nodes[j].strip():
                j += 1
            if j < len(nodes) and isinstance(nodes[j], Tag) and nodes[j].name == 'br':
                flush(); i = j
            else:
                buf.append(n)
        else:
            if isinstance(n, NavigableString) and str(n).startswith('<!--'):
                pass
            else:
                buf.append(n)
        i += 1
    flush()
    html = str(out)
    html = re.sub(r'(<br/>\s*){2,}', '<br/>', html)
    html = re.sub(r'<p>\s*(<br/>\s*)*</p>', '', html)
    html = re.sub(r'\n{3,}', '\n\n', html)
    return html.strip()

def local_og(og):
    if not og: return ''
    p = unquote(urlparse(og).path)
    return p if os.path.exists(FILES + p) else ''

posts, pages, labels, archives = [], [], {}, []
for u, p in d.items():
    if p['type'] in ('post', 'page'):
        body = clean_body(p['body_html'], u)
        bs = BeautifulSoup(body, 'html.parser')
        first_img = ''
        for im in bs.find_all('img'):
            if im.get('src', '').startswith('/images') or im.get('src', '').startswith('/img'):
                first_img = im['src']; break
        h1 = (p['h1'][0] if p['h1'] else p['title']).strip()
        item = {
            'url': u, 'title': p['title'], 'h1': h1, 'description': p['desc'],
            'published': p['published'], 'modified': p['modified'], 'author': p.get('author') or 'M. W. Johnstone',
            'labels': p.get('label_slugs', []), 'label_names': p.get('labels', []),
            'og_image': local_og(p['og_image']), 'first_image': first_img,
            'body': body, 'words': len(bs.get_text(' ', strip=True).split()),
            'breadcrumb_label': (p.get('breadcrumb') or [None, None])[1] if p['type'] == 'post' else None,
        }
        (posts if p['type'] == 'post' else pages).append(item)
    elif p['type'] == 'label':
        s = BeautifulSoup(open(f"{W}/raw/pages/{p['url'].strip('/').replace('/', '__')}.html").read(), 'html.parser')
        intro = s.select_one('.label-intro')
        h1 = intro.find('h1').get_text(' ', strip=True) if intro else ''
        ps = [x.get_text(' ', strip=True) for x in intro.find_all('p')] if intro else []
        slug = u.split('/')[-1]
        labels[slug] = {'url': u, 'slug': slug, 'title': p['title'], 'description': p['desc'], 'h1': h1, 'intro': ps}
    elif p['type'] == 'archive':
        archives.append(u)

# label display names from posts
names = {}
for x in posts:
    for sl, nm in zip(x['labels'], x['label_names']): names[sl] = nm
for sl, l in labels.items(): l['name'] = names.get(sl, l['h1'])
os.makedirs(f'{W}/_build/content', exist_ok=True)
posts.sort(key=lambda x: x['published'], reverse=True)
json.dump(posts, open(f'{W}/_build/content/posts.json', 'w'), indent=1, ensure_ascii=False)
json.dump(pages, open(f'{W}/_build/content/pages.json', 'w'), indent=1, ensure_ascii=False)
json.dump(labels, open(f'{W}/_build/content/labels.json', 'w'), indent=1, ensure_ascii=False)
json.dump(sorted(archives), open(f'{W}/_build/content/archives.json', 'w'), indent=1)
json.dump(log, open(f'{W}/_build/extract_log.json', 'w'), indent=1)
print('posts', len(posts), 'pages', len(pages), 'labels', len(labels), 'archives', len(archives))
print({k: (len(v) if isinstance(v, list) else v) for k, v in log.items()})
print('missing', log['missing_images'][:10])
