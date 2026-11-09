#!/usr/bin/env python3
"""План 90 статей (30 дней × 3 клуба) -> site/plan90.html. Темы – plan90/temy.py, частоты – semantika/*.json (Wordstat через XMLRiver, 10.11.2026)."""
import html, json, re
from datetime import date, timedelta
from pathlib import Path
import sys
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "plan90"))
from temy import T

SEM = ROOT / "semantika"
W = {}
for r in ("35", "1058", "225"):
    W[r] = {}
    for f in (f"k-{r}.json", f"k2-{r}.json"):
        if (SEM / f).exists():
            W[r].update(json.loads((SEM / f).read_text()))
NOISE = re.compile(r"порно|секс|эро|голы|видео|смотреть|скачать|купить|цена|отзыв|фото|wildberries|озон|ozon|авито|бесплатно|1|2|3")
START = date(2026, 11, 15)
CLUBS = {
    "abr": ("Абрикосово", "Краснодар", "balance-fit.ru/abricosovo/blog",
            "Balance Абрикосово, ул. им. Героя Георгия Бочарникова, 4, стр. Б; тренажёрный зал Life Fitness и Hammer Strength, функциональная зона, студия пилатеса и реформер, бассейн, хаммам, финская и инфракрасная сауны, соляная комната, массажный кабинет (10+ видов), Balance кафе с КБЖУ, InBody, Детский клуб"),
    "imp": ("Империал", "Краснодар", "balance-fit.ru/imperial/blog",
            "Balance Империал, ул. Бородинская, 137, к. 2; Balance спа (30+ видов массажа, косметология лица, лазерная эпиляция, ногтевая студия, душ Шарко, акваторнадо, солярий Luxura X8), бассейн 25 м и детский +32 °C, хаммам, сауны, соляная комната, зал Life Fitness и Hammer Strength, парковка"),
    "adm": ("Адмирал", "Туапсе", "balance-fit.ru/admiral/blog",
            "Balance Адмирал, Туапсе, ул. Портовиков, 39, лит. 5; зал Nautilus и Star Trac, Cycle-студия (45 минут), групповые программы, пилатес на реформере, бассейн 25 м на 4 дорожки, финская и солевая сауны, хаммам, Детский клуб, ScanMe, парковка"),
}


def num(r, k):
    v = W[r].get(k)
    if not v or "err" in v:
        return None
    return v.get("total")


def fmt(n):
    return "нет данных" if n is None else f"{n:,}".replace(",", " ")


def extra(k):
    src = W["225"].get(k) or {}
    if not src.get("popular"):
        src = W["35"].get(k) or {}
    out = []
    for t, n in (src.get("popular") or [])[1:]:
        if NOISE.search(t) or t == k:
            continue
        out.append((t, n))
        if len(out) == 6:
            break
    return out


def seo_why(x, krd, tua, rf, city):
    loc = krd if x["club"] != "adm" else tua
    s = [f"Спрос в месяц: {fmt(rf)} по России, {fmt(krd)} в Краснодаре, {fmt(tua)} в Туапсе (Wordstat, все формы запроса, 10.11.2026)."]
    if x["club"] == "adm":
        s.append("Местный спрос в Туапсе маленький, поэтому статья берёт общероссийский информационный спрос, а Туапсе даёт ей привязку к клубу и карточке на картах.")
    if "коммерция" in x["intent"]:
        s.append(f"Смешанная выдача: человек выбирает процедуру и место – статья ведёт с ответа к услуге клуба в {('Краснодаре' if city == 'Краснодар' else 'Туапсе')}.")
    else:
        s.append("Информационный интент: в выдаче статьи и медиа, блог клуба с экспертным ответом туда попадает; продажу закрывает блок про клуб в конце.")
    s.append("Своей статьи на этот интент на balance-fit.ru нет: сверено с 70 адресами блогов и 21 статьёй ноябрьской партии, каннибализации нет.")
    return " ".join(s)


def card(i, x):
    krd, tua, rf = num("35", x["key"]), num("1058", x["key"]), num("225", x["key"])
    name, city, blog, facts = CLUBS[x["club"]]
    d = START + timedelta(days=i)
    ex = extra(x["key"])
    exs = ", ".join(f"{html.escape(t)} <small>{fmt(n)}</small>" for t, n in ex) or "—"
    flag = f'<p class="flag">⚠ {html.escape(x["flag"])}</p>' if x["flag"] else ""
    return f"""<article class="t"><div class="top"><span class="day">День {i + 1} · {d:%d.%m}</span><span class="int">{html.escape(x['intent'])}</span></div>
<h3>{html.escape(x['title'])}</h3>
<p class="key">Главный ключ: <b>{html.escape(x['key'])}</b> <span class="chip">РФ {fmt(rf)}</span><span class="chip">Краснодар {fmt(krd)}</span><span class="chip">Туапсе {fmt(tua)}</span></p>
<p class="ex"><b>Дополнительные ключи:</b> {exs}</p>
<dl><dt>Почему зайдёт в поиске</dt><dd>{html.escape(seo_why(x, krd, tua, rf, city))} Угол статьи: {html.escape(x['angle'])}.</dd>
<dt>AEO – прямой ответ</dt><dd>Ответ на главный вопрос в первых 2–3 фразах под H1, его можно забрать в быстрый ответ Яндекса и блок Google. Формат: {html.escape(x['aeo'])}. Каждый раздел понятен отдельно, FAQ из 3–5 вопросов из подсказок Wordstat с разметкой FAQPage.</dd>
<dt>GEO и ИИ (Алиса, ChatGPT, Perplexity)</dt><dd>Нейросети цитируют источники с проверяемыми фактами и названными сущностями. В статье: {html.escape(facts)}. Оговорки «когда к врачу» и без обещаний результата в цифрах – по нашей методике AEO/GEO такие фрагменты модели забирают охотнее. Автор и дата, разметка Article и LocalBusiness, ссылка на карточку клуба.</dd></dl>{flag}</article>"""


