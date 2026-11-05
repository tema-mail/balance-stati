#!/usr/bin/env python3
"""Пакет для Тильды: tilda/manifest.json (всё для выкладки скриптом) и site/tilda.html (проверка глазами)."""
import html, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from build import parse, render, CLUBS
ROOT = Path(__file__).parent; OUT = ROOT / "tilda"; OUT.mkdir(exist_ok=True)

def main():
    posts = []
    for f in sorted((ROOT / "stati").glob("*.md")):
        m, blocks = parse(f)
        p1, p2, _ = render(m, blocks)
        slug = m["slug"]
        imgs = [f"site/img/{slug}-{i}.jpg" for i in range(4)]
        missing = [i for i in imgs if not (ROOT / i).exists()]
        posts.append(dict(club=m["club"], feed=CLUBS[m["club"]]["feed"], date=m["date"], card=m["card"], h1=m["h1"], title=m["title"],
            description=m["description"], slug=slug, alias=slug, cover=imgs[0], images=imgs, missing=missing, part1=p1, part2=p2,
            css_template=[f".bal-page .hero__cover--{slug}{{background-image:url(URL0)}}"] + [f".bal-page .pic--{slug}-sec{n}{{background-image:url(URL{n})}}" for n in (1, 2, 3)]))
    posts.sort(key=lambda p: (p["date"][6:10], p["date"][3:5], p["date"][:2], p["date"][11:]))
    (OUT / "manifest.json").write_text(json.dumps(posts, ensure_ascii=False, indent=1), encoding="utf8")
    rows = "".join(f'<tr><td>{p["date"]}</td><td>{CLUBS[p["club"]]["name"]}</td><td><a href="{p["slug"]}.html">{html.escape(p["card"])}</a></td>'
                   f'<td>{p["feed"]}/{p["slug"]}</td><td>{4 - len(p["missing"])}/4</td></tr>' for p in posts)
    (ROOT / "site/tilda.html").write_text(f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="robots" content="noindex,nofollow"><title>Balance: пакет для Тильды</title>
<style>body{{font:16px/1.5 -apple-system,Arial,sans-serif;max-width:1100px;margin:0 auto;padding:20px}}table{{border-collapse:collapse;width:100%}}td,th{{border-bottom:1px solid #ddd;padding:7px;text-align:left}}</style></head><body>
<p><a href="index.html">← Все статьи</a></p><h1>Пакет для Тильды: {len(posts)} постов</h1><p>Лента, дата, поля, две части HTML, картинки и строки темы лежат в <code>tilda/manifest.json</code>.</p>
<table><thead><tr><th>Дата</th><th>Клуб</th><th>Пост</th><th>Лента и адрес</th><th>Фото</th></tr></thead><tbody>{rows}</tbody></table></body></html>''', encoding="utf8")
    print(f"постов {len(posts)}; без картинок {sum(bool(p['missing']) for p in posts)}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
