import os
import re
import requests

# Max chars per chunk to avoid 414 Request-URI Too Large (MyMemory uses GET)
# and to stay within typical API limits for LibreTranslate/gtx
_TRANSLATE_CHUNK_MAX = int(os.getenv("TRANSLATE_CHUNK_MAX", "800"))


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


def google_translate_text(text, target_language):
    if not text or not text.strip():
        return "No text content to translate."

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        # Free/no-key fallback: unofficial Google Translate endpoint (client=gtx).
        # Note: This is best-effort and may be rate-limited; for production, set GOOGLE_API_KEY.
        return gtx_translate_text(text, target_language)

    try:
        # Split text into lines (preserving bullet points or paragraphs)
        lines = text.split("\n")
        
        # Filter out empty lines
        lines = [line.strip() for line in lines if line.strip()]

        # Prepare to collect translated lines
        translated_lines = []

        # Translate each line individually
        for line in lines:
            params = {
                "q": line,
                "target": target_language,
                "key": api_key
            }
            response = requests.post("https://translation.googleapis.com/language/translate/v2", data=params)
            response.raise_for_status()
            translated_line = response.json()["data"]["translations"][0]["translatedText"]
            translated_lines.append(translated_line)

        # Join translated lines back with newline character to preserve the format
        translated_text = "\n".join(translated_lines)
        return translated_text

    except Exception as e:
        return f"Error during Google translation: {str(e)}"

def gtx_translate_text(text, target_language):
    """
    No-key translation via translate.googleapis.com (client=gtx).
    Chunks long text to avoid URL size limits.
    """
    if not text or not text.strip():
        return "No text content to translate."

    try:
        chunks = _chunk_text(text)
        translated_parts = []
        for chunk in chunks:
            if not chunk.strip():
                continue
            r = requests.get(
                "https://translate.googleapis.com/translate_a/single",
                params={
                    "client": "gtx",
                    "sl": "auto",
                    "tl": target_language,
                    "dt": "t",
                    "q": chunk,
                },
                timeout=60,
            )
            r.raise_for_status()
            data = r.json()
            frags = (data[0] or []) if isinstance(data, list) and len(data) > 0 else []
            tr = "".join((c[0] or "") for c in frags if isinstance(c, list) and len(c) > 0)
            if tr:
                translated_parts.append(tr)
        return "\n".join(translated_parts) if translated_parts else "Translation returned empty result."
    except Exception as e:
        try:
            return libretranslate_text(text, target_language)
        except Exception:
            return mymemory_text(text, target_language, error=str(e))


def libretranslate_text(text, target_language):
    """
    Free fallback translator using LibreTranslate.
    Chunks long text to avoid 400 Bad Request / payload limits.
    """
    if not text or not text.strip():
        return "No text content to translate."

    url = os.getenv("LIBRETRANSLATE_URL", "https://libretranslate.com/translate").strip()
    api_key = os.getenv("LIBRETRANSLATE_API_KEY")

    try:
        chunks = _chunk_text(text)
        translated_parts = []
        for chunk in chunks:
            if not chunk.strip():
                continue
            payload = {
                "q": chunk,
                "source": "auto",
                "target": target_language,
                "format": "text",
            }
            if api_key:
                payload["api_key"] = api_key

            resp = requests.post(url, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            tr = data.get("translatedText")
            if tr:
                translated_parts.append(tr)
        return "\n".join(translated_parts) if translated_parts else "Translation returned empty."
    except Exception as e:
        return mymemory_text(text, target_language, error=str(e))


def mymemory_text(text, target_language, error=None):
    """
    Backup fallback using MyMemory. Chunks text to avoid 414 Request-URI Too Large
    (MyMemory uses GET with text in URL; URLs are length-limited).
    """
    if not text or not text.strip():
        return "No text content to translate."

    source = os.getenv("MYMEMORY_SOURCE_LANG", "en").strip()
    target = target_language.strip()

    try:
        chunks = _chunk_text(text)
        translated_parts = []
        for chunk in chunks:
            if not chunk.strip():
                continue
            r = requests.get(
                "https://api.mymemory.translated.net/get",
                params={"q": chunk, "langpair": f"{source}|{target}"},
                timeout=60,
            )
            r.raise_for_status()
            data = r.json()
            tr = (data.get("responseData") or {}).get("translatedText")
            if tr:
                translated_parts.append(tr)
        return "\n".join(translated_parts) if translated_parts else "Translation returned empty."
    except Exception as e:
        prefix = "LibreTranslate failed" + (f" ({error})" if error else "")
        return f"{prefix}. MyMemory fallback also failed: {str(e)}"
