#!/usr/bin/env python3
"""Комплект статей Balance: проверка по разделу 3.6, части 1 и 2 для Тильды, страница выдачи.
Запуск: python3 build.py          – проверка и сборка в site/
        python3 build.py --lint   – только проверка
Источник – stati/NN-адрес.md: шапка «ключ: значение» до строки ---, потом текст статьи.
"""
import html, json, re, sys
from pathlib import Path

ROOT = Path(__file__).parent
BASE = "https://balance-fit.ru"

CLUBS = {
    "imperial": dict(name="Империал", city="Краснодар", blog=f"{BASE}/imperial/blog", feed="borodinskaya/blog",
        addr="Краснодар, ул. Бородинская, 137, корп. 2", hours="пн-пт 6:00–23:00, сб-вс 7:00–23:00",
        tel="+7 861 207 27 37", telh="+78612072737", page="/imperial",
        marks=["Бородинская", "207 27 37", "op@balancefit.ru"]),
    "abricosovo": dict(name="Абрикосово", city="Краснодар", blog=f"{BASE}/abricosovo/blog", feed="abricosovo/blog",
        addr="Краснодар, ул. Героя Бочарникова, 4, стр. Б", hours="пн-пт 6:00–23:00, сб-вс 8:00–23:00",
        tel="+7 861 207 27 17", telh="+78612072717", page="/abricosovo",
        marks=["Бочарникова", "207 27 17", "op_abrikosovo@balancefit.ru"]),
    "admiral": dict(name="Адмирал", city="Туапсе", blog=f"{BASE}/admiral/blog", feed="admiral/blog",
        addr="Туапсе, ул. Портовиков, 39, лит. 5", hours="пн-пт 7:00–23:00, сб-вс 8:00–23:00",
        tel="+7 861 205 18 18", telh="+78612051818", page="/admiral",
        marks=["Портовиков", "205 18 18", "opadmiral@balancefit.ru"]),
}
ORDER = {"imperial": ["imperial", "abricosovo", "admiral"],
         "abricosovo": ["abricosovo", "imperial", "admiral"],
         "admiral": ["admiral", "imperial", "abricosovo"]}

LINKS = set("""/blog/bassejn-krasnodar /blog/fitnes-krasnodar /blog/spa-krasnodar /blog/sauna-krasnodar
/blog/semeynyy-fitnes-klub-krasnodar /blog/yoga-krasnodar /blog/hamam-krasnodar /blog/pilates-krasnodar
/blog/akvaaerobika-krasnodar /blog/trenazhyornyy-zal-krasnodar /blog/krossfit-krasnodar
/blog/gruppovye-trenirovki-krasnodar /imperial /imperial/spa /imperial/kids /imperial/kids/services
/abricosovo /abricosovo/schedule /abricosovo/kids /admiral /admiral/schedule /admiral/kids
/admiral/kids/services /admiral/services""".split())

BAN = [(r"₽|\bруб", "цена"), (r"\bразов", "разовое"), (r"абонемент", "абонемент"), (r"\bVIP\b", "VIP"),
       (r"(?-i:\bSPA\b|\bСПА\b)", "SPA"), (r"WhatsApp|ватсап", "WhatsApp"), (r"\bбилет", "билет"),
       (r"в базе|по нашим данным|в материалах|мы не выдумываем", "служебная фраза"),
       (r"спортзал|качалк|джакузи|фитнес-студи", "запрещённое слово"),
       (r"семейн\w+ карт|семейн\w+ визит", "семейная карта"), (r"Balance kids", "латиница"),
       (r"(?<!не )лечит|избавит|оздоров\w+ сосуд|убер[её]т целлюлит|[−-]\s?\d+ ?кг|научим за", "мед. обещание"),
       (r"идеальн|лучши[йе]|уникальн", "клише"), (r"—", "длинное тире"),
       (r"\bпроцедура\b.*лечеб|лечебн", "лечебный эффект")]
