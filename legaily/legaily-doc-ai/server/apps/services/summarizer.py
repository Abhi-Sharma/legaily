import cohere
import os
import re

# Keywords that indicate a legal case/judgment document
_LEGAL_CASE_INDICATORS = [
    "petitioner", "respondent", "bench", "judgment", "supreme court",
    "high court", "vs", "v.", "citation", "headnote", "act", "article",
    "writ petition", "civil appeal", "criminal appeal", "date of judgment",
    "judges", "cj", "j.", "plaintiff", "defendant", "ratio decidendi",
    "obiter dicta", "order", "appeal", "respondent", "court of",
]


def _looks_like_legal_case(text: str) -> bool:
    """Heuristic: text likely represents an Indian court judgment/case."""
    if not text or len(text) < 100:
        return False
    sample = text[:12000].lower()
    hits = sum(1 for k in _LEGAL_CASE_INDICATORS if k in sample)
    return hits >= 3


def _build_legal_case_prompt(text: str) -> str:
    """Structured prompt for summarizing legal cases with key case elements."""
    # Truncate very long inputs but keep key metadata at the start
    max_chars = int(os.getenv("SUMMARY_MAX_CHARS", "12000"))
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[... text truncated ...]"

    return """You are summarizing an Indian legal case/judgment. Extract and present the following in a clear, structured format. Use bullet points or short sections. If a field is not found, write "Not specified."

1. **Case Name**: Petitioner vs Respondent (from the heading)
2. **Date of Judgment**: 
3. **Court & Bench**: Names of judges
4. **Citation**: e.g., AIR, SCR, SCC citations
5. **Acts/Articles Involved**: Key statutes and constitutional articles
6. **Facts (Brief)**: Core facts leading to the dispute (2–4 sentences)
7. **Issues**: Main legal questions the court decided
8. **Judgment/Outcome**: Who won; relief granted; orders passed
9. **Key Legal Principles**: Important ratio/legal holdings (bullet points)

Write only the structured summary. No preamble. Use plain English.

---
Document:
""" + text


def _build_generic_prompt(text: str, length_instruction: str) -> str:
    return f"Summarize the following text {length_instruction}. Do not add any introduction or meta-comment, only the summary.\n\n{text}"


def summarize_text(text):
    """
    Summarize text using Cohere API. For legal cases, produces a structured
    case summary (parties, bench, issues, judgment, etc.). Otherwise, produces
    a concise summary.
    """
    if not text or not text.strip():
        return "No text content to summarize."

    try:
        cohere_api_key = os.getenv("COHERE_API_KEY")
        if not cohere_api_key:
            return summarize_with_transformers(text)

        co = cohere.ClientV2(api_key=cohere_api_key)
        is_legal = _looks_like_legal_case(text)

        if is_legal:
            message = _build_legal_case_prompt(text)
        else:
            word_count = len(text.split())
            if word_count < 30:
                length_instruction = "in 1–2 sentences"
            elif word_count < 100:
                length_instruction = "in a short paragraph"
            else:
                length_instruction = "in a concise paragraph (key points only)"
            message = _build_generic_prompt(text, length_instruction)

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
    For legal cases, prepends a brief structured extraction from the first portion.
    """
    global _TRANSFORMERS_SUMMARIZER

    if not text or not text.strip():
        return "No text content to summarize."

    if _looks_like_legal_case(text):
        # For legal cases without Cohere: extract structured info from first ~8000 chars
        head = text[:8000].strip()
        parts = []
        for label, pattern in [
            ("Case/Parties", r"(?:PETITIONER|Plaintiff|Appellant)[:\s]+([^\n]+(?:Vs?\.?[^\n]+)?)", re.I),
            ("Date", r"DATE\s+OF\s+JUDGMENT[:\s]*([^\n]+)", re.I),
            ("Bench", r"BENCH[:\s]*([^\n]+(?:\n[^\n]+){0,3})", re.I),
            ("Citation", r"CITATION[:\s]*([^\n]+)", re.I),
            ("Acts/Articles", r"ACT[:\s]*([^\n]+)", re.I),
            ("Headnote", r"HEADNOTE[:\s]*([^\n]+(?:\n[^\n]+){0,5})", re.I),
        ]:
            m = re.search(pattern, head, re.M | re.S)
            if m:
                val = m.group(1).strip()[:400].replace("\n", " ")
                parts.append(f"**{label}**: {val}")
        if parts:
            structured = "\n".join(parts)
            try:
                from transformers import pipeline
                if _TRANSFORMERS_SUMMARIZER is None:
                    _TRANSFORMERS_SUMMARIZER = pipeline(
                        "summarization",
                        model=os.getenv("HF_SUMMARY_MODEL", "sshleifer/distilbart-cnn-12-6"),
                    )
                body = text[4000:12000]  # middle section for summary
                out = _TRANSFORMERS_SUMMARIZER(
                    body[:4000],
                    max_length=120,
                    min_length=30,
                    do_sample=False,
                )
                extra = ""
                if isinstance(out, list) and out and isinstance(out[0], dict):
                    extra = out[0].get("summary_text", "")
                return f"{structured}\n\n**Summary of reasoning**: {extra}" if extra else structured
            except Exception:
                return structured

    try:
        from transformers import pipeline

        if _TRANSFORMERS_SUMMARIZER is None:
            _TRANSFORMERS_SUMMARIZER = pipeline(
                "summarization",
                model=os.getenv("HF_SUMMARY_MODEL", "sshleifer/distilbart-cnn-12-6"),
            )

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
