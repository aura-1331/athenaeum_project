"""Book metadata and explicit title-reference lookup for Athenaeum.

ISBN provider order: Open Library direct ISBN endpoint, Open Library Search,
then Google Books as the only external fallback. Title candidates use Open
Library Search first and Google Books only when Open Library returns no usable
candidates. DDC is deliberately not looked up or inferred here.

Configure GOOGLE_BOOKS_API_KEY in the backend process environment. Never put
that key in the Vue frontend or source control.
"""
from __future__ import annotations

import difflib
import logging
import os
import re
import unicodedata
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import get_current_user

logger = logging.getLogger(__name__)
# Do not let httpx log query URLs that may contain the Google Books API key.
logging.getLogger("httpx").setLevel(logging.WARNING)

GOOGLE_BOOKS_API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY", "").strip()
router = APIRouter(prefix="/metadata", tags=["metadata"])
legacy_router = APIRouter(prefix="/catalogue", tags=["catalogue"])


def metadata_result(
    *,
    title: str = "",
    author: str = "",
    publisher: str = "",
    year: str | None = None,
    genre: str | None = None,
    found: bool = False,
    source: str | None = None,
) -> dict[str, Any]:
    """Keep the existing frontend response shape; DDC is not externally filled."""
    return {
        "found": found,
        "title": title,
        "author": author,
        "publisher": publisher,
        "year": year,
        "genre": genre,
        "ddc": None,
        "source": source,
    }


def _year_from(value: object) -> str | None:
    match = re.search(r"\b\d{4}\b", str(value or ""))
    return match.group(0) if match else None


def _first_text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item.strip():
                return item.strip()
    return ""


def _join_texts(value: object, limit: int = 3) -> str:
    if isinstance(value, list):
        return "; ".join(str(item).strip() for item in value[:limit] if str(item).strip())
    return _first_text(value)


def _result_from_fields(
    *,
    title: object,
    author: object = "",
    publisher: object = "",
    date: object = None,
    genre: object = None,
    source: str,
) -> dict[str, Any] | None:
    title_text = _first_text(title)
    if not title_text:
        return None
    return metadata_result(
        found=True,
        title=title_text,
        author=_join_texts(author),
        publisher=_join_texts(publisher, limit=1),
        year=_year_from(date),
        genre=_join_texts(genre, limit=3) or None,
        source=source,
    )


def _redact_secret(message: str) -> str:
    return message.replace(GOOGLE_BOOKS_API_KEY, "[REDACTED]") if GOOGLE_BOOKS_API_KEY else message


async def _open_library_isbn(client: httpx.AsyncClient, isbn: str) -> dict[str, Any] | None:
    """Resolve the specific edition by ISBN before searching the broader index."""
    try:
        response = await client.get(f"https://openlibrary.org/isbn/{isbn}.json")
        logger.info("Open Library ISBN endpoint: HTTP %s", response.status_code)
        if response.status_code != 200:
            return None
        edition = response.json()
        authors: list[str] = []
        for author_ref in (edition.get("authors") or [])[:3]:
            key = (author_ref.get("key") or "").strip() if isinstance(author_ref, dict) else ""
            if not key.startswith("/authors/"):
                continue
            try:
                author_response = await client.get(f"https://openlibrary.org{key}.json")
                if author_response.status_code == 200:
                    name = (author_response.json().get("name") or "").strip()
                    if name:
                        authors.append(name)
            except (httpx.HTTPError, ValueError):
                # Author enrichment is optional; keep the edition result.
                continue
        return _result_from_fields(
            title=edition.get("title"),
            author=authors,
            publisher=edition.get("publishers"),
            date=edition.get("publish_date"),
            genre=edition.get("subjects"),
            source="Open Library ISBN",
        )
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Open Library ISBN lookup failed (%s)", type(exc).__name__)
        return None