VVOD = r"вводн[^.]{0,120}(по желанию|необязательн|принудительн)|(по желанию|необязательн|принудительн)[^.]{0,120}вводн"
ADMIRAL_BAN = r"акватермальн|детск\w+ бассейн|инфракрасн|соляная комнат|зон\w+ релакс|массаж|Balance спа|душ\w* Шарко|Balance кафе|студи\w+ йог"
ABRIC_BAN = r"Balance спа|парковк|душ\w* Шарко|косметолог|акваторнадо|солярий"
HEAD = ["card", "h1", "title", "description", "theme", "query", "club", "slug", "date", "cap1", "cap2", "cap3"]
PROMPTS = ["img0", "img1", "img2", "img3"]


def parse(path):
    raw = path.read_text(encoding="utf8")
    head, _, body = raw.partition("\n---\n")
    meta = {}
    for line in head.splitlines():
        if line.strip():
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    blocks = [b.strip() for b in re.split(r"\n\s*\n", body.strip()) if b.strip()]
    return meta, blocks


def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    return re.sub(r"\*(.+?)\*", r"<em>\1</em>", s)


def plain(s):
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    return s.replace("*", "")


def block_html(b):
    lines = b.split("\n")
    if lines[0].startswith("- "):
        return "<ul>" + "".join(f"<li>{inline(l[2:])}</li>" for l in lines) + "</ul>"
    if re.match(r"\d+\. ", lines[0]):
        return "<ol>" + "".join(f"<li>{inline(re.sub(r'^[0-9]+[.] ', '', l))}</li>" for l in lines) + "</ol>"
    if lines[0].startswith("|"):
        rows = [[c.strip() for c in l.strip("|").split("|")] for l in lines if not re.match(r"^\|[-| ]+\|$", l)]
        th = "".join(f"<th>{inline(c)}</th>" for c in rows[0])
        td = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows[1:])
        return f'<div class="art-table-wrap"><table><thead><tr>{th}</tr></thead><tbody>{td}</tbody></table></div>'
    return f"<p>{inline(' '.join(lines))}</p>"


def sections(blocks):
    """intro-блоки до первого ##, разделы [(заголовок, блоки)]."""
    intro, secs = [], []
    for b in blocks:
        if b.startswith("## "):
            first, _, rest = b.partition("\n")
            secs.append((first[3:].strip(), [rest.strip()] if rest.strip() else []))
        elif secs:
            secs[-1][1].append(b)
        else:
            intro.append(b)
    return intro, secs


def fact(key, i):
    c = CLUBS[key]
    return (f'<a class="fact fact--{i} fact--club" href="{BASE}{c["page"]}"><div class="fact__k">Balance {c["name"]}</div>'
            f'<div class="fact__v">{c["addr"]}<br>{c["hours"]}</div><div class="fact__tel">{c["tel"]}</div></a>')


def foot_club(key):
    c = CLUBS[key]
    return (f'<div class="foot__club"><b><a class="foot__club-name" href="{BASE}{c["page"]}">Balance {c["name"]}</a></b>'
            f'{c["addr"]}<br><a href="tel:{c["telh"]}">{c["tel"]}</a><br><span class="foot__hours">{c["hours"]}</span></div>')


def word_count(blocks):
    return len(re.findall(r"[0-9A-Za-zА-Яа-яЁё°%+-]+", plain(" ".join(blocks)).replace("|", " ")))


