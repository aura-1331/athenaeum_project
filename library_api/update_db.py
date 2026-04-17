import re
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate


def ml_to_manglish(text: str) -> str:
    """
    Convert Malayalam → stable manglish search key
    """

    if not text:
        return ""

    try:
        out = transliterate(text, sanscript.MALAYALAM, sanscript.IAST)

        out = out.lower()

        # remove vowel accents
        out = re.sub(r"[āàá]", "a", out)
        out = re.sub(r"[īìí]", "i", out)
        out = re.sub(r"[ūùú]", "u", out)
        out = re.sub(r"[ēèé]", "e", out)
        out = re.sub(r"[ōòó]", "o", out)

        # remove anything not a-z or number
        out = re.sub(r"[^a-z0-9]", "", out)

        return out

    except Exception:
        return ""