async def _open_library_isbn_search(client: httpx.AsyncClient, isbn: str) -> dict[str, Any] | None:
    """Search Open Library's ISBN index if the direct edition endpoint misses."""
    try:
        response = await client.get(
            "https://openlibrary.org/search.json",
            params={
                "isbn": isbn,
                "limit": 5,
                "fields": "title,author_name,publisher,first_publish_year,publish_date,subject",
            },
        )
        logger.info("Open Library ISBN search: HTTP %s", response.status_code)
        if response.status_code != 200:
            logger.warning("Open Library ISBN search returned HTTP %s", response.status_code)
            return None
        for book in (response.json().get("docs") or []):
            result = _result_from_fields(
                title=book.get("title"),
                author=book.get("author_name"),
                publisher=book.get("publisher"),
                date=book.get("first_publish_year") or book.get("publish_date"),
                genre=book.get("subject"),
                source="Open Library Search",
            )
            if result:
                return result
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Open Library ISBN search failed (%s)", type(exc).__name__)
    return None


async def _google_books_isbn(client: httpx.AsyncClient, isbn: str) -> dict[str, Any] | None:
    """Last-resort ISBN provider. Google Books is never called after OL succeeds."""
    params: dict[str, str | int] = {"q": f"isbn:{isbn}", "maxResults": 5, "printType": "books"}
    if GOOGLE_BOOKS_API_KEY:
        params["key"] = GOOGLE_BOOKS_API_KEY
    else:
        logger.warning("GOOGLE_BOOKS_API_KEY is not configured; Google Books uses unauthenticated quota")
    try:
        response = await client.get("https://www.googleapis.com/books/v1/volumes", params=params)
        logger.info("Google Books ISBN fallback: HTTP %s", response.status_code)
        if response.status_code != 200:
            logger.warning("Google Books returned HTTP %s", response.status_code)
            return None
        for item in (response.json().get("items") or []):
            info = item.get("volumeInfo") or {}
            result = _result_from_fields(
                title=info.get("title"),
                author=info.get("authors"),
                publisher=info.get("publisher"),
                date=info.get("publishedDate"),
                genre=info.get("categories"),
                source="Google Books",
            )
            if result:
                return result
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Google Books ISBN lookup failed (%s): %s", type(exc).__name__, _redact_secret(str(exc)))
    return None


def _title_key(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return " ".join(text.split())


def _title_tokens(value: object) -> list[str]:
    return _title_key(value).split()


def _token_similarity(left: str, right: str) -> float:
    if left == right:
        return 1.0
    return difflib.SequenceMatcher(None, left, right).ratio()


def _title_match_score(query: str, title: str) -> float:
    """Typo-tolerant title similarity; this ranks candidates, never edits titles."""
    query_key = _title_key(query)
    title_key = _title_key(title)
    if not query_key or not title_key:
        return 0.0
    if query_key == title_key:
        return 1.0
    query_tokens = _title_tokens(query_key)
    title_tokens = _title_tokens(title_key)
    if not query_tokens or not title_tokens:
        return difflib.SequenceMatcher(None, query_key, title_key).ratio()

    query_coverage = sum(
        max(_token_similarity(token, candidate) for candidate in title_tokens)
        for token in query_tokens
    ) / len(query_tokens)
    title_precision = sum(
        max(_token_similarity(token, query_token) for query_token in query_tokens)
        for token in title_tokens
    ) / len(title_tokens)
    token_score = (
        2 * query_coverage * title_precision / (query_coverage + title_precision)
        if query_coverage + title_precision else 0.0
    )
    whole_text_score = difflib.SequenceMatcher(None, query_key, title_key).ratio()
    return max(token_score, whole_text_score)


def _title_anchor_queries(query: str, maximum: int = 2) -> list[str]:
    """Pick meaningful query tokens to recover from a misspelled word in a title."""
    stop_words = {"a", "an", "and", "of", "the", "to", "in", "on", "for", "with"}
    tokens = _title_tokens(query)
    anchors: list[str] = []
    # Prefer longer words, while retaining the original token order for ties.
    indexed = sorted(enumerate(tokens), key=lambda pair: (-len(pair[1]), pair[0]))
    for _, token in indexed:
        if len(token) < 4 or token in stop_words or token in anchors:
            continue
        anchors.append(token)
        if len(anchors) >= maximum:
            break
    return anchors


def _ordered_candidates(
    candidates: list[dict[str, Any]],
    query: str,
    *,
    minimum_score: float = 0.52,
) -> list[dict[str, Any]]:
    """Score and rank external candidates against the entered title, keeping source data intact."""
    scored: list[dict[str, Any]] = []
    for candidate in candidates:
        title = _first_text(candidate.get("title"))
        if not title:
            continue
        score = _title_match_score(query, title)
        if score < minimum_score:
            continue
        item = dict(candidate)
        item["match_score"] = round(score * 100)
        scored.append(item)

    scored.sort(key=lambda item: (-int(item.get("match_score") or 0), _title_key(item.get("title"))))
    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, Any]] = []
    for item in scored:
        key = (_title_key(item.get("title")), _title_key(item.get("author")))
        if not key[0] or key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique[:10]