def render(meta, blocks):
    club, slug = meta["club"], meta["slug"]
    c = CLUBS[club]
    intro, secs = sections(blocks)
    lead, rest = intro[0], intro[1:]
    mins = max(1, round(word_count(blocks) / 200))
    t = html.escape(meta["theme"], quote=False)
    p1 = ('<div class="bal-page"><div class="shell"><div class="top"><div class="shell top__in">'
          f'<a class="top__logo" href="{BASE}"></a><div class="top__nav"></div><a class="btn btn--lime" href="{BASE}/">Выбрать клуб</a></div></div>'
          f'<div class="hero"><div class="crumbs"><a href="{BASE}">Главная</a><span>/</span><a href="{c["blog"]}">Блог {c["name"]}</a><span>/</span>{t} </div>'
          f'<div class="hero__grid"><div class="hero__text"><div class="eyebrow">{t}</div><h1>{html.escape(meta["h1"], quote=False)}</h1>'
          f'<p class="hero__lead">{inline(lead)}</p><div class="hero__meta"><span>{mins} мин чтения</span></div>'
          f'<div class="hero__actions"><a class="btn btn--action" href="{BASE}/">Выбрать клуб</a></div></div>'
          f'<div class="hero__media"><div class="hero__cover hero__cover--{slug}"></div></div></div></div>'
          '<div class="facts">' + "".join(fact(k, i + 1) for i, k in enumerate(ORDER[club])) + "</div></div></div>")
    body, toc, faq, n = "", "", "", 0
    if rest:
        body += '<div class="sec sec--intro">' + "".join(block_html(b) for b in rest) + "</div>"
    for title, bl in secs:
        if title.startswith("Частые вопросы"):
            items = ""
            for b in bl:
                q, _, a = b.partition("\n")
                items += (f'<div class="faq__item"><div class="faq__q">{inline(q.replace("**", ""))}</div>'
                          f'<div class="faq__a"><p>{inline(" ".join(a.split()))}</p></div></div>')
            faq = f'<div class="faq" id="faq"><h2>Частые вопросы</h2>{items}</div>'
            continue
        if title.startswith("Запишитесь"):
            continue
        n += 1
        fig = ""
        if n <= 3:
            fig = (f'<div class="art-fig art-fig--sec"><div class="art-pic pic--{slug}-sec{n}"></div>'
                   f'<div class="art-cap">{html.escape(meta["cap%d" % n], quote=False)}</div></div>')
        safe = html.escape(title, quote=False)
        body += (f'<div class="sec" data-a="razdel-{n}"><h2><a name="razdel-{n}">{safe}</a></h2>{fig}'
                 + "".join(block_html(b) for b in bl) + "</div>")
        toc += f'<li><a href="#razdel-{n}">{safe}</a></li>'
    foot = ('<div class="foot"><div class="shell"><div class="foot__clubs">' + "".join(foot_club(k) for k in ORDER[club]) +
            '</div><div class="foot__in"><span>Balance – сеть фитнес-клубов в Краснодаре и Туапсе</span><span class="foot__links">'
            '<a href="https://vk.com/balance_krd" rel="noopener" target="_blank">ВКонтакте</a>'
            '<a href="https://t.me/Balance_krd_bot" rel="noopener" target="_blank">Telegram</a>'
            f'<a href="tel:{c["telh"]}">{c["tel"]}</a></span></div></div></div>')
    cta = ('<p>Гостевой визит – целый день в клубе без ограничений по зонам: бассейн, сауны, тренажёрный зал и групповые программы.</p>'
           f'<a class="btn" href="{BASE}/">Гостевой визит</a>')
    p2 = (f'<div class="bal-page"><div class="shell"><div class="grid"><div class="article">{body}{faq}</div><div class="side"><div class="side__card">'
          f'<div class="side__title">Содержание</div><div class="side__bar"><span id="progress"></span></div><ul class="side__nav">{toc}</ul></div>'
          f'<div class="side__cta">{cta}</div></div></div>{foot}</div></div>')
    return p1, p2, n


