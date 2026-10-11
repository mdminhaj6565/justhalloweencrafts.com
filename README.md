# justhalloweencrafts.com

Source of the **Just Halloween Crafts** website (https://www.justhalloweencrafts.com): Halloween craft tutorials, costume accessories, free printables and party food ideas.

The site is a fast static website (plain HTML + one CSS file + a tiny JS file). The old Blogger mirror (≈120 KB of HTML, 40+ legacy Blogger scripts and 130+ font files per page) was replaced with a clean build that keeps **every existing URL**, all original images and all existing articles.

## What is in this repository

| Path | What it is |
| --- | --- |
| `index.html`, `blog.html`, `404.html` | Home, blog index and error page |
| `2015/…` – `2026/…` | Articles (`/2016/03/post-slug` is served from `2016/03/post-slug.html`) and month archives (`/2016/03` → `2016/03.html`) |
| `search/label/*.html` | Category pages (same URLs as the old Blogger labels) |
| `p/*.html` | About, privacy policy and affiliate disclosure |
| `images/`, `img/` | Original site images (paths unchanged, so image search rankings are kept) |
| `images/thumbs/`, `images/cards/` | Generated listing thumbnails and social cards |
| `assets/` | CSS, JS and self-hosted fonts |
| `sitemap.xml`, `robots.txt`, `feed.xml` | Sitemap (with image entries), robots rules and RSS feed |
| `.htaccess` | Clean URLs, 301 redirects for old Blogger URLs, caching, security headers |
| `_build/` | Content sources and the generator (not public, blocked in `.htaccess`) |

## Deploying to Hostinger

1. Back up the current `public_html` (hPanel → Files → Backups, or download it).
2. Upload the contents of this repository into `public_html` (File Manager → upload ZIP → extract), **or** connect the repository in hPanel → Advanced → Git and deploy it to `public_html`.
3. Make sure **Force HTTPS** is on (hPanel → Security → SSL).
4. In Google Search Console: submit `https://www.justhalloweencrafts.com/sitemap.xml` again and use URL Inspection → Request indexing for the new articles.

The `.htaccess` file needs Apache/LiteSpeed with `mod_rewrite` (standard on Hostinger).

## Editing content

* Existing articles: `_build/content/posts.json` (body HTML, title, description, dates, categories).
* SEO titles/descriptions and added sections: `_build/content/overrides.json`.
* New articles: add an HTML file to `_build/content/new/` with a JSON header (see the existing files).
* Rebuild the whole site:

```bash
pip install beautifulsoup4 pillow
python3 _build/build.py
```

The build rewrites all HTML pages, `sitemap.xml` and `feed.xml`, and creates thumbnails for new articles. Commit and push the result.

## Content autopilot

* `_build/plan/CONTENT-CALENDAR.md` – publishing calendar (every other day in September–October, every 3 days the rest of the year), refresh queue and title change log.
* `_build/plan/AUTOPILOT.md` – the runbook the scheduled tasks follow (publish run and Search Console run).
* `_build/plan/GSC-PROGRESS.md` – Search Console numbers recorded three times a week (clicks, impressions, CTR, position, indexing) and the actions taken.
* `python3 _build/check.py` – link, heading, title/description, JSON-LD and word-count checks after a build.

New articles only go live when the repository is deployed. Turn on **Auto Deployment** in hPanel → Websites → Manage → Advanced → GIT so that every push is published automatically.

---

### বাংলা নির্দেশনা (সংক্ষেপে)

* পুরো সাইট এই repo-তে আছে: সব পুরোনো article, ছবি, নতুন ১২টি article, sitemap, robots.txt ও `.htaccess`।
* Hostinger-এ deploy: `public_html` ব্যাকআপ নিন, তারপর এই repo-র সব ফাইল `public_html`-এ upload/extract করুন অথবা hPanel → Git দিয়ে deploy করুন।
* Deploy-এর পর Search Console-এ sitemap আবার submit করুন এবং নতুন article-গুলোর জন্য "Request indexing" দিন।
* নতুন article যোগ করতে `_build/content/new/`-এ ফাইল রেখে `python3 _build/build.py` চালান।
* Content autopilot: `_build/plan/`-এ content calendar, runbook ও Search Console progress log আছে। প্রতিটি push live করতে hPanel → GIT-এ Auto Deployment চালু রাখুন।