async def _open_library_title_fetch(
    client: httpx.AsyncClient,
    search_query: str,
    *,
    broad: bool = False,
) -> list[dict[str, Any]]:
    """Fetch title candidates. Broad token searches are used only for typo recovery."""
    try:
        params = {
            "limit": 20,
            "fields": "key,title,author_name,first_publish_year,isbn,publisher",
        }
        params["q" if broad else "title"] = search_query
        response = await client.get(
            "https://openlibrary.org/search.json",
            params=params,
        )
        logger.info("Open Library title standardization search (broad=%s): HTTP %s", broad, response.status_code)
        if response.status_code != 200:
            logger.warning("Open Library title search returned HTTP %s", response.status_code)
            return []
        candidates: list[dict[str, Any]] = []
        for doc in (response.json().get("docs") or []):
            title = _first_text(doc.get("title"))
            if not title:
                continue
            candidates.append({
                "title": title,
                "author": _join_texts(doc.get("author_name")),
                "publisher": _join_texts(doc.get("publisher"), limit=1),
                "year": str(doc.get("first_publish_year") or "") or None,
                "isbn": _first_text(doc.get("isbn")),
                "source": "Open Library",
                "external_id": _first_text(doc.get("key")) or None,
            })
        return candidates
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Open Library title search failed (%s)", type(exc).__name__)
        return []


async def _open_library_title_candidates(client: httpx.AsyncClient, query: str) -> list[dict[str, Any]]:
    candidates = await _open_library_title_fetch(client, query)
    ranked = _ordered_candidates(candidates, query)
    # Only stop if the top result is a strong match. Merely similar results such as
    # a workbook or journal should not prevent the anchor-token retry.
    if ranked and int(ranked[0].get("match_score") or 0) >= 82:
        return ranked

    gathered = list(candidates)
    for anchor in _title_anchor_queries(query, maximum=2):
        gathered.extend(await _open_library_title_fetch(client, anchor, broad=True))
    return _ordered_candidates(gathered, query)


async def _google_books_title_fetch(client: httpx.AsyncClient, search_query: str) -> list[dict[str, Any]]:
    params: dict[str, str | int] = {"q": search_query, "maxResults": 20, "printType": "books"}
    if GOOGLE_BOOKS_API_KEY:
        params["key"] = GOOGLE_BOOKS_API_KEY
    else:
        logger.warning("GOOGLE_BOOKS_API_KEY is not configured; Google Books title search uses unauthenticated quota")
    try:
        response = await client.get("https://www.googleapis.com/books/v1/volumes", params=params)
        logger.info("Google Books title fallback: HTTP %s", response.status_code)
        if response.status_code != 200:
            logger.warning("Google Books title search returned HTTP %s", response.status_code)
            return []
        candidates: list[dict[str, Any]] = []
        for item in (response.json().get("items") or []):
            info = item.get("volumeInfo") or {}
            title = _first_text(info.get("title"))
            subtitle = _first_text(info.get("subtitle"))
            if subtitle and subtitle.casefold() not in title.casefold():
                title = f"{title}: {subtitle}"
            if not title:
                continue
            identifiers = info.get("industryIdentifiers") or []
            isbn = next((x.get("identifier", "") for x in identifiers if isinstance(x, dict) and x.get("type") == "ISBN_13"), "")
            if not isbn:
                isbn = next((x.get("identifier", "") for x in identifiers if isinstance(x, dict) and x.get("type") == "ISBN_10"), "")
            candidates.append({
                "title": title,
                "author": _join_texts(info.get("authors")),
                "publisher": _first_text(info.get("publisher")),
                "year": _year_from(info.get("publishedDate")),
                "isbn": isbn or None,
                "source": "Google Books",
                "external_id": _first_text(item.get("id")) or None,
            })
        return candidates
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Google Books title search failed (%s): %s", type(exc).__name__, _redact_secret(str(exc)))
        return []


