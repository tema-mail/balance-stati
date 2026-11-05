#!/usr/bin/env python3
"""Настоящие фото клубов: id – номер в каталоге снимков копии сайта (~/Sites/balance-fit/public/_t).
Режет под формат статьи и пишет site/img/<адрес>-<слот>.jpg. Запуск: python3 photos.py <каталог.json>"""
import json, sys
from pathlib import Path
from PIL import Image, ImageOps
REAL = {
 "limfodrenazhnyj-massazh-krasnodar": {3: (186, "Зона релакса, клуб «Абрикосово», Краснодар")},
 "silovye-trenirovki-krasnodar": {0: (72, ""), 2: (78, "Тренажёрный зал, клуб «Абрикосово», Краснодар")},
 "trenazhernyj-zal-dlya-zhenshchin-krasnodar": {0: (123, "")},
 "infrakrasnaya-sauna-krasnodar": {2: (91, "Бассейн, клуб «Абрикосово», Краснодар"), 3: (45, "Сауна, клуб «Абрикосово», Краснодар")},
 "pitanie-do-i-posle-trenirovki-krasnodar": {0: (125, ""), 1: (188, "Блюдо Balance кафе, клуб «Абрикосово», Краснодар")},
 "trenirovki-posle-40-krasnodar": {2: (180, "Функциональная зона, клуб «Абрикосово», Краснодар")},
 "fitnes-ili-trenazhernyj-zal-krasnodar": {2: (22, "Тренажёрный зал, клуб «Империал», Краснодар")},
 "fitnes-klub-s-bassejnom-krasnodar": {0: (162, "")},
 "kak-nachat-hodit-v-trenazhernyj-zal-krasnodar": {2: (124, "Тренажёрный зал, клуб «Империал», Краснодар")},
 "rastyazhka-tuapse": {2: (111, "Студия групповых программ, клуб «Адмирал», Туапсе")},
 "hamam-tuapse": {0: (41, ""), 2: (137, "Бассейн, клуб «Адмирал», Туапсе"), 3: (77, "Финская сауна, клуб «Адмирал», Туапсе")},
 "kak-pohudet-v-trenazhernom-zale-tuapse": {0: (14, ""), 2: (140, "Тренажёрный зал, клуб «Адмирал», Туапсе")},
 "skolko-raz-v-nedelyu-hodit-v-zal-tuapse": {0: (55, ""), 3: (182, "Тренажёрный зал, клуб «Адмирал», Туапсе")},
 "chto-vzyat-v-fitnes-klub-tuapse": {3: (56, "Бассейн, клуб «Адмирал», Туапсе")},
 "plavanie-dlya-pohudeniya-tuapse": {0: (49, ""), 3: (165, "Бассейн, клуб «Адмирал», Туапсе")},
 "kak-ne-brosit-trenirovki-tuapse": {3: (133, "Cycle-студия, клуб «Адмирал», Туапсе")},
}
def main(cat):
    R = json.load(open(cat, encoding="utf8"))
    used = {}
    for slug, slots in REAL.items():
        for slot, (rid, cap) in slots.items():
            assert rid not in used, (rid, used.get(rid), slug); used[rid] = slug
            src = str(Path.home() / "Sites/balance-fit" / R[rid]["f"])
            ratio = (4, 3) if slot == 0 else (16, 9)
            size = (1200, 900) if slot == 0 else (1200, 675)
            im = ImageOps.fit(Image.open(src).convert("RGB"), size, Image.LANCZOS, centering=(0.5, 0.55))
            out = Path("site/img") / f"{slug}-{slot}.jpg"; im.save(out, quality=84, optimize=True)
            f = next(Path("stati").glob(f"*-{slug}.md")); s = f.read_text(encoding="utf8").split("\n")
            for i, l in enumerate(s):
                if l.startswith(f"img{slot}: "): s[i] = f"img{slot}: настоящее фото клуба, каталог {rid}, {Path(R[rid]['f']).name}"
                if cap and l.startswith(f"cap{slot}: "): s[i] = f"cap{slot}: {cap}"
            f.write_text("\n".join(s), encoding="utf8")
    print("настоящих фото:", len(used))
if __name__ == "__main__":
    main(sys.argv[1])
