#!/usr/bin/env python3
"""Новые статьи – на Тильду черновиками по схеме 10.11 (docs/kartinki-chatgpt.md, «Тильда: как ставить картинки»):
4 картинки в проект (upload_image) → tilda/cdn.json; строки картинок в CSS проекта (бэкап рядом);
пост в ленте клуба (feeds_add_post) → tilda/uids.tsv; поля поста с датой по плану, черновиком;
строка в tilda/raspisanie.tsv – дальше publish_due.py откроет в срок.
Час выхода по клубу – как в расписании 16–18.11 (пояс ленты Asia/Bangkok = НСК).
  python3 tilda_novye.py <адрес> [<адрес> ...]
Повторный запуск безопасен: что уже сделано (cdn, uid, css, расписание) – пропускает."""
import base64, json, sys
from datetime import datetime
from pathlib import Path
from build import parse
from publish_due import call, ROOT

PROEKT = 4906566
LENTA = {"abricosovo": "573779099091", "imperial": "961482311971", "admiral": "954359792021"}
CHAS = {"abricosovo": "14:40", "imperial": "16:40", "admiral": "19:40"}
CDN_F, UIDS_F, RASP_F = ROOT / "tilda/cdn.json", ROOT / "tilda/uids.tsv", ROOT / "tilda/raspisanie.tsv"


def kartinki(slug, cdn):
    nado = [i for i in range(4) if f"{slug}-{i}" not in cdn]
    if not nado:
        return
    imgs = [{"image_base64": base64.b64encode((ROOT / f"site/img/{slug}-{i}.jpg").read_bytes()).decode(),
             "mimetype": "image/jpeg", "filename": f"{slug}-{i}.jpg"} for i in nado]
    otvet = json.loads(call("upload_image", {"projectid": PROEKT, "images": imgs}))
    spisok = otvet if isinstance(otvet, list) else next(v for v in otvet.values() if isinstance(v, list))
    urls = [x if isinstance(x, str) else (x.get("url") or x.get("cdnUrl") or x.get("link")) for x in spisok]
    if len(urls) != len(nado) or not all(u and u.startswith("https://") for u in urls):
        raise RuntimeError(f"upload_image: не тот ответ {str(otvet)[:300]}")
    for i, u in zip(nado, urls):
        cdn[f"{slug}-{i}"] = u
    CDN_F.write_text(json.dumps(cdn, ensure_ascii=False, indent=0), encoding="utf8")


def css(slugi, cdn):
    staryy = call("get_project_css_code", {"projectid": PROEKT})
    try:
        staryy = json.loads(staryy).get("csscode", staryy)
    except (ValueError, AttributeError):
        pass
    stroki = []
    for slug in slugi:
        if f"hero__cover--{slug}" not in staryy:
            stroki.append(f".bal-page .hero__cover--{slug}{{background-image:url({cdn[slug + '-0']})}}")
        for n in (1, 2, 3):
            if f"pic--{slug}-sec{n}" not in staryy:
                stroki.append(f".bal-page .pic--{slug}-sec{n}{{background-image:url({cdn[f'{slug}-{n}']})}}")
    if not stroki:
        return 0
    (ROOT / f"tilda/custom-css-backup-{datetime.now():%Y-%m-%d-%H%M}.css").write_text(staryy, encoding="utf8")
    call("update_project_css_code", {"projectid": PROEKT, "csscode": staryy.rstrip() + "\n" + "\n".join(stroki) + "\n"})
    return len(stroki)


def main(slugi):
    import tilda_post
    from tilda_post import args
    cdn = tilda_post.CDN   # тот же словарь: новые картинки сразу видны args()
    uids = dict(l.split("\t") for l in UIDS_F.read_text(encoding="utf8").split("\n") if "\t" in l)
    rasp = RASP_F.read_text(encoding="utf8")
    for slug in slugi:
        m, _ = parse(next((ROOT / "stati").glob(f"*-{slug}.md")))
        d = datetime.strptime(m["date"][:10], "%d.%m.%Y").strftime("%Y-%m-%d") + " " + CHAS[m["club"]]
        kartinki(slug, cdn)
        if slug not in uids:
            otvet = json.loads(call("feeds_add_post", {"projectid": PROEKT, "feeduid": LENTA[m["club"]], "title": m["card"]}))
            uid = otvet.get("postuid") or otvet.get("uid") or (otvet.get("post") or {}).get("uid")
            if not uid:
                raise RuntimeError(f"feeds_add_post: нет uid {str(otvet)[:300]}")
            uids[slug] = uid
            with UIDS_F.open("a", encoding="utf8") as f:
                f.write(f"{slug}\t{uid}\n")
        print(slug, uids[slug], d, call("feeds_update_post", args(slug, uids[slug], d)), flush=True)
        if f"\n{slug}\t" not in "\n" + rasp:
            rasp = rasp.rstrip("\n") + f"\n{slug}\t{uids[slug]}\t{d}\n"
            RASP_F.write_text(rasp, encoding="utf8")
    print("строк CSS:", css(slugi, cdn))


if __name__ == "__main__":
    main(sys.argv[1:])
