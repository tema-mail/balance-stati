#!/usr/bin/env python3
"""Проверка новостей Яндекс Бизнеса Баланса: posty/yandex/<клуб>.json. Код 0 – ошибок нет.
Правила площадки – как в заводе (engine/ploshchadki.py: YandexBiznes, ZAPRETY_KART, RAZRYADKA, TELEFON),
слова – красный список Баланса (data_spiski/balance.tsv). Завод не импортируем – правила переписаны сюда,
при правке завода сверить. Запуск: python3 posty/yandex/proverka.py [файлы…] (без аргументов – все три клуба)."""
import csv, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TSV = Path.home() / "Sites/zavod-ai-sfera/data_spiski/balance.tsv"
KLUB = {"abricosovo": "abrikosovo", "imperial": None, "admiral": "admiral"}
IMYA = {"abricosovo": "Balance Абрикосово", "imperial": "Balance Империал", "admiral": "Balance Адмирал"}
DATY = ("2026-11-16", "2026-11-19", "2026-11-22", "2026-11-25", "2026-11-28")
NE_BRAT = ("bal-admiral-klub-1", "bal-admiral-klub-2", "bal-admiral-spa-1")
URL_IMG = "https://tema-mail.github.io/balance-stati/img/"
SLOP = r"(?i)в современном мире|давайте разбер|важно отметить|не просто \w+, а|в заключение|играет важную роль|ключ к успеху"

# engine/ploshchadki.py (завод, 16.11.2026)
TELEFON = r"(?:\+7|\b8)[\s\-(]*\d{3}[\s\-)]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}"
RAZRYADKA = r"(?<![\w])(?:[А-Яа-яЁё] ){3,}[А-Яа-яЁё](?![\w])"
ZAPRETY_KART = (
    (r"\b[А-ЯЁ]{6,}\b", "слово капсом – модерация отклонит"),
    (RAZRYADKA, "р а з р я д к а – модерация отклонит"),
    (r"(?s)!.*!.*!", "много «!» – модерация отклонит"),
    (r"(?s)(?:[\U0001F300-\U0001FAFF☀-➿].*){3,}", "больше двух эмодзи – модерация отклонит"),
    (r"(?i)\bдо\s*/\s*после\b", "«до/после» – Яндекс Бизнес отклоняет"),
)
# правила задания сверх завода: латинский капс от 6, второй «!», контакты, «звоните», акции
SVOI = (
    (r"\b[A-Z]{6,}\b", "латиница капсом"),
    (r"(?s)!.*!", "больше одного «!»"),
    (r"(?i)https?://|www\.|\b[\w.-]+\.(?:ru|рф|com|net|org|by)\b", "ссылка / адрес сайта"),
    (TELEFON, "телефон"),
    (r"\d{3}[\s-]?\d{2}[\s-]?\d{2}", "цифры телефона"),
    (r"@", "почта или ник"),
    (r"(?i)звонит|позвонит|\bзвонок", "«звоните»"),
    (r"(?i)скидк|акци[яиюей]\b|распродаж|промокод|бесплатн", "скидка / акция / бесплатно – нет в фактах"),
    (r"(?i)убывающ", "акция «Убывающая скидка» – не наш факт"),
    (r"(?i)instagram|инстаграм|telegram|телеграм|вконтакте|\bвк\b|whatsapp|ютуб|youtube", "соцсети"),
    (r"(?i)\bvip|премиальн", "VIP и премиальные карты не упоминаем"),
)


def krasnyy(klub):
    out = []
    for r in csv.DictReader(TSV.open(encoding="utf8"), delimiter="\t"):
        g = r["gde"]
        if g == "balance" or (KLUB[klub] and g == f"balance/{KLUB[klub]}"):
            out.append((r["regex"], r.get("isklyuchenie") or "", r["uroven"], r["prichina"]))
    return out


def kadry_kluba(klub):
    out = set()
    for md in list((ROOT / "stati").glob("*.md")) + list((ROOT / "dzen").glob("*.md")):
        h = dict(l.split(": ", 1) for l in md.read_text(encoding="utf8").split("---")[0].splitlines() if ": " in l)
        if h.get("club") == klub and h.get("slug"):
            out.add(("dzen-" if md.parent.name == "dzen" else "") + h["slug"])
    return out


def otvet_200(url):
    """Код ответа через curl -sI (как велит задание; у питона на маке нет корневых сертификатов)."""
    r = subprocess.run(["curl", "-sI", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "20", url],
                       capture_output=True, text=True)
    return int(r.stdout) if r.stdout.isdigit() else r.stdout or r.stderr


