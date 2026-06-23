from urllib.parse import urlparse, urlsplit
import re

OBJECT_PATTERN = re.compile(r"^\d+\)\s+\S")
SECTION_PATTERN = re.compile(r"^[A-Za-z\s/]+\s*\([^)]*[\u0400-\u04FF][^)]*\)$")
CONTINENT_PATTERN = re.compile(r"^\d+\)\s+[A-Z\s]+(\([A-Z]+\))?$")


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