#!/usr/bin/env python3
"""Открывает на Тильде статьи, чей час настал (tilda/raspisanie.tsv). Будущую дату Тильда показывает сразу,
поэтому статьи лежат черновиками, а этот скрипт раз в час (launchd ru.deford.balance-stati) публикует их в срок.
Вышедшие пишет в tilda/opublikovano.log. Ключ – ~/.config/tilda/mcp_token_balance.
  python3 publish_due.py          – опубликовать то, чей срок прошёл
  python3 publish_due.py --dry    – только показать
  python3 publish_due.py --drafts – пересохранить будущие черновиками с датами из расписания"""
import json, subprocess, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tilda_post import args

ROOT = Path(__file__).parent
LOG = ROOT / "tilda/opublikovano.log"
TZ = timezone(timedelta(hours=7))  # пояс ленты Asia/Bangkok
TOKEN = (Path.home() / ".config/tilda/mcp_token_balance").read_text().strip()


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
    now = datetime.now(TZ).strftime("%Y-%m-%d %H:%M")
    for line in (ROOT / "tilda/raspisanie.tsv").read_text(encoding="utf8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        slug, uid, date = line.split("\t")
        if slug in done:
            continue
        if mode == "--drafts":
            print(date, slug, "черновик", call("feeds_update_post", args(slug, uid, date)))
        elif date <= now:
            if mode == "--dry":
                print("пора:", date, slug)
                continue
            print(now, slug, call("feeds_update_post", args(slug, uid, date, "y")), flush=True)
            with LOG.open("a") as f:
                f.write(slug + "\n")


if __name__ == "__main__":
    main()
