#!/usr/bin/env python3
"""Проверка публикаций Google Карт (Google Business Profile) Баланса: posty/google/<клуб>.json. Код 0 – ошибок нет.
Основа – posty/yandex/proverka.py. Правила площадки – как в заводе (engine/ploshchadki.py: GoogleKarty,
ZAPRETY_KART, TELEFON), слова – красный список Баланса (data_spiski/balance.tsv). Завод не импортируем –
правила переписаны сюда, при правке завода сверить.
Сверх Яндекса: 500–900 знаков (жёстко 100–1500), телефон – стоп, ровно одно фото и только настоящий кадр
клуба (строка «img<N>: настоящее фото» в статье), кадр не повторяется в соседних постах клуба и не больше
двух раз, кнопка ssylka – страница клуба https с utm и кодом 200, тема не повторяет тему Яндекса того же
клуба в ±3 дня, нет фраз из posty/yandex, posty/2026-11-16, dzen/, stati/.
Обоснование «зачем мы это сделали» (docs/obosnovanie.md) – у каждой публикации, проверка posty/obosnovanie.py:
поля, ключи стоят в тексте, ssylka = кнопка поста, zachem не повторяется ни у одной публикации; без обоснования – ошибка.
Запуск: python3 posty/google/proverka.py [файлы…] [--bez-seti] (без файлов – все три клуба)."""
import csv, json, re, subprocess, sys
from datetime import date
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from obosnovanie import oshibki as ob_oshibki, povtory as ob_povtory

ROOT = Path(__file__).resolve().parents[2]
TSV = Path.home() / "Sites/zavod-ai-sfera/data_spiski/balance.tsv"
STUDIYA = TSV.with_name("studiya.tsv")
KLUB = {"abricosovo": "abrikosovo", "imperial": None, "admiral": "admiral"}
IMYA = {"abricosovo": "Balance Абрикосово", "imperial": "Balance Империал", "admiral": "Balance Адмирал"}
DATY = ("2026-11-20", "2026-11-23", "2026-11-26", "2026-11-29", "2026-12-02", "2026-12-05", "2026-12-08",
        "2026-12-11", "2026-12-14", "2026-12-17", "2026-12-20", "2026-12-23", "2026-12-26", "2026-12-29")
URL_IMG = "https://tema-mail.github.io/balance-stati/img/"
UTM = "?utm_source=google_maps&utm_medium=organic&utm_campaign=gbp_news&utm_content="
KONEC = "Подробности – по кнопке."
# кадры, которые смотрели глазами и не берём: чужие вывески за окном (LADA, автоцентр), чужой зал, логотип TRX
NE_BRAT = ("fitnes-klub-s-bassejnom-krasnodar-0.jpg", "detskij-bassejn-krasnodar-2.jpg", "kak-ubrat-zhivot-krasnodar-1.jpg")
SLOP = r"(?i)в современном мире|давайте разбер|важно отметить|не просто \w+, а|в заключение|играет важную роль|ключ к успеху|пространство для|мы рады"
# тема поста по slug: Google не повторяет тему Яндекса того же клуба в ±3 дня
TEMY = {"cycle": r"cycle", "reformer": r"reformer|pilates", "akvaprog": r"akvaprogramm|akvaaerob", "bani": r"akvaterm|saun|infrakras|solyan|hamam",
        "zal": r"zal|scanme|inbody|hammer|kardio|funkcional|trener|trening", "spa": r"spa|massazh|akvatornado|sharko|kosmetolog|manikyur|pedikyur",
        "kafe": r"kafe|zavtrak|kbzhu", "rezhim": r"vyhodn|prazdnichn|rezhim", "plavanie": r"bassejn|plavan|shkola-plav",
        "deti": r"detsk|detyam|shkol|sad|nyanya|bebi|lager|elki|rozhdeniya|rebenok|igrov"}

