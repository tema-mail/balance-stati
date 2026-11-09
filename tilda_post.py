#!/usr/bin/env python3
"""Аргументы поста для Тильды Balance: python3 tilda_post.py <адрес> <postuid> <дата 'ГГГГ-ММ-ДД ЧЧ:ММ'> [y]
Картинки – прямо в стиле блоков (у ключа нет загрузки в Тильду и правки темы), файлы с GitHub Pages."""
import json, re, sys
from pathlib import Path
from build import parse, render
ROOT = Path(__file__).parent
IMG = "https://tema-mail.github.io/balance-stati/img/"

def args(slug, uid, date, vis=""):
    f = next((ROOT / "stati").glob(f"*-{slug}.md"))
    m, blocks = parse(f)
    p1, p2, _ = render(m, blocks)
    p1 = p1.replace(f'class="hero__cover hero__cover--{slug}"', f'class="hero__cover hero__cover--{slug}" style="background-image:url({IMG}{slug}-0.jpg)"')
    for n in (1, 2, 3):
        p2 = p2.replace(f'class="art-pic pic--{slug}-sec{n}"', f'class="art-pic pic--{slug}-sec{n}" style="background-image:url({IMG}{slug}-{n}.jpg)"')
    assert p1.count("background-image") == 1 and p2.count("background-image") == 3
    cover = IMG + f"{slug}-0.jpg"
    return {"projectid": 4906566, "postuid": uid, "title": m["card"], "descr": m["description"],
            "text": json.dumps([{"ty": "text", "te": p1}, {"ty": "text", "te": p2}], ensure_ascii=False),
            "visibility": vis, "mediatype": "image", "mediadata": cover, "image": cover, "imagealt": m["card"],
            "thumb": cover, "thumbalt": m["card"], "date": date, "postalias": slug,
            "seo_title": m["title"], "seo_descr": m["description"], "disablecomments": "", "priority": 300}

if __name__ == "__main__":
    print(json.dumps(args(*sys.argv[1:]), ensure_ascii=False))