async def _google_books_title_candidates(client: httpx.AsyncClient, query: str) -> list[dict[str, Any]]:
    # Try the complete text first; if typo-heavy text yields no credible candidate,
    # search using a strong token and rank the returned titles against the full input.
    candidates = await _google_books_title_fetch(client, query)
    ranked = _ordered_candidates(candidates, query)
    if ranked and int(ranked[0].get("match_score") or 0) >= 82:
        return ranked

    gathered = list(candidates)
    for anchor in _title_anchor_queries(query, maximum=2):
        gathered.extend(await _google_books_title_fetch(client, anchor))
        ranked = _ordered_candidates(gathered, query)
        if ranked and int(ranked[0].get("match_score") or 0) >= 82:
            return ranked
    return _ordered_candidates(gathered, query)


@router.get("/isbn-lookup", response_model=dict)
async def lookup_isbn(isbn: str, current_user: dict = Depends(get_current_user)):
    clean_isbn = re.sub(r"[^0-9X]", "", str(isbn or "").upper())
    if len(clean_isbn) not in (10, 13):
        raise HTTPException(status_code=400, detail="Enter a valid 10- or 13-character ISBN.")
    headers = {
        "User-Agent": "AthenaeumCatalogue/1.0 (bibliographic metadata lookup)",
        "Accept": "application/json",
    }
    timeout = httpx.Timeout(8.0, connect=4.0)
    async with httpx.AsyncClient(headers=headers, timeout=timeout, follow_redirects=True) as client:
        providers = (
            ("Open Library ISBN", _open_library_isbn),
            ("Open Library Search", _open_library_isbn_search),
            ("Google Books", _google_books_isbn),
        )
        for name, provider in providers:
            result = await provider(client, clean_isbn)
            if result and result.get("title"):
                logger.info("ISBN metadata found through %s", name)
                return result
    logger.warning("No usable ISBN metadata found; ISBN ends in %s", clean_isbn[-4:])
    return metadata_result()


@router.get("/title-lookup", response_model=dict)
async def lookup_title_candidates(
    q: str = Query(..., min_length=2, max_length=255),
    current_user: dict = Depends(get_current_user),
):
    """Explicit, read-only title candidate search; never rewrites a Work automatically."""
    query = " ".join(q.strip().split())
    if len(query) < 2:
        raise HTTPException(status_code=400, detail="Enter at least two characters of a title.")
    headers = {
        "User-Agent": "AthenaeumCatalogue/1.0 (explicit title reference lookup)",
        "Accept": "application/json",
    }
    timeout = httpx.Timeout(8.0, connect=4.0)
    async with httpx.AsyncClient(headers=headers, timeout=timeout, follow_redirects=True) as client:
        candidates = await _open_library_title_candidates(client, query)
        open_library_candidates = candidates
        open_library_is_credible = bool(
            candidates and int(candidates[0].get("match_score") or 0) >= 72
        )
        source = "Open Library" if open_library_is_credible else ""
        if not open_library_is_credible:
            google_candidates = await _google_books_title_candidates(client, query)
            if google_candidates:
                candidates = google_candidates
                source = "Google Books"
            else:
                # Keep weaker Open Library suggestions available if neither source
                # yields a stronger candidate; the operator still has to select one.
                candidates = open_library_candidates
                source = "Open Library" if candidates else ""
    return {
        "found": bool(candidates),
        "query": query,
        "source": source or None,
        "results": candidates,
        "message": "" if candidates else "No title candidates were found in Open Library or Google Books.",
    }


# The application currently mounts the legacy /catalogue router; keep both legacy
# URLs available so the existing frontend and any newer frontend clients work.
legacy_router.add_api_route("/isbn-lookup", lookup_isbn, methods=["GET"], response_model=dict)
legacy_router.add_api_route("/title-lookup", lookup_title_candidates, methods=["GET"], response_model=dict)
