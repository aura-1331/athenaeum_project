# Known Issues

This document records unresolved technical issues discovered
during development.

Keeping these records prevents future debugging from starting
from zero.

---

## 2026-03-14 — Manglish Search Key Corruption

Component:
Search key rebuild pipeline

Script:
app/rebuild_search_keys.py

Database:
works table

---

### Problem

When rebuilding search keys, corrupted characters appear
in the `author_search_key` field.

Example record:

author:
മാർക്ക് ട്വൈൻ

Expected search key:
makktvai

Stored value:
makktvai퉐ࡅ翾쪀卸Ț

---

### Observations

Python transliteration output is correct.

Corruption appears only after writing data to PostgreSQL.

Columns are defined as:

title_search_key text  
author_search_key text

Queries use parameterized SQL.

Cleaning the text with regex did not remove the corruption.

---

### Suspected Cause

Possible encoding mismatch between psycopg2 client and
PostgreSQL server.

Potential areas for investigation:

client_encoding  
server_encoding  
psycopg2 connection configuration

---

### Status

Deferred for later investigation.