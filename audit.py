#!/usr/bin/env python3
"""Проверка: у каждой статьи сайта и Дзена есть картинки на живой странице. Запуск: python3 audit.py"""
import glob, re, subprocess, sys
from pathlib import Path
BASE = "https://tema-mail.github.io/balance-stati"
ok = lambda u: subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "-m", "15", u], capture_output=True, text=True).stdout == "200"
miss, total = [], 0
for kind, pat, slots, pre in (("сайт", "stati/*.md", 4, ""), ("дзен", "dzen/*.md", 3, "dzen-")):
    for f in sorted(glob.glob(pat)):
        slug = re.search(r"^slug: (.+)$", Path(f).read_text(encoding="utf8"), re.M).group(1)
        for i in range(slots):
            total += 1
            if not ok(f"{BASE}/img/{pre}{slug}-{i}.jpg"):
                miss.append(f"{kind} {slug} {i}")
print(f"картинок {total - len(miss)} из {total}")
print("\n".join(miss))
sys.exit(1 if miss else 0)