def lint(path, meta, blocks):
    errs = []
    for k in HEAD + PROMPTS:
        if not meta.get(k):
            errs.append(f"нет поля {k}")
    if errs:
        return errs, 0
    club = meta["club"]
    text = plain("\n\n".join(blocks))
    n = word_count(blocks)
    if not 1150 <= n <= 1400:
        errs.append(f"объём {n} слов (нужно 1150–1400)")
    for b in blocks:
        if not b.startswith(("|", "## ")):
            for line in (b.split("\n") if b[:2] in ("- ", "1.") else [" ".join(b.split("\n"))]):
                if len(plain(line)) > 400:
                    errs.append(f"абзац {len(plain(line))} знаков: {line[:50]}…")
    allt = text + " " + " ".join(meta[k] for k in HEAD)
    for rx, label in BAN:
        for m in re.finditer(rx, allt, re.I):
            errs.append(f"{label}: …{allt[max(0, m.start() - 25):m.end() + 25]}…".replace("\n", " "))
    if re.search(VVOD, allt, re.I | re.S):
        errs.append("вводная по желанию")
    if re.search(r"от \d[\d ]* ?(₽|р\b)", allt):
        errs.append("цена от")
    if len(meta["title"]) > 70:
        errs.append(f"title {len(meta['title'])} знаков")
    if len(meta["description"]) > 160:
        errs.append(f"description {len(meta['description'])} знаков")
    if not meta["title"].endswith(f"| Balance {CLUBS[club]['name']}"):
        errs.append("title без клуба в конце")
    if not re.fullmatch(r"[a-z0-9-]+", meta["slug"]):
        errs.append("адрес не латиницей")
    for mark in CLUBS[club]["marks"]:
        if mark not in text:
            errs.append(f"нет контакта: {mark}")
    for other, c in CLUBS.items():
        if other != club:
            for mark in c["marks"]:
                if mark in text:
                    errs.append(f"чужой контакт: {mark}")
    if club == "admiral":
        for m in re.finditer(ADMIRAL_BAN, text, re.I):
            errs.append(f"нет в Адмирале: …{text[max(0, m.start() - 30):m.end() + 30]}…".replace("\n", " "))
    if club == "abricosovo":
        for m in re.finditer(ABRIC_BAN, text, re.I):
            errs.append(f"нет в Абрикосово: …{text[max(0, m.start() - 30):m.end() + 30]}…".replace("\n", " "))
    links = re.findall(r"\]\(([^)]+)\)", "\n".join(blocks))
    if not 2 <= len(links) <= 4:
        errs.append(f"ссылок {len(links)} (нужно 2–4)")
    own = "/" + CLUBS[club]["feed"] + "/"
    for l in links:
        if l not in LINKS and not l.startswith(own):
            errs.append(f"ссылка не из списка: {l}")
    intro, secs = sections(blocks)
    if len(intro[0]) > 400:
        errs.append("лид длиннее 400")
    titles = [t for t, _ in secs]
    for need in ("Частые вопросы", "Как найти Balance", "Запишитесь"):
        if not any(t.startswith(need) for t in titles):
            errs.append(f"нет раздела «{need}»")
    if not titles[-1].startswith("Запишитесь"):
        errs.append("последний раздел не «Запишитесь»")
    fq = next((bl for t, bl in secs if t.startswith("Частые вопросы")), [])
    if not 5 <= len(fq) <= 6:
        errs.append(f"вопросов {len(fq)} (нужно 5–6)")
    for b in fq:
        if not b.startswith("**") or "\n" not in b:
            errs.append(f"вопрос без формата: {b[:40]}")
    return errs, n


def page(meta, p1, p2, blocks, n):
    """Страница статьи: предпросмотр темой сайта, поля и части для Тильды."""
    slug = meta["slug"]
    c = CLUBS[meta["club"]]
    pics = ""
    for i, cls in enumerate([f"hero__cover--{slug}", f"pic--{slug}-sec1", f"pic--{slug}-sec2", f"pic--{slug}-sec3"]):
        pics += f".bal-page .{cls}{{background-image:url(img/{slug}-{i}.jpg)}}\n"
    fields = [("Лента", c["feed"]), ("Заголовок карточки", meta["card"]), ("H1", meta["h1"]), ("SEO title", meta["title"]),
              ("SEO description", meta["description"]), ("Адрес поста", slug), ("Дата", meta["date"]),
              ("Запрос", meta["query"]), ("Слов", str(n))]
    rows = "".join(f"<tr><th>{k}</th><td>{html.escape(v)}</td></tr>" for k, v in fields)
    prompts = "".join(f"<li><b>{['Главное 4:3', 'Раздел 1 16:9', 'Раздел 2 16:9', 'Раздел 3 16:9'][i]}.</b> {html.escape(meta[f'img{i}'])}</li>" for i in range(4))
    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="robots" content="noindex,nofollow">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(meta['card'])} – {c['name']}</title>
