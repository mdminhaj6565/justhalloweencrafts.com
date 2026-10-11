# justhalloweencrafts.com — SEO Audit ও Fix রিপোর্ট

তারিখ: ১১ অক্টোবর ২০২৬
উৎস: Google Search Console (শেষ ৩ মাস, ৯ জুলাই – ৮ অক্টোবর ২০২৬) + live site-এর সব ১৪৪টি page crawl

## ১. Search Console-এর অবস্থা (আগে)

| বিষয় | মান |
| --- | --- |
| মোট click | 644 |
| মোট impression | ~48,000 |
| গড় CTR | 1.3% |
| গড় position | 8.4 |
| Indexed page | 100 |
| Not indexed page | 278 |
| Core Web Vitals (mobile) | 55 URL "Good" |
| Sitemap | `/sitemap.xml`, 150টি URL discovered, শেষ পড়া ১৩ সেপ্টেম্বর ২০২৬ |

### Not indexed হওয়ার কারণ

| কারণ | Page | ব্যাখ্যা |
| --- | --- | --- |
| Page with redirect | 104 | পুরোনো Blogger `.html` ও `?m=1` URL — redirect ঠিক আছে, এগুলো স্বাভাবিক |
| Alternate page with proper canonical tag | 84 | `?m=1` mobile URL — স্বাভাবিক |
| Discovered – currently not indexed | 58 | গুরুত্বপূর্ণ: নতুন clean URL-গুলো (যেমন hood for cloak, crow cutouts, spell book-এর মত page) এখনো index হয়নি; `_m-1`, `search?updated-max` জাতীয় junk URL-ও আছে |
| Crawled – currently not indexed | 14 | পুরোনো `/feeds/.../comments/default`, month archive, `_m-1` page |
| Blocked by robots.txt | 13 | পুরোনো Blogger label ও search page (এখন robots allow করে) |
| Duplicate, Google chose different canonical | 5 | Month archive page (`/2016/07`, `/2016/01` …) — thin/duplicate |

### Performance-এর মূল সমস্যা

* **Snape quotes page**: 9,002 impression কিন্তু CTR মাত্র 0.5% (position 7.5) → title/description দুর্বল।
* **Half butterfly template**: 2,940 impression, position 1.9, CTR 0.6% → title-এ "half butterfly" ছিল না, অথচ query সেটাই।
* **Perler bead patterns**: 1,598 impression, CTR 0.1%।
* **Wire wreath frame** (position 13.8), **hollow pumpkin** (501 impression, 0 click), **cupcake ideas** (position 64) — দুর্বল ranking।
* Homepage গড় position 33.5 — homepage-এ প্রায় কোনো বিষয়বস্তু/H1 ছিল না।

## ২. Live site audit-এ পাওয়া সমস্যা

### Technical
1. প্রতিটি page গড়ে ~123 KB HTML (সর্বোচ্চ 478 KB) — Blogger theme-এর ~80 KB inline CSS প্রতিটি page-এ।
2. 43টি পুরোনো Blogger JavaScript ফাইল, 132টি Roboto font ফাইল, Blogger comment iframe, share button — static hosting-এ এগুলো কাজই করে না।
3. Analytics দুই/তিনবার load হচ্ছিল: বন্ধ হয়ে যাওয়া Universal Analytics (`UA-64073368-1`, analytics.js) + দুটি GA4 tag।
4. Theme CSS-এ ভাঙা background URL (`/2016/03/https:\/\/themes.googleusercontent.com/...`) — প্রতিটি page-এ 404 request।
5. ২৬টি month archive page index-যোগ্য ও sitemap-এ ছিল (thin/duplicate)।
6. Sitemap-এর সব URL-এ একই `lastmod` (2026-10-07) — Google এমন lastmod বিশ্বাস করে না।
7. Structured data-র image Blogger CDN-এ (blogger.googleusercontent.com) point করছিল।
8. "Post a Comment", "Powered by Blogger", Blogger share link — static site-এ অকার্যকর।
9. Amazon product ছবি (৭১টি) server-এ copy করে রাখা ছিল — Amazon Associates নীতিমালার বিরুদ্ধে।
10. Affiliate link-এ `rel="sponsored"` ছিল না (শুধু `nofollow`)।

