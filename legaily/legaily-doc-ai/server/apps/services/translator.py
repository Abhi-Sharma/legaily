import os
import requests

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
    This is an unofficial endpoint; keep as a fallback for development/demo use.
    """
    if not text or not text.strip():
        return "No text content to translate."

    try:
        r = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={
                "client": "gtx",
                "sl": "auto",
                "tl": target_language,
                "dt": "t",
                "q": text,
            },
            timeout=60,
        )
        r.raise_for_status()

        # Response is a nested JSON array; first element contains translated chunks.
        data = r.json()
        chunks = (data[0] or []) if isinstance(data, list) and len(data) > 0 else []
        translated = "".join((c[0] or "") for c in chunks if isinstance(c, list) and len(c) > 0)
        return translated or "Translation returned empty result."
    except Exception as e:
        # Optional fallback: LibreTranslate if configured, else MyMemory.
        try:
            return libretranslate_text(text, target_language)
        except Exception:
            return mymemory_text(text, target_language, error=str(e))


def libretranslate_text(text, target_language):
    """
    Free fallback translator using LibreTranslate.
    - Default URL uses a public instance; for reliability, self-host and set LIBRETRANSLATE_URL.
    - Supports auto source language detection.
    """
    if not text or not text.strip():
        return "No text content to translate."

    url = os.getenv("LIBRETRANSLATE_URL", "https://libretranslate.com/translate").strip()
    api_key = os.getenv("LIBRETRANSLATE_API_KEY")

    try:
        # LibreTranslate accepts JSON; keep it simple and robust.
        payload = {
            "q": text,
            "source": "auto",
            "target": target_language,
            "format": "text",
        }
        if api_key:
            payload["api_key"] = api_key

        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        translated = data.get("translatedText")
        if translated:
            return translated

        # Some instances may return a different shape; fall back gracefully.
        return str(data) if data else "Translation succeeded but response was empty."
    except Exception as e:
        # Last-resort no-key fallback: MyMemory (requires a fixed source language pair).
        return mymemory_text(text, target_language, error=str(e))


def mymemory_text(text, target_language, error=None):
    """
    Backup fallback using MyMemory (no API key by default, but rate-limited).
    MyMemory requires a source|target langpair; we assume source is English.
    """
    if not text or not text.strip():
        return "No text content to translate."

    try:
        source = os.getenv("MYMEMORY_SOURCE_LANG", "en").strip()
        target = target_language.strip()
        r = requests.get(
            "https://api.mymemory.translated.net/get",
            params={"q": text, "langpair": f"{source}|{target}"},
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        translated = (data.get("responseData") or {}).get("translatedText")
        if translated:
            return translated
        return str(data) if data else "Translation succeeded but response was empty."
    except Exception as e:
        prefix = "LibreTranslate failed" + (f" ({error})" if error else "")
        return f"{prefix}. MyMemory fallback also failed: {str(e)}"
