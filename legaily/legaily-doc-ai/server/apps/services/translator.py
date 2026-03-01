import os
import re
from typing import Optional

import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# Max chars per chunk to avoid 414 Request-URI Too Large (MyMemory uses GET)
# and to stay within typical API limits for LibreTranslate/gtx
_TRANSLATE_CHUNK_MAX = int(os.getenv("TRANSLATE_CHUNK_MAX", "800"))

# Larger chunks for Google API (supports up to 30k per text, 128 texts/request)
_GOOGLE_CHUNK_MAX = int(os.getenv("GOOGLE_TRANSLATE_CHUNK_MAX", "4500"))
_GOOGLE_BATCH_SIZE = int(os.getenv("GOOGLE_TRANSLATE_BATCH_SIZE", "20"))


def _chunk_text(text: str, max_chars: int = _TRANSLATE_CHUNK_MAX) -> list[str]:
    """Split text into chunks that fit within URL/API limits. Prefer paragraph boundaries."""
    if not text or len(text.strip()) <= max_chars:
        return [text.strip()] if text and text.strip() else []

    chunks = []
    remaining = text.strip()

    while remaining:
        if len(remaining) <= max_chars:
            chunks.append(remaining)
            break
        cut = remaining[:max_chars]
        # Prefer breaking at paragraph or sentence boundary
        last_para = max(cut.rfind("\n\n"), cut.rfind("\n"))
        ends = [m.end() for m in re.finditer(r"[.!?]\s+", cut) if m.end() <= max_chars]
        last_sent = max(ends) if ends else -1
        split_at = max(last_para, last_sent, max_chars // 2)
        if split_at <= 0:
            split_at = max_chars
        chunk = remaining[:split_at].strip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[split_at:].lstrip()

    return chunks


def _chunk_text_large(text: str, max_chars: int = _GOOGLE_CHUNK_MAX) -> list[str]:
    """Split text into larger chunks for Google API (fewer, bigger chunks = faster)."""
    return _chunk_text(text, max_chars)


def google_translate_text(text, target_language):
    if not text or not text.strip():
        return "No text content to translate."

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        # Free/no-key fallback: unofficial Google Translate endpoint (client=gtx).
        # Note: This is best-effort and may be rate-limited; for production, set GOOGLE_API_KEY.
        return gtx_translate_text(text, target_language)

    try:
        # Use large chunks and batch API (up to 128 texts per request) for much faster translation
        chunks = _chunk_text_large(text)
        if not chunks:
            return "No text content to translate."

        translated_parts = []
        # Process in batches of _GOOGLE_BATCH_SIZE
        for i in range(0, len(chunks), _GOOGLE_BATCH_SIZE):
            batch = chunks[i : i + _GOOGLE_BATCH_SIZE]
            params = {
                "q": batch,
                "target": target_language,
                "key": api_key,
            }
            response = requests.post(
                "https://translation.googleapis.com/language/translate/v2",
                data=params,  # form-encoded; q can be sent multiple times for array
            )
            response.raise_for_status()
            data = response.json()
            translations = data.get("data", {}).get("translations", [])
            for t in translations:
                translated_parts.append(t.get("translatedText", ""))

        return "\n".join(translated_parts) if translated_parts else ""

    except Exception as e:
        return f"Error during Google translation: {str(e)}"

def _gtx_translate_chunk(chunk: str, target_language: str) -> str:
    """Translate a single chunk via gtx. Used for parallel execution."""
    if not chunk.strip():
        return ""
    r = requests.get(
        "https://translate.googleapis.com/translate_a/single",
        params={"client": "gtx", "sl": "auto", "tl": target_language, "dt": "t", "q": chunk},
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    frags = (data[0] or []) if isinstance(data, list) and len(data) > 0 else []
    return "".join((c[0] or "") for c in frags if isinstance(c, list) and len(c) > 0)


def gtx_translate_text(text, target_language):
    """
    No-key translation via translate.googleapis.com (client=gtx).
    Uses parallel chunk translation for faster large-document processing.
    """
    if not text or not text.strip():
        return "No text content to translate."

    try:
        chunks = _chunk_text(text)
        chunks = [c for c in chunks if c.strip()]
        if not chunks:
            return "No text content to translate."

        max_workers = min(5, len(chunks))
        translated_parts = [""] * len(chunks)
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {ex.submit(_gtx_translate_chunk, c, target_language): i for i, c in enumerate(chunks)}
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    tr = future.result()
                    if tr:
                        translated_parts[idx] = tr
                except Exception:
                    translated_parts[idx] = ""
        parts = [p for p in translated_parts if p]
        return "\n".join(parts) if parts else "Translation returned empty result."
    except Exception as e:
        try:
            return libretranslate_text(text, target_language)
        except Exception:
            return mymemory_text(text, target_language, error=str(e))


def _libretranslate_chunk(chunk: str, target_language: str, url: str, api_key: Optional[str]) -> str:
    """Translate a single chunk via LibreTranslate."""
    if not chunk.strip():
        return ""
    payload = {"q": chunk, "source": "auto", "target": target_language, "format": "text"}
    if api_key:
        payload["api_key"] = api_key
    resp = requests.post(url, json=payload, timeout=60)
    resp.raise_for_status()
    return (resp.json().get("translatedText") or "").strip()


def libretranslate_text(text, target_language):
    """
    Free fallback translator using LibreTranslate.
    Uses parallel chunk translation for faster large-document processing.
    """
    if not text or not text.strip():
        return "No text content to translate."

    url = os.getenv("LIBRETRANSLATE_URL", "https://libretranslate.com/translate").strip()
    api_key = os.getenv("LIBRETRANSLATE_API_KEY")

    try:
        chunks = _chunk_text(text)
        chunks = [c for c in chunks if c.strip()]
        if not chunks:
            return "No text content to translate."

        max_workers = min(5, len(chunks))
        translated_parts = [""] * len(chunks)
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {
                ex.submit(_libretranslate_chunk, c, target_language, url, api_key): i
                for i, c in enumerate(chunks)
            }
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    tr = future.result()
                    if tr:
                        translated_parts[idx] = tr
                except Exception:
                    translated_parts[idx] = ""
        parts = [p for p in translated_parts if p]
        return "\n".join(parts) if parts else "Translation returned empty."
    except Exception as e:
        return mymemory_text(text, target_language, error=str(e))


def _mymemory_chunk(chunk: str, source: str, target: str) -> str:
    """Translate a single chunk via MyMemory."""
    if not chunk.strip():
        return ""
    r = requests.get(
        "https://api.mymemory.translated.net/get",
        params={"q": chunk, "langpair": f"{source}|{target}"},
        timeout=60,
    )
    r.raise_for_status()
    return ((r.json().get("responseData") or {}).get("translatedText") or "").strip()


def mymemory_text(text, target_language, error=None):
    """
    Backup fallback using MyMemory. Uses parallel chunk translation for faster
    large-document processing.
    """
    if not text or not text.strip():
        return "No text content to translate."

    source = os.getenv("MYMEMORY_SOURCE_LANG", "en").strip()
    target = target_language.strip()

    try:
        chunks = _chunk_text(text)
        chunks = [c for c in chunks if c.strip()]
        if not chunks:
            return "No text content to translate."

        max_workers = min(5, len(chunks))
        translated_parts = [""] * len(chunks)
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {ex.submit(_mymemory_chunk, c, source, target): i for i, c in enumerate(chunks)}
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    tr = future.result()
                    if tr:
                        translated_parts[idx] = tr
                except Exception:
                    translated_parts[idx] = ""
        parts = [p for p in translated_parts if p]
        return "\n".join(parts) if parts else "Translation returned empty."
    except Exception as e:
        prefix = "LibreTranslate failed" + (f" ({error})" if error else "")
        return f"{prefix}. MyMemory fallback also failed: {str(e)}"