### Content ও link
1. **craftymarie.com** (১৬টি link + About page-এর contact link) — domain-টি এখন একটি জুয়া (slot/gambling) spam site। খুবই ক্ষতিকর outbound link।
2. **halloweenangel.com** (২৫টি link) — অন্য একটি অসম্পর্কিত site (myeasycamper.com)-এ redirect হয়।
3. ৬টি YouTube video মুছে ফেলা/private (embed ও link)।
4. ৭৫টি article ২০১৫–২০১৯ সালের, বেশিরভাগ শেষবার update ২০১৮-এ।
5. কয়েকটি গুরুত্বপূর্ণ printable/tutorial page thin (375–587 শব্দ)।
6. পুরোনো লেখায় "comments below-এ জানান" — কিন্তু comment system আর নেই।
7. About/FTC page-এ অকার্যকর contact পদ্ধতি ও পুরোনো তারিখ।

## ৩. যা fix করা হয়েছে

* পুরো site নতুন করে বানানো (static HTML): একই URL, একই ছবির path, সব article রাখা হয়েছে। গড় HTML 123 KB → 18 KB; একটি 12 KB CSS, 2 KB JS, self-hosted font।
* `.htaccess`: www canonical, `.html` → clean URL, `?m=1`, `_m-1`, `_spref-pi`, trailing slash, label-এর space, `/search` → `/blog`, পুরোনো feed → `/feed.xml`, বাকি feed 410 — সব single-hop 301।
* Title/description নতুন করে লেখা: Snape quotes, Luna quotes, hood for cloak, sew hood onto cape, cloak without pattern, half butterfly, crow silhouettes, Maleficent template, potion labels, Perler patterns, wire wreath, spell book, hollow pumpkin।
* ৯টি পুরোনো article-এ নতুন section যোগ (sizing tips, problem fix, printing tips, FAQ, craft ideas) — dateModified আপডেট।
* ৪৬টি dead/spam link সরানো, ৪টি মৃত video embed সরানো, বাকি video click-to-load (youtube-nocookie)।
* ৩৪৬টি affiliate link → `rel="sponsored nofollow noopener"`; Amazon/Etsy ছবি তাদের নিজস্ব CDN থেকে।
* Schema: BlogPosting + BreadcrumbList + Organization (প্রতিটি article), CollectionPage + ItemList (category), WebSite (home)।
* Sitemap: আসল lastmod, image sitemap entry; archive ও ১–২ post-এর category noindex এবং sitemap থেকে বাদ।
* RSS feed, favicon set, web manifest, 404 page, breadcrumb, related posts, author box, affiliate disclosure।
* Analytics শুধু একটি GA4 tag (`G-34D5HXD2C1`)।
* **১২টি নতুন article** (১,০৪০–১,২৯৮ শব্দ, প্রতিটি আলাদা keyword):
  1. How to Make a Witch Hat from Felt or Card
  2. How to Make a Witch's Broom from Twigs and a Stick
  3. The Best Fabric for a Cloak or Cape (and What to Avoid)
  4. How to Make a Wizard Wand with Chopsticks and Hot Glue
  5. Egg Carton Halloween Crafts: Bats, Spiders and Little Monsters
  6. Halloween Sensory Bin Ideas for Toddlers and Preschoolers
  7. Painted Halloween Rocks: Easy Designs and Tips That Last
  8. How to Make DIY Potion Bottles for Halloween Decor
  9. Paper Plate Halloween Masks Kids Can Make
  10. Glow-in-the-Dark Halloween Crafts: 6 Easy Projects
  11. Felt Halloween Finger Puppets: Ghost, Pumpkin, Bat and Cat
  12. How to Store Halloween Decorations So They Last for Years

## ৪. যা হাতে করতে হবে (Manual / Live verification required)

1. Repo-টি Hostinger-এ deploy করা (README দেখুন) — deploy ছাড়া live site বদলাবে না।
2. Deploy-এর পর Search Console-এ sitemap resubmit ও নতুন article-এর জন্য Request indexing।
3. About page-এ কাজের একটি contact পদ্ধতি (email/contact form) যোগ করা — আগেরটি spam domain-এ ছিল।
4. পুরোনো Amazon/Etsy product (২০১৫–২০১৭) এখনো বিক্রি হচ্ছে কিনা যাচাই।
5. Deploy-এর পর Core Web Vitals ও redirect live-এ পরীক্ষা (যেমন `/2016/03/luna-lovegood-quotes-books-harry-potter.html?m=1` → এক hop-এ clean URL)।
6. Indexing, ranking ও CTR-এর উন্নতি দেখতে ৪–৮ সপ্তাহ সময় লাগে।
