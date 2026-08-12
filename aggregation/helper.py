from urllib.parse import urlparse
import re

OBJECT_PATTERN = re.compile(r"^\d+\)\s*\S")
SECTION_PATTERN = re.compile(r"^[A-Za-z\s/]+\s*\([^)]*[\u0400-\u04FF][^)]*\)$")
CONTINENT_PATTERN = re.compile(r"^\d+\)\s+[A-Z\s]+(\([A-Z]+\))?$")

URL_CORRECTIONS = {
    "https://en.wikipedia.org/wiki/File:Ferry_Building_Marketplace,_San_Francisco.jpg":
        "https://en.wikipedia.org/wiki/San_Francisco_Ferry_Building",
    "https://en.wikipedia.org/wiki/Tower_Bridge#/media/File:Tower_Bridge_at_Dawn.jpg":
        "https://en.wikipedia.org/wiki/Tower_Bridge",
    "https://en.wikipedia.org/wiki/File:Kraljičina_plaža.jpg":
        "https://bar.travel/listing/kraljicina-plaza/",
    "https://mos-holidays.ru/spb/interesnoe/krytyj-verevochny...ce-c-tabs-1":
        "https://mos-holidays.ru/spb/interesnoe/krytyj-verevochnyj-park-vysotnyj-gorod/",
}


def normalize_url(url: str) -> str:
    value = url.strip()
    return URL_CORRECTIONS.get(value, value)


def is_url(text: str) -> bool:
    try:
        result = urlparse(text.strip())
        return bool(result.scheme and result.netloc)
    except Exception:
        return False


def clean_name(text: str) -> str:
    return re.sub(r"^(?:\d+[.)]+\s*)+", "", text).strip()


def split_object_text(text: str) -> tuple[str, str]:
    body = clean_name(text)
    match = re.search(r"\)(?=[A-Z][a-z])", body)
    if not match:
        return body, ""
    name = body[: match.end()].strip()
    inline_description = body[match.end() :].strip()
    return name, inline_description


def split_inline_uk_address(name: str) -> tuple[str, str]:
    """Move an inline UK address out of a place name while retaining price notes."""
    opening = name.find("(")
    if opening < 0:
        return name, ""

    tail = name[opening:]
    postcode = re.search(r"\b[A-Z]{1,2}\d[A-Z\d]?(?:\s*\d[A-Z]{2})?\b", tail)
    if not postcode or "," not in tail[: postcode.end()]:
        return name, ""

    clean_place_name = name[:opening].rstrip(" .\u00a0")
    remainder = tail[postcode.end() :]
    note_match = re.search(
        r"(?i)(?:exit\s+is\s+free|\d+(?:[.,]\d+)?\s*\$.*)[\s.)]*$",
        remainder,
    )
    if note_match:
        address_part = tail[: postcode.end() + note_match.start()]
        suffix = note_match.group(0).strip(" (),.\u00a0")
    else:
        address_part = tail
        suffix = ""

    address = address_part.strip(" (),.\u00a0")
    address = re.sub(r"\)\s*,", ",", address)
    corrections = {"Tover of London": "Tower of London"}
    clean_place_name = corrections.get(clean_place_name, clean_place_name)
    if suffix:
        clean_place_name = f"{clean_place_name} ({suffix})"
    return clean_place_name, address


def is_city_line(text: str) -> bool:
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


def is_numbered_geo_heading(rows: list[dict], row_index: int, continent_names: set[str]) -> bool:
    """Distinguish numbered geography headings from all-caps place names."""
    row = rows[row_index]
    if row.get("type") != "text":
        return False

    text = row.get("text", "").strip()
    if not CONTINENT_PATTERN.match(text):
        return False

    name = text.split(")", 1)[1].strip()
    if name in continent_names:
        return True

    for next_row in rows[row_index + 1 :]:
        if next_row.get("type") != "text":
            continue
        next_text = next_row.get("text", "").strip()
        if next_text:
            return is_city_line(next_text)

    return False