def proverit(f, set_url=True):
    p = Path(f)
    klub = p.stem
    posty = json.loads(p.read_text(encoding="utf8"))
    err, vn = [], []
    rl, kadry = krasnyy(klub), kadry_kluba(klub)
    if [x.get("data") for x in posty] != list(DATY):
        err.append(f"даты {[x.get('data') for x in posty]}, нужно {list(DATY)}")
    if len({x.get("slug") for x in posty}) != len(posty):
        err.append("slug повторяется")
    if len({x.get("tema") for x in posty}) != len(posty):
        err.append("тема повторяется")
    for x in posty:
        t, z = x.get("tekst") or "", x.get("zagolovok")
        tag = f"{klub} {x.get('data')}"
        if x.get("kanal") != "yandex_biznes": err.append(f"{tag}: канал не yandex_biznes")
        if z != "": err.append(f"{tag}: заголовок должен быть пустой строкой")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", x.get("slug") or ""): err.append(f"{tag}: slug не латиница-через-дефис")
        if not 500 <= len(t) <= 1000: err.append(f"{tag}: {len(t)} знаков, нужно 500–1000")
        abz = [a for a in t.split("\n\n") if a.strip()]
        if not 3 <= len(abz) <= 5: err.append(f"{tag}: абзацев {len(abz)}, нужно 3–5")
        if IMYA[klub] not in t: err.append(f"{tag}: нет названия «{IMYA[klub]}»")
        if "маршрут" not in abz[-1].lower(): vn.append(f"{tag}: в конце нет мягкого шага (маршрут / карточка)")
        if "—" in t: err.append(f"{tag}: длинное тире")
        if re.search(r"\.\.\.|…", t): err.append(f"{tag}: многоточие")
        if re.search(r"₽|\bруб|\bот \d", t): err.append(f"{tag}: похоже на цену")
        if re.search(SLOP, t): err.append(f"{tag}: штамп «{re.search(SLOP, t).group(0)}»")
        for rx, pr in ZAPRETY_KART:
            m = re.search(rx, t)
            if m: err.append(f"{tag}: ZAPRETY_KART: {pr} («{m.group(0)[:40]}»)")
        for rx, pr in SVOI:
            m = re.search(rx, t)
            if m: err.append(f"{tag}: {pr} («{m.group(0)[:40]}»)")
        # имена людей не выдумываем: слово с заглавной не в начале предложения и не из белого списка – смотреть глазами
        bel = r"Balance|Адмирал|Абрикосово|Империал|Туапсе|Краснодар\w*|Детск\w+|Cycle[\w-]*|Aqua|Mix|Noodles|Power|Life|Fitness|Hammer|Strength|Nautilus|Star|Trac|ScanMe|InBody|КБЖУ|Шарко|Баунти|Горячий|Мангомания|Мужской|Восточная|Будь|Балансе"
        for m in re.finditer(r"(?<=[^.\n«–] )([A-ZА-ЯЁ][\w-]+)", t):
            if not re.fullmatch(bel, m.group(1)): vn.append(f"{tag}: слово с заглавной «{m.group(1)}» – не имя ли")
        for rx, isk, ur, pr in rl:
            try:
                m = re.search(rx, t)
            except re.error:
                vn.append(f"красный список: не разобрался регэксп {rx[:40]}")
                continue
            if m and not (isk and re.search(isk, t)):
                (err if ur == "STOP" else vn).append(f"{tag}: красный список ({ur}): {pr} («{m.group(0)}»)")
        k = x.get("kartinki") or []
        if not 1 <= len(k) <= 2: err.append(f"{tag}: картинок {len(k)}, нужно 1–2")
        for u in k:
            fn = u.rsplit("/", 1)[-1]
            if not u.startswith(URL_IMG): err.append(f"{tag}: картинка не с {URL_IMG}: {u}")
            if not (ROOT / "site/img" / fn).exists(): err.append(f"{tag}: нет файла site/img/{fn}")
            if any(b in fn for b in NE_BRAT): err.append(f"{tag}: запрещённый кадр {fn}")
            if re.sub(r"-\d+\.jpg$", "", fn) not in kadry: err.append(f"{tag}: кадр не из статей клуба {fn}")
            if set_url:
                s = otvet_200(u)
                if s != 200: err.append(f"{tag}: {fn} отвечает {s}")
    for e in err: print("ОШИБКА", e)
    for v in vn: print("внимание", v)
    print(f"{p.name}: новостей {len(posty)}, длины {[len(x['tekst']) for x in posty]}, ошибок {len(err)}, внимание {len(vn)}")
    return posty, len(err)


def main(args):
    set_url = "--bez-seti" not in args
    files = [a for a in args if not a.startswith("--")] or [str(Path(__file__).parent / f"{k}.json") for k in IMYA]
    vse, oshibok = {}, 0
    for f in files:
        posty, n = proverit(f, set_url)
        vse[Path(f).stem] = posty
        oshibok += n
    if len(vse) > 1:   # в один день у разных клубов – разные темы и разные кадры
        for d in DATY:
            temy = [(k, x["tema"]) for k, v in vse.items() for x in v if x["data"] == d]
            if len({t for _, t in temy}) != len(temy):
                print("ОШИБКА", d, "одинаковые темы у клубов"); oshibok += 1
        kadry = [u for v in vse.values() for x in v for u in x["kartinki"]]
        povtor = sorted({u.rsplit("/", 1)[-1] for u in kadry if kadry.count(u) > 1})
        if povtor: print("внимание кадр стоит больше чем в одной новости:", ", ".join(povtor))
    print(f"ИТОГО: ошибок {oshibok}")
    return 1 if oshibok else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
