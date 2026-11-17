#!/usr/bin/env python3
"""Проверка обоснования материала (docs/obosnovanie.md): поля на месте, ключи реально стоят в тексте, нет повторов.
Зовут proverka.py постов и build.py статей: oshibki(ob, tekst) -> список строк; povtory(spisok) -> список строк.
Запуск сам по себе: python3 posty/obosnovanie.py  – проходит все posty/**/*.json и stati/*.md, код 1 при ошибках."""
import glob, json, re, sys
from pathlib import Path

POLYA = ("zachem", "vedyot_na", "ssylka", "klyuchi", "spros")
VODA = ("узнаваемост", "лояльност", "вовлечённост", "вовлеченност", "seo-оптимиз", "контент-план", "целевой аудитор",
        "позиционирован")
KOREN = Path(__file__).resolve().parent.parent


def _osnovy(s: str) -> list[str]:
    """Основы слов: первые буквы слова (русская морфология на глаз – до 5 букв хватает, чтобы поймать падежи)."""
    return [w[:max(3, min(5, len(w) - 2))] for w in re.findall(r"[a-zа-яё0-9]+", s.lower().replace("ё", "е")) if len(w) > 2]


def oshibki(ob, tekst: str) -> list[str]:
    if not isinstance(ob, dict):
        return ["нет обоснования"]
    o = []
    for p in POLYA:
        if not ob.get(p):
            o.append(f"обоснование: пусто поле {p}")
    z = str(ob.get("zachem") or "")
    if z and not 40 <= len(z) <= 400:
        o.append(f"обоснование: zachem {len(z)} знаков, надо 40–400")
    for v in VODA:
        if v in z.lower():
            o.append(f"обоснование: вода в zachem – «{v}…»")
    if "—" in json.dumps(ob, ensure_ascii=False):
        o.append("обоснование: длинное тире")
    kl = ob.get("klyuchi") or []
    if not isinstance(kl, list) or not 1 <= len(kl) <= 6:
        o.append("обоснование: klyuchi – список из 1–6 фраз")
        kl = []
    t = " ".join(_osnovy(tekst))
    for k in kl:
        net = [w for w in _osnovy(k) if w not in t]
        if net:
            o.append(f"обоснование: ключа «{k}» нет в тексте (не найдено: {', '.join(net)})")
    return o


def povtory(spisok: list[tuple[str, dict]]) -> list[str]:
    vid, o = {}, []
    for imya, ob in spisok:
        z = re.sub(r"\W+", " ", str((ob or {}).get("zachem") or "").lower()).strip()
        if z and z in vid:
            o.append(f"обоснование: одинаковый zachem у {vid[z]} и {imya}")
        vid.setdefault(z, imya)
    return o


def iz_shapki(md: str) -> tuple[dict, str]:
    shapka, _, telo = md.partition("\n---\n")
    d = dict(re.findall(r"^(\w+):\s*(.*)$", shapka, re.M))
    ob = {"zachem": d.get("zachem", ""), "vedyot_na": d.get("vedyot", ""), "ssylka": d.get("vedyot_url", ""),
          "klyuchi": [k.strip() for k in d.get("klyuchi", "").split(";") if k.strip()], "spros": d.get("spros", "")}
    return ob, " ".join([d.get("h1", ""), d.get("title", ""), telo])


def main():
    vse, plohie, net = [], 0, 0
    for f in sorted(glob.glob(str(KOREN / "posty/**/*.json"), recursive=True)):
        for x in json.loads(Path(f).read_text(encoding="utf8")):
            imya = f"{Path(f).relative_to(KOREN)} {x.get('data')} {x.get('kanal')}"
            ob = x.get("obosnovanie")
            if ob is None:
                net += 1
                continue
            vse.append((imya, ob))
            for s in oshibki(ob, (x.get("zagolovok") or "") + " " + x.get("tekst", "")):
                plohie += 1
                print(f"{imya}: {s}")
    for f in sorted(glob.glob(str(KOREN / "stati/*.md"))):
        ob, tekst = iz_shapki(Path(f).read_text(encoding="utf8"))
        if not ob["zachem"]:
            net += 1
            continue
        vse.append((Path(f).name, ob))
        for s in oshibki(ob, tekst):
            plohie += 1
            print(f"{Path(f).name}: {s}")
    for s in povtory(vse):
        plohie += 1
        print(s)
    print(f"с обоснованием {len(vse)}, без обоснования {net}, ошибок {plohie}")
    sys.exit(1 if plohie or ("--strogo" in sys.argv and net) else 0)


if __name__ == "__main__":
    main()
