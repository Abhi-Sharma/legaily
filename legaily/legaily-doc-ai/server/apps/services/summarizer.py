import cohere
import os

def summarize_text(text):
    """
    Summarize text using Cohere API with adaptive summary length.

    :param text: The text to summarize
    :return: Summarized text
    """
    if not text or not text.strip():
        return "No text content to summarize."
    
    try:
        cohere_api_key = os.getenv("COHERE_API_KEY")
        if not cohere_api_key:
            # Free/no-key fallback: local Transformers summarizer (slow on first run).
            return summarize_with_transformers(text)

        # Summarize API was removed Sep 2025; use Chat API (ClientV2).
        co = cohere.ClientV2(api_key=cohere_api_key)
        word_count = len(text.split())
        if word_count < 30:
            length_instruction = "in 1–2 sentences"
        elif word_count < 100:
            length_instruction = "in a short paragraph"
        else:
            length_instruction = "in a concise paragraph (key points only)"

        message = f"Summarize the following text {length_instruction}. Do not add any introduction or meta-comment, only the summary.\n\n{text}"
        model = os.getenv("COHERE_CHAT_MODEL", "command-a-03-2025")

        response = co.chat(
            model=model,
            messages=[{"role": "user", "content": message}],
        )

        if response.message and getattr(response.message, "content", None) and len(response.message.content) > 0:
            first = response.message.content[0]
            return getattr(first, "text", str(first)) or "No summary returned."
        return "No summary returned."

    except Exception as e:
        return f"Error during summarization: {str(e)}"


_TRANSFORMERS_SUMMARIZER = None


def summarize_with_transformers(text: str) -> str:
    """
    Offline summarization fallback using HuggingFace Transformers.
    This avoids requiring any paid API key, but may download a model on first run.
    """
    global _TRANSFORMERS_SUMMARIZER

    if not text or not text.strip():
        return "No text content to summarize."

    try:
        from transformers import pipeline

        if _TRANSFORMERS_SUMMARIZER is None:
            # Smaller model than BART-large; good default for CPU environments.
            _TRANSFORMERS_SUMMARIZER = pipeline(
                "summarization",
                model=os.getenv("HF_SUMMARY_MODEL", "sshleifer/distilbart-cnn-12-6"),
            )

        # Trim extremely long inputs to avoid model context overflow.
        # This is a simple heuristic; better chunking can be added later.
        max_chars = int(os.getenv("SUMMARY_MAX_CHARS", "12000"))
        clipped = text.strip()
        if len(clipped) > max_chars:
            clipped = clipped[:max_chars]

        out = _TRANSFORMERS_SUMMARIZER(
            clipped,
            max_length=int(os.getenv("SUMMARY_MAX_LENGTH", "160")),
            min_length=int(os.getenv("SUMMARY_MIN_LENGTH", "40")),
            do_sample=False,
        )

        if isinstance(out, list) and out and isinstance(out[0], dict):
            return out[0].get("summary_text") or "No summary returned."
        return str(out) if out is not None else "No summary returned."
    except Exception as e:
        return f"Summarization unavailable (no COHERE_API_KEY and local model failed): {str(e)}"