# engine/ploshchadki.py (завод, 16.11.2026)
TELEFON = r"(?:\+7|\b8)[\s\-(]*\d{3}[\s\-)]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}"
RAZRYADKA = r"(?<![\w])(?:[А-Яа-яЁё] ){3,}[А-Яа-яЁё](?![\w])"
ZAPRETY_KART = (
    (TELEFON, "телефон в тексте – Google отклонит публикацию"),
    (r"\b[А-ЯЁ]{6,}\b", "слово капсом – модерация отклонит"),
    (RAZRYADKA, "р а з р я д к а – модерация отклонит"),
    (r"(?s)!.*!.*!", "много «!» – модерация отклонит"),
    (r"(?s)(?:[\U0001F300-\U0001FAFF☀-➿].*){3,}", "больше двух эмодзи – модерация отклонит"),
    (r"(?i)\bдо\s*/\s*после\b", "«до/после» – отклоняют"),
)
# правила задания сверх завода
SVOI = (
    (r"\b[A-Z]{6,}\b", "латиница капсом"),
    (r"(?s)!.*!", "больше одного «!»"),
    (r"(?i)https?://|www\.|\b[\w.-]+\.(?:ru|рф|com|net|org|by)\b", "ссылка / адрес сайта – ссылка только кнопкой"),
    (r"\d{3}[\s-]?\d{2}[\s-]?\d{2}", "цифры телефона"),
    (r"(?i)телефон\w* клуба|по телефону", "отсылка к телефону"),
    (r"@", "почта или ник"),
    (r"(?i)звонит|позвонит|\bзвонок", "«звоните»"),
    (r"(?i)скидк|акци[яиюей]\b|распродаж|промокод|бесплатн|подар\w* карт|сертификат", "скидка / акция / подарок – нет в фактах"),
    (r"(?i)гостев|пробн\w* (заняти|тренировк|визит)", "гостевой визит / пробное – нет в разделе 4 фактов"),
    (r"(?i)instagram|инстаграм|telegram|телеграм|вконтакте|\bвк\b|whatsapp|ютуб|youtube", "соцсети"),
    (r"(?i)\bvip|премиальн", "VIP и премиальные карты не упоминаем"),
)


def krasnyy(klub):
    out = []
    for r in csv.DictReader(TSV.open(encoding="utf8"), delimiter="\t"):
        g = r["gde"]
        if g == "balance" or (KLUB[klub] and g == f"balance/{KLUB[klub]}"):
            out.append((r["regex"], r.get("isklyuchenie") or "", r["uroven"], r["prichina"]))
    # общие правила завода: слой студии для всех и площадка «карты» (data_spiski/studiya.tsv) – их завод
    # применяет при загрузке построчно; без них новость проходит здесь и встаёт СТОПом в заводе (было 17.11)
    for r in csv.DictReader(STUDIYA.open(encoding="utf8"), delimiter="\t"):
        if (r["sloy"], r["gde"]) in (("studiya", "*"), ("ploshchadka", "karty")):
            out.append(("(?m)" + r["regex"], "", "STOP", r["prichina"]))
    return out


def nastoyashchie(klub):
    """Файлы site/img, которые в статьях клуба помечены «настоящее фото клуба»."""
    out = set()
    for md in (ROOT / "stati").glob("*.md"):
        h = {}
        for l in md.read_text(encoding="utf8").splitlines():
            m = re.match(r"^(club|slug|img\d):\s*(.*)", l)
            if m: h.setdefault(m.group(1), m.group(2))
        if h.get("club") != klub: continue
        for i in range(4):
            if "настоящ" in h.get(f"img{i}", ""):
                out.add(f"{h['slug']}-{i}.jpg")
    return out


def otpechatok(fn):
    """Разностный хеш 9×8 – одинаковый кадр в разных обрезках даёт близкий отпечаток."""
    im = Image.open(ROOT / "site/img" / fn).convert("L").resize((9, 8))
    px = list(im.tobytes())
    return [px[r * 9 + c] > px[r * 9 + c + 1] for r in range(8) for c in range(8)]


def odin_kadr(a, b):
    return sum(x != y for x, y in zip(otpechatok(a), otpechatok(b))) <= 12


def kod(url, follow=False):
    """Код ответа через curl (у питона на маке нет корневых сертификатов)."""
    cmd = ["curl", "-sI", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "20", url]
    if follow: cmd.insert(1, "-L")
    r = subprocess.run(cmd, capture_output=True, text=True)
    return int(r.stdout[-3:]) if r.stdout[-3:].isdigit() else r.stdout or r.stderr


def slova(t):
    return re.findall(r"[а-яёa-z0-9]+", t.lower().replace("ё", "е"))


def shingly(t, n=8):
    w = slova(t)
    return {" ".join(w[i:i + n]) for i in range(len(w) - n + 1)}


