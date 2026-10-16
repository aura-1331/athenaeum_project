"""Shared accession-number and catalogue-code helpers.

These functions are pure formatting helpers used by Work, Item, and the
catalogue preview endpoint. They contain no database or request logic.
"""


def get_language_prefix(language: str) -> str:
    lang = (language or "").strip().lower()
    if lang == "malayalam":
        return "ML"
    if lang == "english":
        return "EN"
    if "multi" in lang:
        return "MU"
    if lang == "tamil":
        return "TA"
    if lang == "telugu":
        return "TE"
    if lang == "marathi":
        return "MR"
    if lang == "malay":
        return "MA"
    return lang[:2].upper() if lang else "UN"


def get_category_code(category: str) -> str:
    cat = (category or "").strip()
    if cat == "Fiction":
        return "FIC"
    if cat == "Non-Fiction":
        return "NF"
    if cat == "Reference":
        return "REF"
    if cat == "Religious":
        return "REL"
    if cat == "Poetry":
        return "POE"
    return "GEN"