CSS = """*{box-sizing:border-box}body{margin:0;background:#f4f4f2;color:#1b1b1b;font:16px/1.5 -apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif}
.wrap{max-width:1000px;margin:0 auto;padding:20px 16px 80px}a{color:#0b5fd0}h1{font-size:32px;line-height:1.15;margin:14px 0 8px}
.lead{font-size:17px;max-width:780px}.nav{position:sticky;top:0;background:#f4f4f2;padding:10px 0;z-index:2;display:flex;gap:8px;flex-wrap:wrap}
.nav a{background:#1f2125;color:#fff;text-decoration:none;border-radius:20px;padding:7px 14px;font-size:15px}
h2{font-size:26px;margin:34px 0 6px}.sub{color:#555;margin:0 0 14px}
.t{background:#fff;border-radius:14px;padding:16px 18px;margin-bottom:12px}.top{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;font-size:13px;color:#666}
.day{font-weight:600;color:#1b1b1b}.int{background:#eef3ff;border-radius:10px;padding:2px 8px}h3{font-size:20px;margin:8px 0}
.chip{display:inline-block;background:#f0f0ec;border-radius:10px;padding:1px 8px;margin-left:6px;font-size:13px}.key,.ex{margin:6px 0}.ex small{color:#777}
dl{margin:10px 0 0}dt{font-weight:600;margin-top:10px}dd{margin:3px 0 0}.flag{background:#fff3cd;border-radius:8px;padding:8px 10px;margin:12px 0 0}
.box{background:#fff;border-radius:14px;padding:14px 18px;margin:14px 0}table{border-collapse:collapse;width:100%;font-size:14px}td,th{border-bottom:1px solid #e6e6e2;padding:6px;text-align:left}
@media(max-width:700px){h1{font-size:26px}}"""


def main():
    by = {c: [x for x in T if x["club"] == c] for c in CLUBS}
    flags = sum(1 for x in T if x["flag"])
    body = [f"""<p><a href="index.html">← Все статьи</a></p><h1>План: 90 статей на 30 дней</h1>
<p class="lead">По одной статье в день на каждый клуб, с {START:%d.%m} по {START + timedelta(days=29):%d.%m.%Y}. Темы выбраны по спросу Wordstat (снят 10.11.2026 через XMLRiver, ~13 ₽), сверены с уже вышедшими статьями, чтобы не было двух страниц на один запрос. Ничего не выложено на сайт – это план для согласования.</p>
<div class="box"><b>Как читать.</b> У каждой темы: главный ключ и его частота в месяц, дополнительные ключи (подсказки Wordstat по России), интент, почему статья зайдёт в поиске (SEO), как она даёт прямой ответ (AEO) и почему её будут цитировать нейросети (GEO). Жёлтым отмечено то, что нужно подтвердить у клуба до написания – {flags} тем.</div>
<div class="box"><b>Правила для всех 90.</b> Одна тема – одна страница на весь сайт: два клуба Краснодара и Адмирал пишут о разном. Факты о клубах – только из раздела 4 инструкции. Без обещаний килограммов и лечебного эффекта. Картинки – сначала живые фото клуба, потом гибрид (кадр клуба + люди), потом крупный план без интерьера.</div>
<nav class="nav">""" + "".join(f'<a href="#{c}">{CLUBS[c][0]} · 30</a>' for c in CLUBS) + "</nav>"]
    for c, xs in by.items():
        name, city, blog, _ = CLUBS[c]
        body.append(f'<h2 id="{c}">{name} ({city})</h2><p class="sub">Блог: {blog} · 30 статей</p>')
        body += [card(i, x) for i, x in enumerate(xs)]
    page = (f'<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="robots" content="noindex,nofollow">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>План 90 статей Balance</title><style>{CSS}</style></head>'
            f'<body><div class="wrap">{"".join(body)}</div></body></html>')
    (ROOT / "site/plan90.html").write_text(page, encoding="utf8")
    miss = [x["key"] for x in T if num("225", x["key"]) is None]
    print("план:", len(T), "тем, флагов", flags, "| без частоты РФ:", miss)


if __name__ == "__main__":
    main()
