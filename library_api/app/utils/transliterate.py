import re
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

def ml_to_manglish(text: str) -> str:
    if not text:
        return ""

    try:
        # 1. The Academic translation
        manglish = transliterate(text, sanscript.MALAYALAM, sanscript.ITRANS)
        manglish = manglish.lower()

        # 2. THE "HUMAN" FIXES 
        # Fix the 'F' sound (ITRANS uses 'ph', humans use 'f')
        manglish = manglish.replace("ph", "f")
        
        # Fix the 'V'/'W' sound (Standardize to 'v')
        manglish = manglish.replace("w", "v")
        
        # Fix the 'Z'/'Zh' sound (For 'ഴ')
        manglish = manglish.replace("zh", "z")

        # 3. Simplify lazy vowels (Humans rarely type double vowels correctly)
        manglish = manglish.replace("aa", "a")
        manglish = manglish.replace("ee", "i")
        manglish = manglish.replace("oo", "u")

        # 4. Standard normalize
        manglish = manglish.replace("m$", "n")
        
        # Keep only latin + numbers
        manglish = re.sub(r"[^a-z0-9]", "", manglish)

        return manglish
    except Exception:
        return ""