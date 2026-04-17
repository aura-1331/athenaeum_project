import re
from app.utils.transliterate import ml_to_manglish


MALAYALAM_RANGE = re.compile(r'[\u0D00-\u0D7F]')


def contains_malayalam(text: str) -> bool:
    return bool(MALAYALAM_RANGE.search(text))


def collapse_duplicates(text: str) -> str:
    return re.sub(r'(.)\1+', r'\1', text)


def phonetic_normalize(text: str) -> str:
    # Lowercase
    text = text.lower()

    # Consonant simplifications
    replacements = {
        "sh": "s",
        "kh": "k",
        "ph": "f",
        "th": "t",
        "dh": "d",
        "gh": "g",
        "ch": "c",
    }

    for k, v in replacements.items():
        text = text.replace(k, v)
        # Harmonize single vowel differences
    text = text.replace("o", "a")

    # Vowel normalization
    vowel_replacements = {
        "aa": "a",
        "ee": "i",
        "ii": "i",
        "oo": "u",
        "uu": "u",
        "ai": "a",
        "au": "a",
    }

    for k, v in vowel_replacements.items():
        text = text.replace(k, v)

    # Remove non-alphanumeric
    text = re.sub(r'[^a-z0-9]', '', text)

    # Collapse repeated letters
    text = collapse_duplicates(text)

    return text


def build_search_key(text: str) -> str:
    if not text:
        return ""

    # If Malayalam, transliterate first
    if contains_malayalam(text):
        text = ml_to_manglish(text)

    return phonetic_normalize(text)