def korpus(n=8):
    """8-словные куски всех прошлых текстов: Яндекс, Дзен и ВК недели, Дзен, статьи сайта.
    8 слов – чтобы ловить повтор фразы, а не общий факт («бассейн на 25 метров с 4 дорожками»)."""
    sh = set()
    for f in list((ROOT / "posty/yandex").glob("*.json")) + list((ROOT / "posty/2026-11-16").glob("*.json")):
        for x in json.loads(f.read_text(encoding="utf8")):
            sh |= shingly(x.get("tekst", ""), n)
    for md in list((ROOT / "dzen").glob("*.md")) + list((ROOT / "stati").glob("*.md")):
        sh |= shingly(md.read_text(encoding="utf8"), n)
    return sh


def temy(slug):
    return {k for k, rx in TEMY.items() if re.search(rx, slug)}


def proverit(f, set_url, kor, kor5):
    p = Path(f)
    klub = p.stem
    posty = json.loads(p.read_text(encoding="utf8"))
    err, vn = [], []
    rl, real = krasnyy(klub), nastoyashchie(klub)
    yandex = json.loads((ROOT / "posty/yandex" / f"{klub}.json").read_text(encoding="utf8"))
    if [x.get("data") for x in posty] != list(DATY):
        err.append(f"даты {[x.get('data') for x in posty]}, нужно {list(DATY)}")
    if len({x.get("slug") for x in posty}) != len(posty): err.append("slug повторяется")
    if len({x.get("tema") for x in posty}) != len(posty): err.append("тема повторяется")
    for x in posty:
        t, z, s = x.get("tekst") or "", x.get("zagolovok"), x.get("slug") or ""
        tag = f"{klub} {x.get('data')}"
        if x.get("kanal") != "google_karty": err.append(f"{tag}: канал не google_karty")
        if z != "": err.append(f"{tag}: заголовок должен быть пустой строкой (у Google его нет)")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", s) or not s.startswith(klub + "-"):
            err.append(f"{tag}: slug не латиница-через-дефис с кодом клуба")
        if not 100 <= len(t) <= 1500: err.append(f"{tag}: {len(t)} знаков – Google примет только 100–1500")
        elif not 500 <= len(t) <= 900: err.append(f"{tag}: {len(t)} знаков, нужно 500–900")
        abz = [a for a in t.split("\n\n") if a.strip()]
        if not 3 <= len(abz) <= 5: err.append(f"{tag}: абзацев {len(abz)}, нужно 3–5")
        if IMYA[klub] not in t: err.append(f"{tag}: нет названия «{IMYA[klub]}»")
        if not t.rstrip().endswith(KONEC): err.append(f"{tag}: конец не «{KONEC}»")
        if "—" in t: err.append(f"{tag}: длинное тире")
        if re.search(r"\.\.\.|…", t): err.append(f"{tag}: многоточие")
        if re.search(r"₽|\bруб|\bот \d", t): err.append(f"{tag}: похоже на цену")
        if re.search(SLOP, t): err.append(f"{tag}: штамп «{re.search(SLOP, t).group(0)}»")
        for rx, pr in ZAPRETY_KART + SVOI:
            m = re.search(rx, t)
            if m: err.append(f"{tag}: {pr} («{m.group(0)[:40]}»)")
        bel = (r"Balance|Адмирал\w*|Абрикосово|Империал\w*|Туапсе|Краснодар\w*|Детск\w+|Cycle[\w-]*|Aqua|Mix|Noodles|Power|"
               r"Life|Fitness|Hammer|Strength|Nautilus|Star|Trac|ScanMe|InBody|КБЖУ|Шарко|Баунти|Горячий|Мангомания|Мужской|"
               r"Восточная|Будь|Балансе|Яндекс|Картах|Хорошее|Особенно|Лидер|Бородинской|Героя|Георгия|Бочарникова|Нептуна")
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
        povtor = sorted(shingly(t) & kor)
        if povtor: err.append(f"{tag}: фразы из прошлых текстов: {povtor[:3]}")
        # заход (первая фраза) – свой: ни одного куска в 5 слов из прошлых текстов
        pervaya = re.split(r"(?<=[.?!])\s", t, maxsplit=1)[0]
        if shingly(pervaya, 5) & kor5: err.append(f"{tag}: заход повторяет прошлый текст: {sorted(shingly(pervaya, 5) & kor5)[:2]}")
        # тема Яндекса того же клуба в ±3 дня
        d = date.fromisoformat(x["data"])
        for y in yandex:
            if abs((date.fromisoformat(y["data"]) - d).days) <= 3 and temy(s) & temy(y["slug"]):
                err.append(f"{tag}: тема пересекается с Яндексом {y['data']} «{y['tema']}»")
        # фото
        k = x.get("kartinki") or []
        if len(k) != 1: err.append(f"{tag}: фото {len(k)}, у Google ровно одно")
        for u in k:
            fn = u.rsplit("/", 1)[-1]
            if not u.startswith(URL_IMG): err.append(f"{tag}: картинка не с {URL_IMG}: {u}")
            if not (ROOT / "site/img" / fn).exists(): err.append(f"{tag}: нет файла site/img/{fn}"); continue
            if fn in NE_BRAT: err.append(f"{tag}: кадр в стоп-листе {fn}")
            if fn not in real: err.append(f"{tag}: {fn} – не настоящее фото своего клуба (нейросеть или чужой клуб)")
            if set_url and (c := kod(u)) != 200: err.append(f"{tag}: {fn} отвечает {c}")
        # кнопка
        sl = x.get("ssylka") or ""
        if not re.fullmatch(rf"https://balance-fit\.ru/{klub}{re.escape(UTM)}{re.escape(s)}", sl):
            err.append(f"{tag}: ssylka не https://balance-fit.ru/{klub}{UTM}{s}: {sl}")
        elif set_url and (c := kod(sl, follow=True)) != 200:
            err.append(f"{tag}: кнопка отвечает {c}")
        # обоснование: поля и ключи (posty/obosnovanie.py), ведёт туда же, куда кнопка
        ob = x.get("obosnovanie")
        for o in ob_oshibki(ob, (z or "") + " " + t):
            err.append(f"{tag}: {o}")
        if isinstance(ob, dict) and ob.get("ssylka") != sl:
            err.append(f"{tag}: обоснование: ssylka не равна кнопке поста")
    # один кадр: не в соседних постах клуба и не больше двух раз
    fn = [x["kartinki"][0].rsplit("/", 1)[-1] for x in posty if x.get("kartinki")]
    if all((ROOT / "site/img" / f).exists() for f in fn):
        for i in range(len(fn) - 1):
            if odin_kadr(fn[i], fn[i + 1]): err.append(f"{klub}: один кадр в соседних постах {posty[i]['data']} и {posty[i+1]['data']}")
        for i, a in enumerate(fn):
            n = sum(odin_kadr(a, b) for b in fn)
            if n > 2: err.append(f"{klub}: кадр {a} стоит {n} раз (можно не больше двух)")
            elif n == 2 and i == min(j for j, b in enumerate(fn) if odin_kadr(a, b)):
                vn.append(f"{klub}: кадр {a} повторён (не в соседних – можно)")
    for e in err: print("ОШИБКА", e)
    for v in vn: print("внимание", v)
    print(f"{p.name}: публикаций {len(posty)}, длины {[len(x['tekst']) for x in posty]}, ошибок {len(err)}, внимание {len(vn)}")
    return posty, len(err)


