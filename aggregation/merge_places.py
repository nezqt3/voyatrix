"""
merge.py  —  второй проход: JSON → CSV

Структура входного JSON (из extract.py):
  [
    {"type": "text",  "id": "paragraph_000015", "uuid": "...", "text": "..."},
    {"type": "image", "id": "image_000014",      "image": "image1.jpg"},
    ...
  ]

Иерархия документа:
  1) NORTH AMERICA            ← материк
      United States           ← страна
      - New York              ← город
        Accommodation (жилье) ← секция (кириллица в скобках)
          Hotels              ← подкатегория
          [image]             ← превью объекта
          1) Night Hotel...   ← объект
            215 West ...      ← адрес
            On the Upper...   ← описание
            https://...       ← booking url → закрывает объект
          [image]             ← превью следующего объекта
          2) The Mayfair...   ← следующий объект

=== Алгоритм привязки изображений ===

Изображение всегда является превью СЛЕДУЮЩЕГО объекта.
Между image и объектом НИКОГДА нет других строк (1626/1637 случаев).
В 11/1637 edge-cases image стоит внутри предыдущего объекта
(после URL, перед следующей секцией), но всё равно принадлежит
следующему объекту. Схема всегда одна из двух:

  Вариант А (стандартный, начало категории):
    Hotels                     ← plain_label (подкатегория)
    [image]                    ← pending_image
    1) Night Hotel Broadway    ← объект забирает pending_image

  Вариант Б (стандартный, продолжение):
    https://booking.com/...    ← url предыдущего объекта
    [image]                    ← pending_image (current = None)
    2) The Mayfair Hotel       ← объект забирает pending_image

  Edge-case (11 штук):
    https://booking.com/...    ← url предыдущего объекта → close_current
    [image ВНУТРИ предыдущего] ← в этот момент current уже None,
                                  поэтому image → pending_image
    Restaurants/cafe (кафе...) ← новая секция
    [image]                    ← ещё одно pending_image (перезаписывает)
    1) Следующий объект        ← забирает pending_image

Итог: 0 или 1 image на объект. image_url = "media/imageN.jpg".

Секции Transport пропускаются автоматически (0 % ссылок в первом проходе).
"""

from pathlib import Path
import json
import csv
import re

from helper import (
    OBJECT_PATTERN,
    SECTION_PATTERN,
    CONTINENT_PATTERN,
    normalize_url,
    is_url,
    clean_name,
    is_city_line,
    is_plain_label,
    find_first_address,
    country_matches_address,
)

BASE_DIR = Path(__file__).parent
INPUT_FILE  = BASE_DIR / "export" / "text.json"
OUTPUT_DIR  = BASE_DIR / "merged_data"
MEDIA_DIR   = "media"          # относительный путь к медиа (от export/)
OUTPUT_DIR.mkdir(exist_ok=True)

CONTINENT_NAMES = {
    "NORTH AMERICA", "SOUTH AMERICA", "EUROPE", "ASIA", "AUSTRALIA", "AFRICA",
}

URL_RATE_THRESHOLD = 0.5       # ниже — секция считается справочной (без мест)


# ------------------------------------------------------------------ #
#  Утилита: путь к изображению → URL-like строка                      #
# ------------------------------------------------------------------ #

def image_url(filename: str) -> str:
    """
    Строим относительный URL вида  media/image1.jpg
    Легко заменить на абсолютный, если картинки переедут на CDN:
        return f"https://cdn.example.com/travel/{filename}"
    """
    return f"{MEDIA_DIR}/{filename}"


# ------------------------------------------------------------------ #
#  Проход 1: какие секции не содержат реальных мест (нет ссылок)?     #
# ------------------------------------------------------------------ #

def compute_section_url_rates(rows: list) -> dict:
    stats: dict      = {}
    current_section  = None
    in_obj           = False
    obj_has_url      = False

    def flush():
        nonlocal in_obj, obj_has_url
        if in_obj and current_section is not None:
            entry = stats.setdefault(current_section, [0, 0])
            entry[0] += 1
            entry[1] += int(obj_has_url)
        in_obj      = False
        obj_has_url = False

    for r in rows:
        if r["type"] == "image":
            continue
        t = r["text"]
        if not t:
            continue
        if SECTION_PATTERN.match(t):
            flush()
            current_section = t.split("(", 1)[0].strip()
        elif is_city_line(t):
            flush()
        elif OBJECT_PATTERN.match(t):
            flush()
            in_obj = True
        elif is_url(t) and in_obj:
            obj_has_url = True

    flush()
    return {
        name: (cnt[1] / cnt[0]) if cnt[0] else 0
        for name, cnt in stats.items()
    }


# ------------------------------------------------------------------ #
#  Проход 2: основной парсинг                                         #
# ------------------------------------------------------------------ #

