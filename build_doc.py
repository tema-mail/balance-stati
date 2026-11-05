#!/usr/bin/env python3
"""Инструкция: docs/instrukciya-*.md -> site/instrukciya.html. Без зависимостей, только стандартная библиотека."""
import html, re
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "docs/instrukciya-2026-11-05.md"
OUT = ROOT / "site/instrukciya.html"


def inline(s):
    codes = []
    def keep(m):
        codes.append(f"<code>{html.escape(m.group(1), quote=False)}</code>")
        return f"\0{len(codes) - 1}\0"
    s = re.sub(r"`([^`]+)`", keep, s)
    s = html.escape(s, quote=False)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"(?<![\"'>/])(https?://[^\s<)]+)", r'<a href="\1">\1</a>', s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", s)
    return re.sub(r"\0(\d+)\0", lambda m: codes[int(m.group(1))], s)


ITEM = re.compile(r"^(\s*)(?:[-*]|\d+\.)\s+(.*)$")


def render_list(lines):
    """Список с вложенностью: отступ определяет уровень, продолжения строк приклеиваются к пункту."""
    out, stack, i = [], [], 0
    while i < len(lines):
        line = lines[i]
        m = ITEM.match(line)
        if not m:
            i += 1
            continue
        ind, text = len(m.group(1)), m.group(2)
        tag = "ol" if re.match(r"\s*\d+\.", line) else "ul"
        i += 1
        while i < len(lines) and not ITEM.match(lines[i]) and lines[i].strip() and not lines[i].lstrip().startswith("```"):
            text += " " + lines[i].strip()
            i += 1
        while stack and stack[-1][0] > ind:
            out.append(f"</li></{stack.pop()[1]}>")
        if not stack or stack[-1][0] < ind:
            out.append(f"<{tag}><li>")
            stack.append((ind, tag))
        else:
            out.append("</li><li>")
        check = re.match(r"\[( |x)\]\s*(.*)", text)
        if check:
            mark = "☑" if check.group(1) == "x" else "☐"
            out.append(f'<span class="box">{mark}</span> {inline(check.group(2))}')
        else:
            out.append(inline(text))
        # код внутри пункта
        if i < len(lines) and lines[i].lstrip().startswith("```"):
            i += 1
            code = []
            while i < len(lines) and not lines[i].lstrip().startswith("```"):
                code.append(lines[i].strip())
                i += 1
            i += 1
            out.append(code_block("\n".join(code)))
    while stack:
        out.append(f"</li></{stack.pop()[1]}>")
    return "".join(out)


def code_block(text):
    return (f'<div class="code"><button type="button" onclick="copyCode(this)">Скопировать</button>'
            f"<pre>{html.escape(text, quote=False)}</pre></div>")


def render(lines):
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if not s or s == "---":
            i += 1
        elif s.startswith("```"):
            i += 1
            code = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1
            out.append(code_block("\n".join(code)))
        elif s.startswith("### "):
            out.append(f"<h3>{inline(s[4:])}</h3>")
            i += 1
        elif s.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                if not re.match(r"^\|[\s:|-]+\|$", lines[i].strip()):
                    rows.append([c.strip() for c in re.split(r"(?<!\\)\|", lines[i].strip().strip("|"))])
                i += 1
            th = "".join(f"<th>{inline(c)}</th>" for c in rows[0])
            td = "".join("<tr>" + "".join(f"<td>{inline(c.replace(chr(92) + '|', '|'))}</td>" for c in r) + "</tr>" for r in rows[1:])
            out.append(f'<div class="table"><table><thead><tr>{th}</tr></thead><tbody>{td}</tbody></table></div>')
        elif s.startswith(">"):
            q = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                q.append(lines[i].strip().lstrip("> "))
                i += 1
            out.append(f'<div class="note">{inline(" ".join(q))}</div>')
        elif ITEM.match(line):
            start = i
            while i < len(lines):
                cur = lines[i]
                if not cur.strip():
                    nxt = lines[i + 1] if i + 1 < len(lines) else ""
                    if ITEM.match(nxt) or nxt.startswith("   "):
                        i += 1
                        continue
                    break
                if cur.startswith(("## ", "### ", "|", ">")):
                    break
                i += 1
            out.append(render_list([l for l in lines[start:i] if l.strip()]))
        else:
            para = []
            while i < len(lines):
                cur = lines[i].strip()
                if not cur or cur == "---" or cur.startswith(("#", "|", ">", "```")) or ITEM.match(lines[i]):
                    break
                para.append(cur)
                i += 1
            out.append(f"<p>{inline(' '.join(para))}</p>")
    return "".join(out)


