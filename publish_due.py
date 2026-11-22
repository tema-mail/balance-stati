#!/usr/bin/env python3
"""Открывает на Тильде статьи, чей час настал (tilda/raspisanie.tsv). Будущую дату Тильда показывает сразу,
поэтому статьи лежат черновиками, а этот скрипт раз в час (launchd ru.deford.balance-stati) публикует их в срок.
Вышедшие пишет в tilda/opublikovano.log. Ключ – ~/.config/tilda/mcp_token_balance.
  python3 publish_due.py          – опубликовать то, чей срок прошёл
  python3 publish_due.py --dry    – только показать
  python3 publish_due.py --drafts – пересохранить будущие черновиками с датами из расписания"""
import html, json, os, re, subprocess, sys, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from build import CLUBS, parse
from tilda_post import args

ROOT = Path(__file__).parent
LOG = Path(os.environ.get("BALANCE_TILDA_LOG", ROOT / "tilda/opublikovano.log"))
TZ = timezone(timedelta(hours=7))  # пояс ленты Asia/Bangkok
TOKEN = Path(os.environ.get("BALANCE_TILDA_TOKEN", Path.home() / ".config/tilda/mcp_token_balance")).read_text().strip()
USTARELO = {"ждёт «да» Артёма на выкладку в Тильду (расписание статей Баланса)"}


def meta(slug):
    return parse(next((ROOT / "stati").glob(f"*-{slug}.md")))[0]


def uids():
    return dict(line.split("\t") for line in (ROOT / "tilda/uids.tsv").read_text(encoding="utf8").splitlines()
                if "\t" in line)


def public_url(slug):
    m = meta(slug)
    return f"https://balance-fit.ru/{CLUBS[m['club']]['feed']}/{slug}"


def proverit_live(slug):
    """Публикация считается вышедшей только после 200, точных title/canonical и нативной разметки статьи."""
    m, url = meta(slug), public_url(slug)
    r = subprocess.run(["/usr/bin/curl", "-sS", "-L", "--max-time", "60", "-w",
                        "\n%{http_code}\n%{url_effective}", url],
                       capture_output=True, text=True)
    if r.returncode or r.stdout.count("\n") < 2:
        raise RuntimeError(f"проверка {url}: curl {r.returncode}: {r.stderr[-200:]}")
    body, code, effective = r.stdout.rsplit("\n", 2)
    title = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
    title = html.unescape(title.group(1)).strip() if title else ""
    canonical = f'<link rel="canonical" href="{url}">'
    if effective != url or code != "200" or title != m["title"] or canonical not in body or "bal-page" not in body:
        raise RuntimeError(f"не доехало: {url}, final={effective}, http={code}, title={title!r}, canonical={canonical in body}")
    return url


def otmetit_v_zavode(slug, uid, url):
    """На сервере синхронизирует только точную статью Balance после публичной проверки."""
    baza = os.environ.get("ZAVOD_DB")
    if not baza:
        return
    app = os.environ.get("ZAVOD_APP", "/opt/zavod/app")
    if app not in sys.path:
        sys.path.insert(0, app)
    from engine import db as zdb
    con = zdb.connect(baza)
    row = con.execute("SELECT c.id,c.site_id,c.status,c.url,c.prichina,json_extract(c.dannye,'$.tilda_uid') tilda_uid "
                      "FROM stati_chernoviki c "
                      "JOIN sites s ON s.id=c.site_id WHERE s.slug='balance' AND c.slug=?", (slug,)).fetchone()
    if not row:
        return
    if row["tilda_uid"] != uid:
        raise RuntimeError(f"Завод: UID {row['tilda_uid']!r} вместо {uid!r} у {slug}")
    if row["status"] == "vylozhen" and row["url"] == url:
        if row["prichina"] not in USTARELO:
            return
    con.execute("UPDATE stati_chernoviki SET status='vylozhen',url=?,prichina='',updated=? WHERE id=?",
                (url, time.time(), row["id"]))
    zdb.sobytie(con, "vykladka", f"Tilda Feed: доехало: {url}", site_id=row["site_id"], chernovik=row["id"])


def call(tool, arguments):
    """Через curl: у python.org-питона на маке нет корневых сертификатов. Ключ уходит в curl через stdin, не в аргументах."""
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": tool, "arguments": arguments}}, ensure_ascii=False)
    tmp = ROOT / "tilda/.body.json"
    tmp.write_text(body, encoding="utf8")
    cfg = (f'header = "Authorization: Bearer {TOKEN}"\nheader = "Content-Type: application/json"\n'
           'header = "Accept: application/json, text/event-stream"\nheader = "MCP-Protocol-Version: 2025-06-18"\n'
           f'data-binary = "@{tmp}"\nurl = "https://tilda.ru/api/mcp/"\nsilent\nmax-time = 180\n')
    out = subprocess.run(["/usr/bin/curl", "-K", "-"], input=cfg, capture_output=True, text=True, check=True).stdout
    tmp.unlink()
    r = json.loads(out)
    if "error" in r:
        raise RuntimeError(r["error"])
    text = r["result"]["content"][0]["text"]
    if r["result"].get("isError"):
        raise RuntimeError(text)
    return text


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    done = set(LOG.read_text().split()) if LOG.exists() else set()
    uidy = uids()
    now = datetime.now(TZ).strftime("%Y-%m-%d %H:%M")
    for line in (ROOT / "tilda/raspisanie.tsv").read_text(encoding="utf8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        slug, uid, date = line.split("\t")
        if uidy.get(slug) != uid:
            raise RuntimeError(f"расписание: UID {uid!r} не совпал с uids.tsv {uidy.get(slug)!r} у {slug}")
        if slug in done:
            continue
        if mode == "--drafts":
            print(date, slug, "черновик", call("feeds_update_post", args(slug, uid, date)))
        elif date <= now:
            if mode == "--dry":
                print("пора:", date, slug)
                continue
            print(now, slug, call("feeds_update_post", args(slug, uid, date, "y")), flush=True)
            url = proverit_live(slug)
            LOG.parent.mkdir(parents=True, exist_ok=True)
            with LOG.open("a") as f:
                f.write(slug + "\n")
            otmetit_v_zavode(slug, uid, url)
    if mode not in ("--dry", "--drafts"):
        for slug in sorted(set(LOG.read_text().split()) if LOG.exists() else set()):
            try:
                uid = uidy.get(slug)
                if not uid:
                    raise RuntimeError("нет UID в tilda/uids.tsv")
                otmetit_v_zavode(slug, uid, proverit_live(slug))
            except Exception as e:
                print(f"синхронизация {slug}: {e}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
