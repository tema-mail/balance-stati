#!/usr/bin/env python3
"""Картинки статьи из фотобанка клиента: строка `foto: id0, id1, id2, id3` в stati/NN-<slug>.md →
site/img/<slug>-0.jpg (4:3, 1200×900) и -1..-3 (16:9, 1200×675). Номера – refs/katalog-klubov.json
(снимки со страниц своего клуба на balance-fit.ru), листы с номерами – refs/list-<клуб>.jpg.
Запуск: python3 refs/narezat.py stati/22-*.md …  Падает, если снимок чужого клуба или номер повторён в статье."""
import json, re, sys
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
KAT = {x["id"]: x for x in json.load(open(ROOT / "refs/katalog-klubov.json", encoding="utf8"))}


def odna(md: Path):
    t = md.read_text(encoding="utf8")
    head = dict(l.split(": ", 1) for l in t.split("---")[0].splitlines() if ": " in l)
    ids = [int(x) for x in re.findall(r"\d+", head.get("foto", ""))]
    if len(ids) != 4 or len(set(ids)) != 4:
        sys.exit(f"{md.name}: нужно 4 разных номера в строке foto")
    for slot, i in enumerate(ids):
        x = KAT[i]
        if x["club"] != head["club"]:
            sys.exit(f"{md.name}: снимок {i} со страниц клуба {x['club']}, а статья {head['club']}")
        size = (1200, 900) if slot == 0 else (1200, 675)
        im = ImageOps.fit(Image.open(x["f"]).convert("RGB"), size, Image.LANCZOS, centering=(0.5, 0.5))
        im.save(ROOT / "site/img" / f"{head['slug']}-{slot}.jpg", quality=84, optimize=True)
    print(md.name, "картинки:", ids)


if __name__ == "__main__":
    for a in sys.argv[1:]:
        odna(Path(a))
