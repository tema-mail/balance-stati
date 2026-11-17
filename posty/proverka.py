#!/usr/bin/env python3
"""Проверка файла постов недели: posty/<дата>/<клуб>.json. Код 0 – ошибок нет.
Правила площадок – как в заводе (engine/ploshchadki.py), слова – красный список Баланса (data_spiski/balance.tsv).
Обоснование «зачем мы это сделали» (docs/obosnovanie.md) – у каждого поста, проверка posty/obosnovanie.py; без него – ошибка.
Запуск: python3 posty/proverka.py [файлы…]  – без файлов все три клуба posty/2026-11-16/ и сверка по сети
(график ВК и Дзена: на каждую дату ровно один пост каждого канала, повторы обоснований по всем постам)."""
import csv, json, re, sys
import datetime as dt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from obosnovanie import oshibki as ob_oshibki, povtory as ob_povtory

ROOT = Path(__file__).resolve().parent.parent
NEDELYA = ROOT / "posty/2026-11-16"
START, KONEC_GRAFIKA = dt.date(2026, 11, 16), dt.date(2027, 1, 18)
# пост сети (поле "set": true) – сверх 14 постов клуба, только в эти даты, лежит в файле клуба по очереди (31.12 – Адмирал)
SET_DATY = {"2026-12-31"}
VK_SSYLKA = "сообщения сообщества vk.ru/balance_krd"
TSV = Path.home() / "Sites/zavod-ai-sfera/data_spiski/balance.tsv"
KLUB = {"abricosovo": "abrikosovo", "imperial": None, "admiral": "admiral"}
BLOG = {"abricosovo": "abricosovo/blog", "imperial": "imperial/blog", "admiral": "admiral/blog"}
NE_BRAT = ("bal-admiral-klub-1", "bal-admiral-klub-2", "bal-admiral-spa-1")
SLOP = r"(?i)в современном мире|давайте разбер|важно отметить|не просто \w+, а|в заключение|играет важную роль|ключ к успеху"


def krasnyy(klub):
    out = []
    for r in csv.DictReader(TSV.open(encoding="utf8"), delimiter="\t"):
        g = r["gde"]
        if g == "balance" or (KLUB[klub] and g == f"balance/{KLUB[klub]}"):
            out.append((r["regex"], r.get("isklyuchenie") or "", r["uroven"], r["prichina"]))
    return out


