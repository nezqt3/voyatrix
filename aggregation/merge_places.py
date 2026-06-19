from pathlib import Path
from urllib.parse import urlparse, urlsplit
import json
import csv
import re

BASE_DIR = Path(__file__).parent

INPUT_FILE = BASE_DIR / "export" / "text.json"
OUTPUT_DIR = BASE_DIR / "merged_data"

OUTPUT_DIR.mkdir(exist_ok=True)

# --------------------------------------------------------------------
# Никаких жёстких списков стран/категорий — всё определяется по
# структуре документа динамически (двумя проходами), чтобы ничего
# не терялось (например "Bed&Breakfast", которого не было в старом
# списке категорий).
# --------------------------------------------------------------------

OBJECT_PATTERN = re.compile(r"^\d+\)\s+\S")
# Заголовок раздела вида "Accommodation (жилье)" — отличительный признак:
# перевод в скобках на кириллице.
SECTION_PATTERN = re.compile(r"^[A-Za-z\s/]+\s*\([^)]*[\u0400-\u04FF][^)]*\)$")
# "1) NORTH AMERICA" или "7) THE UNITED ARAB EMIRATES (UAE)"
CONTINENT_PATTERN = re.compile(r"^\d+\)\s+[A-Z\s]+(\([A-Z]+\))?$")
CONTINENT_NAMES = {
    "NORTH AMERICA", "SOUTH AMERICA", "EUROPE", "ASIA", "AUSTRALIA", "AFRICA",
}

# Раздел считаем "не местами" (типа Transport — справка о тарифах без
# ссылок), а не реальными объектами, если доля пунктов со ссылкой
# в нём ниже этого порога. Подобрано так, чтобы отсечь только разделы
# вида Transport (0% ссылок), но не задеть разделы вида Extreme sport,
# где почти всегда есть ссылка (~90-99%).
URL_RATE_THRESHOLD = 0.5


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    return f"{parts.scheme}://{parts.netloc}{parts.path}"


def is_url(text: str) -> bool:
    try:
        result = urlparse(text.strip())
        return bool(result.scheme and result.netloc)
    except Exception:
        return False


def clean_name(text: str) -> str:
    return re.sub(r"^\d+\)\s+", "", text).strip()


def is_city_line(text: str) -> bool:
    """
    '- New York', '- Las Vegas, Nevada' -> True
    '- Rooftop pool with a large bar...' / '- Private bathrooms and
    free WiFi' (буллеты в описании) -> False
    Названия городов — это Title Case (каждое слово с большой буквы),
    в отличие от обычных предложений-буллетов, где есть служебные
    слова со строчной буквы (and, with, free...).
    """
    if not text.startswith("- "):
        return False
    body = text[2:].strip()
    if not body or len(body) > 40:
        return False
    if any(ch.isdigit() for ch in body):
        return False
    if any(s in body for s in ("$", "€", "£", "(", ")", ":")):
        return False
    words = re.split(r"[\s,]+", body)
    words = [w for w in words if w]
    if not words:
        return False
    connectors = {"de", "da", "do", "di", "la", "le", "van", "von", "der", "den", "of"}
    return all(
        w[:1].isupper() or w.lower() in connectors
        for w in words if w[:1].isalpha()
    )


def is_plain_label(text) -> bool:
    """
    Короткая "голая" строка без разметки — это либо название страны
    (если дальше идёт город), либо название категории (если дальше
    идёт нумерованный объект): 'United States', 'Hotels',
    'Bed&Breakfast', 'Mexico'. Запятые/точки отсекаем, чтобы не
    путать с обрывками описаний вроде 'Asian, Burmese.'.
    """
    if not text or len(text) > 40:
        return False
    if is_url(text):
        return False
    if any(ch.isdigit() for ch in text):
        return False
    if any(s in text for s in ("(", ")", "$", "€", "£", ":", "/", ",", ".")):
        return False
    if text.startswith("- "):
        return False
    if not text[:1].isupper():
        return False
    return True


def find_first_address(texts, start_idx):
    """
    Адрес первого объекта внутри блока города — нужен, чтобы
    ПРОВЕРИТЬ кандидата в страны (страна должна встречаться в адресе
    первого же отеля/места), а не просто поверить случайной короткой
    строке вроде 'Free'.
    """
    seen_object = False
    for j in range(start_idx, min(start_idx + 80, len(texts))):
        t = texts[j]
        if not t:
            continue
        if is_city_line(t) or CONTINENT_PATTERN.match(t):
            return None
        if not seen_object and OBJECT_PATTERN.match(t):
            seen_object = True
            continue
        if seen_object:
            return t
    return None


def country_matches_address(candidate: str, address: str) -> bool:
    c = candidate.lower()
    a = address.lower()
    if c in a:
        return True
    # на случай локализованного названия страны (Italia / Italy,
    # Polska / Poland и т.п.) — сверяем по началу слова
    prefix = c[:4]
    return len(prefix) >= 4 and prefix in a