def main(args):
    set_url = "--bez-seti" not in args
    files = [a for a in args if not a.startswith("--")] or [str(Path(__file__).parent / f"{k}.json") for k in IMYA]
    kor, kor5 = korpus(), korpus(5)
    vse, oshibok = {}, 0
    for f in files:
        posty, n = proverit(f, set_url, kor, kor5)
        vse[Path(f).stem] = posty
        oshibok += n
    pov = ob_povtory([(f"{k} {x.get('data')}", x.get("obosnovanie")) for k, v in vse.items() for x in v])
    for o in pov: print("ОШИБКА", o)
    oshibok += len(pov)
    if len(vse) > 1:
        for d in DATY:   # в один день у разных клубов – разные темы
            den = [(k, x) for k, v in vse.items() for x in v if x["data"] == d]
            if len({x["tema"] for _, x in den}) != len(den):
                print("ОШИБКА", d, "одинаковые темы у клубов"); oshibok += 1
            for i, (k1, a) in enumerate(den):
                for k2, b in den[i + 1:]:
                    obshchie = temy(a["slug"]) & temy(b["slug"])
                    if obshchie: print("внимание", d, k1, k2, "близкие темы:", ", ".join(sorted(obshchie)))
        # одни и те же фразы в разных публикациях Google
        vse_p = [(k, x) for k, v in vse.items() for x in v]
        for i, (k1, a) in enumerate(vse_p):
            for k2, b in vse_p[i + 1:]:
                o = {x for x in shingly(a["tekst"]) & shingly(b["tekst"]) if not re.search(r"\d|подробности", x)}
                if o: print("внимание повтор фразы", k1, a["data"], "/", k2, b["data"], ":", sorted(o)[0])
    print(f"ИТОГО: ошибок {oshibok}")
    return 1 if oshibok else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