def main(f):
    p = Path(f)
    klub = p.stem
    posty = json.loads(p.read_text(encoding="utf8"))
    err, vn = [], []
    rl = krasnyy(klub)
    kl_files = set()   # slug кадров своего клуба: статьи сайта и Дзена
    for md in list((ROOT / "stati").glob("*.md")) + list((ROOT / "dzen").glob("*.md")):
        h = dict(l.split(": ", 1) for l in md.read_text(encoding="utf8").split("---")[0].splitlines() if ": " in l)
        if h.get("club") == klub and h.get("slug"):
            kl_files.add(("dzen-" if md.parent.name == "dzen" else "") + h["slug"])
    svoi = [x for x in posty if not x.get("set")]
    seti = [x for x in posty if x.get("set")]
    if len(svoi) != 14:
        err.append(f"постов клуба {len(svoi)}, нужно 14 (плюс посты сети с \"set\": true)")
    for x in seti:
        if x.get("data") not in SET_DATY:
            err.append(f"{x.get('data')} {x.get('kanal')}: пост сети не в праздничную дату {sorted(SET_DATY)}")
    if len({(x.get("data"), x.get("kanal")) for x in seti}) != len(seti):
        err.append("два поста сети одного канала в одну дату")
    # ВК и Дзен – одна группа и один канал на сеть: пост раз в 3 дня от 16.11, клубы по очереди (Артём 16.11)
    for x in posty:
        if (dt.date.fromisoformat(x["data"]) - START).days % 3:
            err.append(f"{x['data']} {x.get('kanal')}: дата не по графику раз в 3 дня от 16.11")
    for x in posty:
        k, t, z = x.get("kanal"), x.get("tekst") or "", x.get("zagolovok") or ""
        tag = f"{x.get('data')} {k}"
        n = len(t)
        both = z + "\n" + t
        if "—" in both: err.append(f"{tag}: длинное тире")
        if re.search(r"\.\.\.|…", both): err.append(f"{tag}: многоточие")
        if re.search(r"₽|\bруб|\bот \d", both): err.append(f"{tag}: похоже на цену")
        if re.search(SLOP, both): err.append(f"{tag}: штамп нейросети «{re.search(SLOP, both).group(0)}»")
        for rx, isk, ur, pr in rl:
            try:
                m = re.search(rx, both)
            except re.error:
                continue
            if m and not (isk and re.search(isk, both)):
                (err if ur == "STOP" else vn).append(f"{tag}: {pr} («{m.group(0)}»)")
        for u in x.get("kartinki") or []:
            fn = u.rsplit("/", 1)[-1]
            if not (ROOT / "site/img" / fn).exists(): err.append(f"{tag}: нет картинки {fn}")
            if any(b in fn for b in NE_BRAT): err.append(f"{tag}: запрещённый кадр {fn}")
            if re.sub(r"-\d+\.jpg$", "", fn) not in kl_files: err.append(f"{tag}: кадр не из статей клуба {fn}")
        # обоснование: поля, ключи стоят в тексте (posty/obosnovanie.py), куда ведёт – по каналу
        ob = x.get("obosnovanie")
        for s in ob_oshibki(ob, z + " " + t):
            err.append(f"{tag}: {s}")
        if isinstance(ob, dict):
            sl = str(ob.get("ssylka") or "")
            if k == "vk" and sl != VK_SSYLKA:
                err.append(f"{tag}: обоснование: ssylka ВК – «{VK_SSYLKA}», стоит «{sl}»")
            if k == "dzen":
                v_tekste = re.findall(r"https://balance-fit\.ru/[^\s)\]]+", t)
                if v_tekste and not any(u in sl for u in v_tekste):
                    err.append(f"{tag}: обоснование: ssylka Дзена не из ссылок текста {v_tekste[:1]}")
                if not v_tekste and sl != "канал Дзена сети":
                    err.append(f"{tag}: обоснование: ссылки в тексте нет – ssylka «канал Дзена сети»")
        if k == "dzen":
            if not 15 <= len(z) <= 140: err.append(f"{tag}: заголовок {len(z)} знаков")
            if not 2500 <= n <= 5500: err.append(f"{tag}: {n} знаков, нужно 2500–5500")
            if "{img1}" not in t or "{img2}" not in t: err.append(f"{tag}: нет {{img1}}/{{img2}}")
            if len(x.get("kartinki") or []) != 2: err.append(f"{tag}: нужно 2 картинки")
            if f"balance-fit.ru/{BLOG[klub]}?utm_source=dzen" not in t: err.append(f"{tag}: нет ссылки на блог клуба с utm")
            if re.search(r"(?i)(до|про)читайте?\s+(\w+\s+){0,3}на\s+(нашем\s+)?сайте|продолжение\s+на\s+сайте", t):
                err.append(f"{tag}: «дочитать на сайте»")
        elif k == "vk":
            if z: err.append(f"{tag}: у ВК нет заголовка")
            if not 500 <= n <= 1300: err.append(f"{tag}: {n} знаков, нужно 500–1300")
            if re.search(r"https?://|www\.", t): err.append(f"{tag}: ссылка в тексте ВК")
            if len(re.findall(r"#[\wа-яё]+", t, re.I)) > 3: err.append(f"{tag}: хештегов больше трёх")
            if "сообщени" not in t: err.append(f"{tag}: нет призыва написать в сообщения")
            if len(x.get("kartinki") or []) != 1: err.append(f"{tag}: нужна 1 картинка")
        else:
            err.append(f"{tag}: канал не dzen/vk")
    for e in err: print("ОШИБКА", e)
    for v in vn: print("внимание", v)
    print(f"{p.name}: постов {len(posty)} (сети {len(seti)}), ошибок {len(err)}, внимание {len(vn)}")
    return len(err), posty


def po_seti(vse):
    """Сверка всех клубов вместе: на каждую дату графика – один пост ВК и один Дзен, повторы обоснований."""
    err = []
    den = {}
    for klub, posty in vse.items():
        for x in posty:
            den.setdefault((x["data"], x.get("kanal")), []).append(klub)
    d = START
    while d <= KONEC_GRAFIKA:
        for k in ("dzen", "vk"):
            kto = den.pop((d.isoformat(), k), [])
            if len(kto) != 1:
                err.append(f"{d} {k}: постов по сети {len(kto)} ({', '.join(kto) or 'нет'}), нужно 1")
        d += dt.timedelta(days=3)
    for (data, k), kto in sorted(den.items()):
        err.append(f"{data} {k}: вне графика 16.11–18.01 ({', '.join(kto)})")
    err += ob_povtory([(f"{klub} {x['data']} {x.get('kanal')}", x.get("obosnovanie"))
                       for klub, posty in vse.items() for x in posty])
    for e in err: print("ОШИБКА сеть:", e)
    return len(err)


def zapusk(args):
    files = [a for a in args if not a.startswith("--")]
    vsya_set = not files
    files = files or [str(NEDELYA / f"{k}.json") for k in KLUB]
    oshibok, vse = 0, {}
    for f in files:
        n, posty = main(f)
        oshibok += n
        vse[Path(f).stem] = posty
    if vsya_set:
        oshibok += po_seti(vse)
    else:
        pov = ob_povtory([(f"{k} {x['data']} {x.get('kanal')}", x.get("obosnovanie")) for k, v in vse.items() for x in v])
        for e in pov: print("ОШИБКА", e)
        oshibok += len(pov)
    print(f"ИТОГО: ошибок {oshibok}")
    return 1 if oshibok else 0


if __name__ == "__main__":
    sys.exit(zapusk(sys.argv[1:]))