def is_implicit_city_heading(rows: list[dict], row_index: int, current_section: str | None) -> bool:
    """Detect a city/country label written without the usual ``- `` prefix."""
    if current_section != "Transport":
        return False

    row = rows[row_index]
    text = row.get("text", "").strip()
    if row.get("type") != "text" or not is_plain_label(text):
        return False

    for next_row in rows[row_index + 1 :]:
        if next_row.get("type") != "text":
            continue
        next_text = next_row.get("text", "").strip()
        if not next_text:
            continue
        if not SECTION_PATTERN.match(next_text):
            return False
        return next_text.split("(", 1)[0].strip() == "Accommodation"

    return False


def is_implicit_object_start(rows: list[dict], row_index: int) -> bool:
    """Recognize an unnumbered place when its block reaches a URL first."""
    row = rows[row_index]
    if row.get("type") != "text":
        return False

    text = row.get("text", "").strip()
    if (
        not text
        or OBJECT_PATTERN.match(text)
        or SECTION_PATTERN.match(text)
        or is_city_line(text)
        or is_url(text)
    ):
        return False

    for next_row in rows[row_index + 1 :]:
        if next_row.get("type") != "text":
            continue
        next_text = next_row.get("text", "").strip()
        if not next_text:
            continue
        if is_url(next_text):
            return True
        if (
            OBJECT_PATTERN.match(next_text)
            or SECTION_PATTERN.match(next_text)
            or is_city_line(next_text)
        ):
            return False

    return False


def is_plain_label(text) -> bool:
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


def is_probable_address(text: str, allow_terminal_punctuation: bool = False) -> bool:
    value = text.strip()
    if not value or is_url(value):
        return False
    if re.match(
        r"(?i)^(?:located\b|comfortable accommodations\b|beachfront\b|"
        r"prime location\b|elegant accommodations\b|only\b|set over\b|"
        r"welcome to\b|guests\b|the official\b|"
        r"the\s+.{1,80}\s+(?:is|offers|features)\b)",
        value,
    ):
        return False
    if len(value) > 220:
        return False

    lower = value.lower()
    address_words = {
        "avenue", "ave", "street", "st", "road", "rd", "boulevard", "blvd",
        "lane", "ln", "drive", "dr", "square", "sq", "place", "plaza",
        "calle", "rue", "ulica", "strada", "prospekt", "ulitsa",
    }
    if (
        any(re.search(rf"\b{re.escape(word)}\b", lower) for word in address_words)
        and "," in value
        and len(value) < 180
        and (allow_terminal_punctuation or not re.search(r"[.!?]$", value))
    ):
        return True
    if (
        re.search(r"\b\d{2,6}\b", value)
        and "," in value
        and len(value) < 180
        and not any(symbol in value for symbol in ("$", "€", "£", "¥", "₩"))
        and (allow_terminal_punctuation or not any(symbol in value for symbol in (":", ";")))
        and (allow_terminal_punctuation or not re.search(r"[.!?]$", value))
    ):
        return True
    if (
        value.count(",") >= 2
        and (allow_terminal_punctuation or ":" not in value)
        and (allow_terminal_punctuation or ";" not in value)
        and len(value) < 180
        and (allow_terminal_punctuation or not re.search(r"[.!?]$", value))
    ):
        return True
    if (
        re.search(r"^[A-Z0-9][A-Za-z0-9 .'-]+,\s*[A-Z]", value)
        and len(value) < 180
        and (allow_terminal_punctuation or not re.search(r"[.!?]$", value))
    ):
        return True
    return False


def find_first_address(rows, start_idx):
    seen_object = False
    for j in range(start_idx, min(start_idx + 80, len(rows))):
        r = rows[j]
        if r["type"] != "text":
            continue
        t = r["text"]
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
    prefix = c[:4]
    return len(prefix) >= 4 and prefix in a