TOP = """
<h1>Как делать статьи Balance</h1>
<p class="lead">Инструкция для того, кто пишет статьи для блогов клубов и выкладывает их в Тильду и Дзен. Всё, что нужно по делу, в трёх карточках ниже. Подробности – в разделах, они открываются по клику.</p>
<div class="cards">
<div class="card"><h2>Статья на сайт</h2><ol>
<li>Выберите клуб и тему, которой ещё нет. <a href="#s1">Куда и что уже вышло</a></li>
<li>Отдайте нейросети факты и готовый промт. <a href="#s7">Промт</a></li>
<li>Проверьте по чек-листу: цен нет, контакты этого клуба. <a href="#s3">Правила</a></li>
<li>Подберите 4 картинки. <a href="#s5">Какие</a></li>
<li>Выложите в ленту клуба. <a href="#s8">Как у наших статей</a></li>
</ol></div>
<div class="card"><h2>Картинки</h2><ol>
<li><b>Сначала живое фото этого клуба.</b></li>
<li>Нужны люди – настоящий кадр клуба, людей добавляет ChatGPT, зал не меняем.</li>
<li>Снимка нет – крупный план без интерьера: руки, полотенце, еда.</li>
</ol><p class="stop">Нельзя: придуманный зал, сауна, кабинет или стойка. Фото другого клуба.</p><a href="#s5">Подробнее</a></div>
<div class="card"><h2>Дзен</h2><ol>
<li>История про читателя, а не справка: 440–900 слов.</li>
<li>Текст свой, не копия статьи с сайта.</li>
<li>Обложка обязательна, заголовок без обмана и кричащих знаков.</li>
<li>Выходит после статьи на сайте и ведёт на неё ссылкой с меткой.</li>
</ol><a href="#s10">Подробнее</a></div>
</div>
<div class="ready"><b>Партия на ноябрь уже написана.</b> Если вы выкладываете её, инструкция почти не нужна: откройте <a href="index.html">страницу со статьями</a>, у каждой есть поля и кнопки «Скопировать».</div>
<h2 class="more">Подробности по разделам</h2>
"""

CSS = """
*{box-sizing:border-box}body{margin:0;background:#f4f4f2;color:#1b1b1b;font:17px/1.55 -apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif}
.wrap{max-width:980px;margin:0 auto;padding:20px 20px 80px}.back{font-size:15px}a{color:#0b5fd0}
h1{font-size:36px;line-height:1.15;margin:18px 0 10px}.lead{font-size:19px;max-width:760px;margin:0 0 24px}
.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.card{background:#fff;border-radius:14px;padding:18px 20px;font-size:16px}
.card h2{margin:0 0 10px;font-size:21px}.card ol{margin:0 0 10px;padding-left:20px}.card li{margin-bottom:7px}.stop{background:#fdecea;border-radius:8px;padding:8px 10px;margin:0 0 10px;font-size:15px}
.ready{background:#e9f6df;border-radius:12px;padding:14px 18px;margin:16px 0 0}.more{font-size:24px;margin:34px 0 12px}
details{background:#fff;border-radius:12px;margin-bottom:8px}summary{cursor:pointer;padding:15px 20px;font-size:19px;font-weight:600;list-style-position:inside}
details[open] summary{border-bottom:1px solid #e6e6e2}.body{padding:6px 20px 18px;overflow-wrap:anywhere}.body h3{font-size:19px;margin:22px 0 8px}
.body li{margin-bottom:6px}.box{font-size:18px}.table{overflow-x:auto;margin:12px 0}table{border-collapse:collapse;width:100%;font-size:15px}th,td{border:1px solid #deded9;padding:7px 10px;text-align:left;vertical-align:top;overflow-wrap:normal}th{background:#f4f4f2}
code{background:#efefec;border-radius:4px;padding:1px 5px;font-size:.88em;overflow-wrap:anywhere}.code{position:relative;margin:12px 0}.code pre{background:#1f2125;color:#eee;border-radius:10px;padding:40px 14px 14px;margin:0;font-size:13px;line-height:1.45;white-space:pre-wrap;overflow-wrap:anywhere;max-height:360px;overflow:auto}
.code button{position:absolute;top:8px;right:8px;background:#fff;border:0;border-radius:6px;padding:5px 10px;font-size:13px;cursor:pointer}.note{background:#fff6dd;border-radius:10px;padding:12px 14px;margin:12px 0}
@media(max-width:800px){.cards{grid-template-columns:1fr}h1{font-size:30px}body{font-size:16px}.wrap{padding:14px 14px 60px}.body{padding:6px 14px 16px}summary{padding:14px}}
"""

JS = """
function copyCode(b){navigator.clipboard.writeText(b.nextElementSibling.innerText);b.textContent='Скопировано';setTimeout(function(){b.textContent='Скопировать'},1500)}
function openHash(){var e=document.getElementById(location.hash.slice(1));if(e&&e.tagName==='DETAILS'){e.open=true;e.scrollIntoView()}}
addEventListener('hashchange',openHash);openHash();
"""

TITLES = {"1": "Куда публикуем и что уже вышло", "2": "Как выбрать тему", "3": "Как написать статью: правила и чек-лист", "4": "Факты о клубах",
          "5": "Картинки", "6": "Простая выкладка в Тильду", "7": "Готовые промты для нейросети", "8": "Выкладка как у наших статей: дизайн, код, проверка",
          "9": "Партия на 06–12 ноября: график", "10": "Дзен"}


def main():
    text = SRC.read_text(encoding="utf8")
    parts = re.split(r"^## ", text, flags=re.M)
    secs = ""
    for part in parts[1:]:
        head, _, body = part.partition("\n")
        m = re.match(r"(\d+)\.", head)
        sid = f"s{m.group(1)}" if m else "changes"
        title = TITLES[m.group(1)] if m else "Что изменилось в инструкции"
        secs += f'<details id="{sid}"><summary>{html.escape(title)}</summary><div class="body">{render(body.splitlines())}</div></details>'
    page = (f'<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="robots" content="noindex,nofollow">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>Как делать статьи Balance</title><style>{CSS}</style></head>'
            f'<body><div class="wrap"><p class="back"><a href="index.html">← Все статьи</a></p>{TOP}{secs}</div><script>{JS}</script></body></html>')
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(page, encoding="utf8")
    print("инструкция:", page.count("<details"), "разделов,", len(page) // 1024, "КБ")


if __name__ == "__main__":
    main()
