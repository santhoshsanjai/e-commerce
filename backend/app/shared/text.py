import re
import unicodedata


def slugify(value: str, max_length: int = 120) -> str:
    """ASCII, lower-case, hyphen-separated slug. Falls back to 'item' when nothing is left."""
    normalised = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", normalised.lower()).strip("-")
    return slug[:max_length].strip("-") or "item"