def merge():
    with open(INPUT_FILE, encoding="utf-8") as f:
        rows: list = json.load(f)

    section_url_rate = compute_section_url_rates(rows)
    skip_sections = {
        name for name, rate in section_url_rate.items()
        if rate < URL_RATE_THRESHOLD
    }
    print(f"Skipped sections: {sorted(skip_sections)}")

    records: list = []

    context = {
        "continent": None,
        "country":   None,
        "city":      None,
        "section":   None,
        "category":  None,
    }

    current       = None   # текущий открытый объект
    skip_section  = False  # текущая секция — справочная
    after_section = False  # ждём подкатегорию (plain_label после секции)
    prev_text     = None   # предыдущая непустая текстовая строка

    # Изображение всегда принадлежит СЛЕДУЮЩЕМУ объекту.
    # Сохраняем его здесь до тех пор, пока объект не появится.
    pending_image: str | None = None

    def close_current():
        nonlocal current
        if not current:
            return
        current["description"] = "\n".join(current["description"]).strip()
        records.append(current)
        current = None

    for row in rows:

        # ── IMAGE ──────────────────────────────────────────────────
        # Изображение почти всегда стоит ПЕРЕД объектом (превью).
        # Если текущий объект ещё открыт (edge-case: 11/1637) —
        # значит URL ещё не пришёл, поэтому pending устанавливаем
        # и в этом случае (объект закроется чуть позже на URL/секции,
        # а image подхватит следующий объект).
        if row["type"] == "image":
            pending_image = image_url(row["image"])
            continue

        t = row["text"].strip()
        if not t:
            continue

        previous_text = prev_text
        prev_text = t

        # ── URL ────────────────────────────────────────────────────
        # URL закрывает объект. После него может прийти plain_label
        # (смена подкатегории: Hotels → Bed&Breakfast → Hostels),
        # поэтому ставим after_section = True.
        if is_url(t):
            if current:
                current["url"] = normalize_url(t)
                close_current()
                after_section = True   # ждём возможную смену подкатегории
            continue

        # ── CONTINENT / страна-в-формате-материка ──────────────────
        if CONTINENT_PATTERN.match(t):
            close_current()
            name       = t.split(")", 1)[1].strip()
            name_clean = re.sub(r"\s*\([A-Z]+\)$", "", name).strip()
            if name in CONTINENT_NAMES:
                context.update(
                    continent=name.title(), country=None,
                    city=None, section=None, category=None,
                )
            else:
                context.update(
                    country=re.sub(r"^The\s+", "", name_clean.title()),
                    city=None, section=None, category=None,
                )
            after_section = False
            continue

        # ── CITY ───────────────────────────────────────────────────
        if is_city_line(t):
            close_current()
            if is_plain_label(previous_text):
                addr = find_first_address(rows, rows.index(row) + 1)
                if addr and country_matches_address(previous_text, addr):
                    context["country"] = previous_text
            if context["country"] is None:
                context["country"] = context["continent"]
            context.update(city=t[2:].strip(), section=None, category=None)
            after_section = False
            continue

        # ── SECTION ────────────────────────────────────────────────
        if SECTION_PATTERN.match(t):
            close_current()
            section_name  = t.split("(", 1)[0].strip()
            skip_section  = section_name in skip_sections
            context.update(
                section=section_name,
                category=None if skip_section else section_name,
            )
            after_section = True    # ждём plain_label-подкатегорию
            continue

        # ── OBJECT ─────────────────────────────────────────────────
        if OBJECT_PATTERN.match(t):
            close_current()

            if skip_section:
                pending_image = None
                after_section = False
                continue

            # Подкатегория (Hotels, Bed&Breakfast…) стоит только
            # сразу после секции или после предыдущей подкатегории,
            # НЕ между двумя объектами одной категории.
            if after_section and is_plain_label(previous_text):
                context["category"] = previous_text

            current = {
                **context,
                "source_id":   row["id"],
                "name":        clean_name(t),
                "address":     "",
                "description": [],
                "url":         "",
                # Одна картинка или None. Картинка всегда приходит
                # непосредственно перед объектом (см. комментарий выше).
                "image_url":   pending_image or "",
            }
            pending_image = None
            after_section = False
            continue

        # ── CONTENT INSIDE OBJECT ──────────────────────────────────
        if current:
            if not current["address"]:
                current["address"] = t
            else:
                current["description"].append(t)

    close_current()

    # ── CSV ────────────────────────────────────────────────────────
    csv_file = OUTPUT_DIR / "places.csv"
    fieldnames = [
        "source_id", "continent", "country", "city",
        "section", "category", "name", "address",
        "description", "url", "image_url",
    ]
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    # ── Сводка ─────────────────────────────────────────────────────
    print(f"\nSaved {len(records)} records → {csv_file}")

    from collections import Counter
    cats = Counter(r["category"] for r in records)
    print("\nКатегории:")
    for cat, cnt in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {cat:35s} {cnt}")

    print(f"\nСтран:        {len(set(r['country'] or '' for r in records))}")
    print(f"Городов:      {len(set(r['city'] for r in records))}")
    print(f"Без country:  {sum(1 for r in records if not r['country'])}")
    print(f"Без url:      {sum(1 for r in records if not r['url'])}")
    print(f"С картинкой:  {sum(1 for r in records if r['image_url'])}")
    print(f"Без картинки: {sum(1 for r in records if not r['image_url'])}")


if __name__ == "__main__":
    merge()