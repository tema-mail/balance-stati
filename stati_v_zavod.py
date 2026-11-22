#!/usr/bin/env python3
"""Статьи Баланса из stati/*.md – в календарь завода (сайт balance): строка stati_chernoviki (превью на Pages,
обоснование из шапки) и день в плане выхода. Текст статьи в завод не копируется – кабинет открывает превью.
Запуск на claude-vps от пользователя zavod:
  PYTHONPATH=/opt/zavod/app python3 stati_v_zavod.py /opt/zavod/data/zavod.db <папка со статьями> [--dry] [--s 2026-12-01]
--dry – на копии базы. --s – брать статьи с этой даты. Повторный запуск: статья уже есть (по slug) –
обновляет только обоснование. Ничего не выкладывает: статус «готово», выкладка – отдельным «да»."""
import json, re, shutil, sys, tempfile, time
from pathlib import Path

from engine import db, kalendar

PREVYU = "https://tema-mail.github.io/balance-stati/{slug}.html"
URL = "https://balance-fit.ru/{club}/blog/{slug}"
PUT = {"imperial": "borodinskaya", "abricosovo": "abricosovo", "admiral": "admiral"}


def shapka(md: str) -> dict:
    return dict(re.findall(r"^(\w+):\s*(.*)$", md.partition("\n---\n")[0], re.M))


def obosnovanie(d: dict) -> dict | None:
    if not d.get("zachem"):
        return None
    return {"zachem": d["zachem"], "vedyot_na": d.get("vedyot", ""), "ssylka": d.get("vedyot_url", ""),
            "klyuchi": [k.strip() for k in d.get("klyuchi", "").split(";") if k.strip()], "spros": d.get("spros", "")}


def zagruzit(con, papka: Path, s_daty: str = "") -> list[str]:
    sid = con.execute("SELECT id FROM sites WHERE slug='balance'").fetchone()["id"]
    uids = dict(l.split("\t") for l in (papka.parent / "tilda/uids.tsv").read_text(encoding="utf8").splitlines()
                if "\t" in l)
    itogi = []
    for f in sorted(papka.glob("*.md")):
        d = shapka(f.read_text(encoding="utf8"))
        den, mes, god = d["date"].split()[0].split(".")
        iso = f"{god}-{mes}-{den}"
        if s_daty and iso < s_daty:
            continue
        if d["slug"] not in uids:
            itogi.append(f"{iso} {d['slug']}: СТОП нет Tilda UID – сначала создать нативный черновик")
            continue
        ob = obosnovanie(d)
        byl = con.execute("SELECT id, dannye FROM stati_chernoviki WHERE site_id=? AND slug=?", (sid, d["slug"])).fetchone()
        if byl:
            dn = json.loads(byl["dannye"] or "{}")
            izmenen = False
            if dn.get("tilda_uid") != uids[d["slug"]]:
                dn["tilda_uid"] = uids[d["slug"]]
                izmenen = True
            if ob and dn.get("obosnovanie") != ob:
                dn["obosnovanie"] = ob
                izmenen = True
            if izmenen:
                con.execute("UPDATE stati_chernoviki SET dannye=?,url=? WHERE id=?",
                            (json.dumps(dn, ensure_ascii=False), URL.format(club=PUT[d["club"]], slug=d["slug"]), byl["id"]))
                itogi.append(f"{iso} {d['slug']}: уже есть, Tilda UID/адрес синхронизированы")
            else:
                itogi.append(f"{iso} {d['slug']}: уже есть")
            continue
        if not ob:
            itogi.append(f"{iso} {d['slug']}: СТОП нет обоснования в шапке")
            continue
        now = time.time()
        dn = {"prevyu": PREVYU.format(slug=d["slug"]), "obosnovanie": ob, "tilda_uid": uids[d["slug"]]}
        con.execute("BEGIN")
        try:
            cid = con.execute("INSERT INTO stati_chernoviki(site_id, tema, slug, dannye, status, url, created, updated) "
                              "VALUES(?,?,?,?,?,?,?,?)",
                              (sid, d["h1"], d["slug"], json.dumps(dn, ensure_ascii=False), "gotovo",
                               URL.format(club=PUT[d["club"]], slug=d["slug"]), now, now)).lastrowid
            kalendar.postavit(con, sid, "statya", cid, "sayt", data=iso)
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
        itogi.append(f"{iso} {d['slug']}: в календаре")
    return itogi


def main():
    baza, papka = Path(sys.argv[1]), Path(sys.argv[2])
    s_daty = sys.argv[sys.argv.index("--s") + 1] if "--s" in sys.argv else ""
    if "--dry" in sys.argv:
        tmp = Path(tempfile.mkdtemp()) / "zavod.db"
        db.kopiya(baza, tmp)
        baza = tmp
    con = db.connect(baza)
    for s in zagruzit(con, papka, s_daty):
        print(s)
    if "--dry" in sys.argv:
        shutil.rmtree(baza.parent)
        print("(проба на копии, база не тронута)")


if __name__ == "__main__":
    main()
