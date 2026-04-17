# Development Log

This file records development progress of the library catalogue system.

---

## 2026-03-14

### Work Completed

Implemented multilingual search key generation.

Added database fields:

title_search_key  
author_search_key

Created rebuild script:

app/rebuild_search_keys.py

Script converts Malayalam text to Manglish search keys.

Example:

ഹക്കിൾബെറി ഫിന്നിന്റെ വിക്രമങ്ങൾ
→ hakkibrifinninrvikramanna

മാർക്ക് ട്വൈൻ
→ makktvai

---

### Observations

Python transliteration produces correct results.

However corruption appears in the database when writing
`author_search_key`.

Example:

Expected:
makktvai

Stored:
makktvai퉐ࡅ翾쪀卸Ț

---

### Decision

Issue temporarily deferred.

Development continues with other catalogue features.

---

### Next Focus

Continue implementing catalogue filtering and search system.