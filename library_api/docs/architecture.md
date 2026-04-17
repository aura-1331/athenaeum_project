# Library Catalogue System Architecture

## System Overview

This project implements a multilingual library catalogue system.

The system stores and manages catalogue records and supports
searching Malayalam titles using Manglish transliteration.

---

## Technology Stack

Backend:
FastAPI (Python)

Database:
PostgreSQL

Frontend:
Vue

Environment:
Windows + Python virtual environment

Database Driver:
psycopg2

---

## Project Components

Backend API:
library_api/app

Database:
PostgreSQL database named `library_catalogue`

Frontend:
Vue interface for catalogue browsing and editing.

---

## Core Database Table

works

Important columns:

id  
serial_no  
title  
author  
language  
category  
genre  
publisher  
title_search_key  
author_search_key  
notes  

---

## Search Architecture

Malayalam catalogue records are searchable using Manglish keys.

Example:

Title:
ഹക്കിൾബെറി ഫിന്നിന്റെ വിക്രമങ്ങൾ

Generated search key:
hakkibrifinninrvikramanna

Author:
മാർക്ക് ട്വൈൻ

Generated search key:
makktvai

These keys allow users to search Malayalam records using
Latin keyboard input.

---

## Search Key Pipeline

Script:
app/rebuild_search_keys.py

Pipeline:

1. Read title and author fields
2. Convert Malayalam → Manglish
3. Clean text to ASCII search key
4. Store result in database

Columns used:

title_search_key  
author_search_key

---

## API Layer

FastAPI handles:

Catalogue listing  
Pagination  
Filtering  
Sorting  
Metadata retrieval  
Record editing

---

## Frontend Layer

Vue interface provides:

Catalogue table view  
Pagination controls  
Inspector panel  
Edit mode  
Search filtering