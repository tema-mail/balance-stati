#!/usr/bin/env python3
"""Статьи для Дзена: проверка и страницы для копирования. Источник – dzen/NN-адрес.md, шапка до ---."""
import glob, html, re, sys
from pathlib import Path
ROOT = Path(__file__).parent; SITE = ROOT / "site"; BASE = "https://tema-mail.github.io/balance-stati/"
CLUB = dict(imperial=("Империал", "borodinskaya/blog"), abricosovo=("Абрикосово", "abricosovo/blog"), admiral=("Адмирал", "admiral/blog"))
BAN = [r"—", r"₽|\bруб", r"\bразов", r"абонемент", r"\bVIP\b", r"WhatsApp", r"спортзал|качалк|джакузи", r"(?<!не )лечит|лечебн|избавит",
       r"идеальн|лучши[йе]|уникальн", r"[−-]\s?\d+ ?кг", r"[A-ZА-ЯЁ]{6,}(?<!ScanMe)", r"\bшок\b|сенсаци"]

def parse(f):
    head, _, body = Path(f).read_text(encoding="utf8").partition("\n---\n")
    m = {}
    for l in head.splitlines():
        if ": " in l:
            k, v = l.split(": ", 1); m[k] = v.strip()
    return m, [b.strip() for b in re.split(r"\n\s*\n", body.strip()) if b.strip()]

def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda x: f'<a href="{x.group(2)}">{x.group(1)}</a>', s)
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)

def lint(m, blocks):
    e = []
    text = "\n".join(blocks)
    n = len(re.findall(r"[0-9A-Za-zА-Яа-яЁё%+-]+", re.sub(r"\]\([^)]+\)", "]", text)))
    if not 440 <= n <= 900: e.append(f"объём {n}")
    if not 15 <= len(m["title"]) <= 100: e.append(f"заголовок {len(m['title'])} знаков")
    if m["title"].count("!") or m["title"].count("?") > 1: e.append("знаки в заголовке")
    for rx in BAN:
        for x in re.finditer(rx, m["title"] + "\n" + text):
            e.append(f"запрет {rx}: …{(m['title'] + chr(10) + text)[max(0, x.start() - 20):x.end() + 20]}…".replace("\n", " "))
    club, feed = CLUB[m["club"]]
    need = f"https://balance-fit.ru/{feed}/{m['slug']}?utm_source=dzen&utm_medium=article&utm_campaign={m['slug']}"
    if need not in text: e.append("нет ссылки на статью сайта с меткой")
    if m["slug"] not in [re.search(r"^slug: (.+)$", Path(a).read_text(encoding="utf8"), re.M).group(1) for a in glob.glob(str(ROOT / "stati/*.md"))]:
        e.append("нет такой статьи сайта")
    if sum(b.startswith("{img") for b in blocks) != 2: e.append("нужно 2 картинки в тексте")
    for b in blocks:
        if not b.startswith(("##", "{img")) and len(b) > 500: e.append(f"абзац {len(b)}: {b[:40]}")
    return e, n

def page(m, blocks, n):
    slug, parts, kit = m["slug"], [], []
    for b in blocks:
        if b.startswith("{img"):
            i = b[4]; u = f"{BASE}img/dzen-{slug}-{i}.jpg"
            parts.append(f'<p class="pic"><img src="img/dzen-{slug}-{i}.jpg" alt=""></p>')
            kit.append(f'<li><a href="{u}" download>Скачать</a> · <button onclick="navigator.clipboard.writeText(\'{u}\')">Ссылка</button></li>')
        elif b.startswith("## "):
            parts.append(f"<h2>{inline(b[3:])}</h2>")
        else:
            parts.append(f"<p>{inline(' '.join(b.split()))}</p>")
    body = "".join(parts)
    cover = f"{BASE}img/dzen-{slug}-0.jpg"
    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="robots" content="noindex,nofollow">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(m['title'])}: Дзен</title>
<style>body{{font:18px/1.55 -apple-system,Arial,sans-serif;max-width:760px;margin:0 auto;padding:20px;color:#111}}img{{max-width:100%;border-radius:8px}}
.kit{{background:#f3f3f3;padding:14px 16px;border-radius:10px;font-size:15px}}button{{padding:8px 12px;margin:3px 6px 3px 0;cursor:pointer}}h2{{margin-top:1.4em}}</style></head><body>
<p><a href="index.html">← Все статьи</a></p>
<div class="kit"><b>Дата:</b> {m['date']} · <b>Клуб:</b> {CLUB[m['club']][0]} · <b>Слов:</b> {n}<br><br>
<button onclick="navigator.clipboard.writeText(document.getElementById('t').innerText)">1. Скопировать заголовок</button>
<button id="c" onclick="copyBody()">2. Скопировать текст</button><br>
<b>3. Обложка:</b> <a href="{cover}" download>скачать</a> · <button onclick="navigator.clipboard.writeText('{cover}')">ссылка</button>
<br><b>4. Картинки в тексте</b> (места отмечены ниже, вставить по ссылке или с компьютера):<ol style="margin:4px 0">{''.join(kit)}</ol></div>
<h1 id="t">{html.escape(m['title'])}</h1><p class="cover"><img src="img/dzen-{slug}-0.jpg" alt=""></p><div id="b">{body}</div>
<script>async function copyBody(){{const d=document.getElementById('b').cloneNode(true);d.querySelectorAll('.pic').forEach(p=>p.remove());
const h=d.innerHTML;await navigator.clipboard.write([new ClipboardItem({{'text/html':new Blob([h],{{type:'text/html'}}),'text/plain':new Blob([d.innerText],{{type:'text/plain'}})}})]);
document.getElementById('c').textContent='Скопировано';}}</script></body></html>"""

def main():
    bad, rows = 0, []
    for f in sorted(glob.glob(str(ROOT / "dzen/*.md"))):
        m, blocks = parse(f); e, n = lint(m, blocks)
        print(("OK " if not e else "ERR"), Path(f).name, n)
        for x in e: print("   ", x)
        bad += bool(e); rows.append((m, n))
        if "--lint" not in sys.argv:
            (SITE / f"dzen-{m['slug']}.html").write_text(page(m, blocks, n), encoding="utf8")
    if "--lint" not in sys.argv:
        tr = "".join(f'<tr><td>{m["date"]}</td><td>{CLUB[m["club"]][0]}</td><td><a href="dzen-{m["slug"]}.html">{html.escape(m["title"])}</a></td><td>{n}</td></tr>' for m, n in rows)
        idx = SITE / "index.html"; s = idx.read_text(encoding="utf8")
        block = f'<h2>Дзен: 7 статей</h2><table><thead><tr><th>Дата</th><th>Клуб</th><th>Статья</th><th>Слов</th></tr></thead><tbody>{tr}</tbody></table>'
        idx.write_text(s.replace('<p><a href="instrukciya.html">', block + '<p><a href="instrukciya.html">'), encoding="utf8")
    print(f"Дзен: {len(rows)}, с ошибками {bad}")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
