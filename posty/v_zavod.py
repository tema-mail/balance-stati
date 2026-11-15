#!/usr/bin/env python3
"""Посты Баланса из posty/<неделя>/<клуб>.json – в календарь завода (сайт balance) функциями самого завода:
публикация → проверка площадки (красный список, правила, факты) → «ждёт да» (решение владельцу) → день в календаре.
Запуск на claude-vps от пользователя zavod:
  PYTHONPATH=/opt/zavod/app python3 v_zavod.py /opt/zavod/data/zavod.db файл.json [--dry]
--dry – на копии базы, в настоящую ничего не пишет. Повторный запуск пропускает уже заведённые посты (по теме)."""
import json, shutil, sys, tempfile, time
from pathlib import Path

from engine import db, kalendar
from engine import ploshchadki as pl
from engine.st_ploshchadki import v_utverzhdeniya

IMYA = {"abricosovo": "Абрикосово", "imperial": "Империал", "admiral": "Адмирал"}


def zagruzit(con, fail: Path) -> list[str]:
    klub = fail.stem
    s = con.execute("SELECT * FROM sites WHERE slug='balance'").fetchone()
    site = {**dict(s), "settings": json.loads(s["settings"] or "{}")}
    itogi = []
    for x in json.loads(fail.read_text(encoding="utf8")):
        k = x["kanal"]
        mod = pl.PLOSHCHADKI[k]
        tema = f"{IMYA[klub]}: {x['tema']}"
        if con.execute("SELECT 1 FROM publikacii WHERE site_id=? AND ploshchadka=? AND tema=?",
                       (s["id"], k, tema)).fetchone():
            itogi.append(f"{x['data']} {k} {tema}: уже есть")
            continue
        paket = {"zagolovok": x.get("zagolovok") or "", "tekst": x["tekst"], "kartinki": x.get("kartinki") or [],
                 "pishet_chelovek": False, "ssylka": None}
        paket.update(mod.vylozhit(paket, {}))
        if mod.pravila.avtopublikaciya:   # пост без статьи сайта – в Студию Дзена руками (как станция «Посты»)
            paket.update(sposob="paket", avtomaticheski=False, kuda="Студия Дзена → Создать → Статья",
                         shagi=["открыть Студию Дзена", "вставить заголовок и текст, картинки на места {img1} {img2}",
                                "опубликовать и вставить ссылку на вышедшую публикацию в завод"])
        con.execute("BEGIN")
        try:
            pid = pl.sozdat(con, site_id=s["id"], ploshchadka=k, tema=tema)
            itog = mod.proverit(con, paket, site, "")
            metka = f"{IMYA[klub]} · {paket['zagolovok'] or x['tema']}"
            pl.smenit(con, pid, "proverka", zagolovok=metka, tekst=paket["tekst"], paket=paket, proverka=itog)
            if not itog["ok"]:
                pr = "; ".join(n["chto"] for n in itog["nahodki"] if n["uroven"] == pl.STOP)
                con.execute("ROLLBACK")
                itogi.append(f"{x['data']} {k} {tema}: СТОП {pr[:200]}")
                continue
            aid = v_utverzhdeniya(con, s, {"id": None, "tema": tema}, mod, pid, paket, itog)
            pl.smenit(con, pid, "zhdyot_da", f"ждёт «да»: решение {aid}", reshenie_id=aid)
            kalendar.postavit(con, s["id"], "post", pid, k, data=x["data"])
            con.execute("COMMIT")
            itogi.append(f"{x['data']} {k} {tema}: ждёт «да» (внимание {itog['vnimanie']})")
        except Exception:
            con.execute("ROLLBACK")
            raise
    return itogi


def main():
    baza, fail = Path(sys.argv[1]), Path(sys.argv[2])
    if "--dry" in sys.argv:
        tmp = Path(tempfile.mkdtemp()) / "zavod.db"
        db.kopiya(baza, tmp)
        baza = tmp
    con = db.connect(baza)
    for s in zagruzit(con, fail):
        print(s)
    if "--dry" in sys.argv:
        shutil.rmtree(baza.parent)
        print("(проба на копии, база не тронута)")


if __name__ == "__main__":
    main()
