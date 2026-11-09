#!/usr/bin/env python3
"""Аргументы поста для Тильды Balance: python3 tilda_post.py <адрес> <postuid> <дата 'ГГГГ-ММ-ДД ЧЧ:ММ'> [y]
Картинки привязаны строками в теме сайта (custom.css) к файлам в Тильде проекта Balance (tilda/cdn.json); стиль в коде поста Тильда вырезает."""
import json, re, sys
from pathlib import Path
from build import parse, render
ROOT = Path(__file__).parent
CDN = json.load(open(Path(__file__).parent / "tilda/cdn.json", encoding="utf8"))
img = lambda slug, i: CDN[f"{slug}-{i}"]

def args(slug, uid, date, vis=""):
    f = next((ROOT / "stati").glob(f"*-{slug}.md"))
    m, blocks = parse(f)
    p1, p2, _ = render(m, blocks)
    cover = img(slug, 0)
    return {"projectid": 4906566, "postuid": uid, "title": m["card"], "descr": m["description"],
            "text": json.dumps([{"ty": "text", "te": p1}, {"ty": "text", "te": p2}], ensure_ascii=False),
            "visibility": vis, "mediatype": "image", "mediadata": cover, "image": cover, "imagealt": m["card"],
            "thumb": cover, "thumbalt": m["card"], "date": date, "postalias": slug,
            "seo_title": m["title"], "seo_descr": m["description"], "disablecomments": "", "priority": 300}

if __name__ == "__main__":
    print(json.dumps(args(*sys.argv[1:]), ensure_ascii=False))