def compute_section_url_rates(texts):
    """Первый проход: для каждого раздела считаем долю пунктов со
    ссылкой, чтобы потом отсеять разделы-справочники без мест
    (Transport и подобные), не перечисляя их по именам."""
    stats = {}
    current_section = None
    in_obj = False
    obj_has_url = False

    def flush():
        nonlocal in_obj, obj_has_url
        if in_obj and current_section is not None:
            total, with_url = stats.setdefault(current_section, [0, 0])
            stats[current_section][0] = total + 1
            stats[current_section][1] = with_url + (1 if obj_has_url else 0)
        in_obj = False
        obj_has_url = False

    for t in texts:
        if not t:
            continue
        if SECTION_PATTERN.match(t):
            flush()
            current_section = t.split("(", 1)[0].strip()
            continue
        if is_city_line(t):
            flush()
            continue
        if OBJECT_PATTERN.match(t):
            flush()
            in_obj = True
            continue
        if is_url(t) and in_obj:
            obj_has_url = True
            continue
    flush()

    return {
        name: (counts[1] / counts[0]) if counts[0] else 0
        for name, counts in stats.items()
    }


def merge():

    with open(INPUT_FILE, encoding="utf-8") as f:
        rows = json.load(f)

    texts = [r["text"].strip() for r in rows]

    section_url_rate = compute_section_url_rates(texts)
    skip_sections = {
        name for name, rate in section_url_rate.items() if rate < URL_RATE_THRESHOLD
    }

    records = []

    context = {
        "continent": None,
        "country": None,
        "city": None,
        "section": None,
        "category": None,
    }

    current = None
    skip_current_section = False
    prev_text = None  # предыдущая непустая строка

    def save_current():
        nonlocal current
        if not current:
            return
        current["description"] = "\n".join(current["description"]).strip()
        records.append(current)
        current = None

    for idx, row in enumerate(rows):

        text = texts[idx]

        if not text:
            continue

        previous_text = prev_text
        prev_text = text

        # -------------------------
        # URL -> закрывает объект (если объект открыт)
        # -------------------------
        if is_url(text):

            if current:
                current["url"] = normalize_url(text)

            continue

        # -------------------------
        # CONTINENT / страна-в-формате-материка
        # -------------------------
        if CONTINENT_PATTERN.match(text):

            save_current()

            name = text.split(")", 1)[1].strip()
            name_no_parens = re.sub(r"\s*\([A-Z]+\)$", "", name).strip()

            if name in CONTINENT_NAMES:
                context["continent"] = name.title()
                context["country"] = None
                context["city"] = None
            else:
                context["country"] = re.sub(r"^The\s+", "", name_no_parens.title())
                context["city"] = None

            context["section"] = None
            context["category"] = None

            continue

        # -------------------------
        # CITY
        # -------------------------
        if is_city_line(text):

            save_current()

            if is_plain_label(previous_text):
                addr = find_first_address(texts, idx + 1)
                if addr and country_matches_address(previous_text, addr):
                    context["country"] = previous_text

            if context["country"] is None:
                # страна нигде не указана отдельной строкой
                # (например "5) AUSTRALIA" -> сразу "- Sydney")
                context["country"] = context["continent"]

            context["city"] = text[2:].strip()
            context["section"] = None
            context["category"] = None

            continue

        # -------------------------
        # SECTION
        # -------------------------
        if SECTION_PATTERN.match(text):

            save_current()

            section_name = text.split("(", 1)[0].strip()
            context["section"] = section_name
            skip_current_section = section_name in skip_sections

            # по умолчанию категория = сама секция (Attractions, Excursions...),
            # если дальше будет отдельная строка-подкатегория (Hotels,
            # Bed&Breakfast...) — она её переопределит
            context["category"] = None if skip_current_section else section_name

            continue

        # -------------------------
        # OBJECT
        # 1) Night Hotel Broadway
        # -------------------------
        if OBJECT_PATTERN.match(text):

            save_current()

            if skip_current_section:
                # раздел вроде Transport — это справочные тарифы,
                # а не места (ни у одного пункта нет ссылки)
                continue

            if is_plain_label(previous_text):
                context["category"] = previous_text

            current = {
                **context,
                "source_id": row["id"],
                "name": clean_name(text),
                "address": "",
                "description": [],
                "url": "",
            }

            continue

        # -------------------------
        # CONTENT INSIDE OBJECT
        # -------------------------
        if current:
            if not current["address"]:
                current["address"] = text
            else:
                current["description"].append(text)

    save_current()

    csv_file = OUTPUT_DIR / "places.csv"

    with open(csv_file, "w", newline="", encoding="utf-8") as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "source_id", "continent", "country", "city", "section",
                "category", "name", "address", "description", "url",
            ]
        )

        writer.writeheader()
        writer.writerows(records)

    print(f"Saved {len(records)} records")
    print(f"Skipped sections (no real places, e.g. fare info): {sorted(skip_sections)}")
    print(csv_file)


if __name__ == "__main__":
    merge()