<link rel="stylesheet" href="theme.css"><style>{pics}
.kit{{font:15px/1.5 -apple-system,Arial,sans-serif;max-width:1100px;margin:0 auto;padding:20px;color:#111}}
.kit table{{border-collapse:collapse;width:100%}}.kit th,.kit td{{border:1px solid #ccc;padding:6px 10px;text-align:left;vertical-align:top}}.kit th{{width:190px;font-weight:600}}
.kit textarea{{width:100%;height:90px;font:12px monospace}}.kit button{{padding:8px 14px;margin:6px 0;cursor:pointer}}.kit a{{color:#06c}}</style></head><body>
<div class="kit"><p><a href="index.html">← Все статьи</a></p><h2>{html.escape(meta['card'])} · {c['name']}</h2><table>{rows}</table>
<h3>Часть 1 для Тильды</h3><textarea id="p1" readonly>{html.escape(p1)}</textarea><button onclick="navigator.clipboard.writeText(p1.value)">Скопировать часть 1</button>
<h3>Часть 2 для Тильды</h3><textarea id="p2" readonly>{html.escape(p2)}</textarea><button onclick="navigator.clipboard.writeText(p2.value)">Скопировать часть 2</button>
<h3>Промты картинок</h3><ol>{prompts}</ol><h3>Как будет выглядеть</h3></div>{p1}{p2}</body></html>"""


def index(items):
    rows = ""
    for m, n in items:
        c = CLUBS[m["club"]]
        rows += (f'<tr><td>{m["date"][:5]}</td><td>{c["name"]}</td><td><a href="{m["slug"]}.html">{html.escape(m["card"])}</a></td>'
                 f'<td>{html.escape(m["query"])}</td><td>{n}</td></tr>')
    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="robots" content="noindex,nofollow">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Balance: 14 статей</title>
<style>body{{font:16px/1.5 -apple-system,Arial,sans-serif;max-width:1000px;margin:0 auto;padding:20px;color:#111}}
table{{border-collapse:collapse;width:100%}}th,td{{border-bottom:1px solid #ddd;padding:8px;text-align:left}}a{{color:#06c}}</style></head><body>
<h1>Balance: 14 статей на 06–19.11.2026</h1>
<!--STATUS-->
<table><thead><tr><th>Дата</th><th>Клуб</th><th>Статья</th><th>Запрос</th><th>Слов</th></tr></thead><tbody>{rows}</tbody></table>
<p><a href="instrukciya.html">Инструкция</a></p></body></html>"""


def main():
    only_lint = "--lint" in sys.argv
    files = sorted((ROOT / "stati").glob("*.md"))
    bad, items = 0, []
    site = ROOT / "site"
    site.mkdir(exist_ok=True)
    for f in files:
        meta, blocks = parse(f)
        errs, n = lint(f, meta, blocks)
        print(f"{'OK ' if not errs else 'ERR'} {f.name} {n} слов")
        for e in errs:
            print("    " + e)
        bad += bool(errs)
        items.append((meta, n))
        if not only_lint and meta.get("cap3"):
            p1, p2, secs = render(meta, blocks)
            for part in (p1, p2):
                assert part.count("<div") == part.count("</div>"), f.name
            (site / f"{meta['slug']}.html").write_text(page(meta, p1, p2, blocks, n), encoding="utf8")
            (site / f"{meta['slug']}.json").write_text(json.dumps(dict(p1=p1, p2=p2), ensure_ascii=False), encoding="utf8")
    items.sort(key=lambda it: (it[0].get("date", "")[:10], it[0].get("date", "")[11:]))
    if not only_lint:
        status = (ROOT / "docs/status.html").read_text(encoding="utf8") if (ROOT / "docs/status.html").exists() else ""
        (site / "index.html").write_text(index(items).replace("<!--STATUS-->", status), encoding="utf8")
        (site / "theme.css").write_text((ROOT / "theme/custom.css").read_text(encoding="utf8"), encoding="utf8")
        doc = (ROOT / "docs/instrukciya-2026-11-05.md").read_text(encoding="utf8")
        (site / "instrukciya.html").write_text('<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="robots" content="noindex,nofollow">'
            '<meta name="viewport" content="width=device-width,initial-scale=1"><title>Balance: инструкция</title></head>'
            '<body style="max-width:1000px;margin:0 auto;padding:20px"><p><a href="index.html">← Все статьи</a></p>'
            f'<pre style="white-space:pre-wrap;font:15px/1.5 -apple-system,Arial,sans-serif">{html.escape(doc)}</pre></body></html>', encoding="utf8")
    print(f"Итого: {len(files)} файлов, с ошибками {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
