from fastapi import APIRouter, File, UploadFile, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
from apps.services.ocr import extract_text
from apps.services.summarizer import summarize_text
from apps.services.translator import google_translate_text
from apps.services.chat import chat as legal_chat
from apps.services.qa_summary import qa_over_summary
from apps.services.drafter import generate_draft
from apps.services.slre import get_structured_response

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    history: list[dict] | None = None
    mode: str = "detailed"

class QASummaryRequest(BaseModel):
    summary_text: str
    question: str
    history: list[dict] | None = None

class DraftRequest(BaseModel):
    template_id: str
    data: dict
    refine_tone: bool = False


@router.post("/qa_summary/")
async def qa_summary_endpoint(body: QASummaryRequest):
    """Answers a question based on a provided summary using RAG."""
    try:
        reply = qa_over_summary(body.summary_text, body.question, body.history)
        return {"reply": reply}
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})

def _safe_str(s) -> str:
    """Strip surrogate characters that cause UnicodeEncodeError in Starlette's UTF-8 encoder.
    Cohere emoji responses can contain surrogate pairs (\uD800-\uDFFF) that are invalid UTF-8."""
    return str(s).encode("utf-8", errors="surrogatepass").decode("utf-8", errors="replace")


@router.post("/chat/")
async def chat_endpoint(body: ChatRequest):
    """Legal AI Assistant: reply using SLRE or Cohere Chat API."""
    import traceback as _tb
    import logging as _log
    _logger = _log.getLogger(__name__)
    try:
        result = get_structured_response(body.message, body.mode)

        if not isinstance(result, dict):
            raise ValueError(f"Unexpected SLRE result type: {type(result)}")

        if "error" in result:
            reply = legal_chat(body.message, body.history)
            return JSONResponse(content={"reply": _safe_str(reply), "type": "raw"})

        data = result.get("data")
        rtype = result.get("type", "detailed")

        if data is None:
            raise ValueError("SLRE returned None for 'data' field.")

        return JSONResponse(content={"reply": _safe_str(data), "type": _safe_str(rtype)})

    except Exception as e:
        _logger.error("chat_endpoint error: %s\n%s", e, _tb.format_exc())
        return JSONResponse(status_code=500, content={"message": _safe_str(e)})

# Summarization endpoint (unchanged)
@router.post("/process/")
async def process_file(file: UploadFile = File(...), action: str = Form("summarize")):
    try:
        text = await extract_text(file)

        if action == "summarize":
            result = summarize_text(text)
        else:
            return JSONResponse(status_code=400, content={"message": "Invalid action specified"})

        return {"result": result, "full_text": text}
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})

# Unified translation endpoint using Google Translate API
@router.post("/translate/")
async def google_translate_file(
    file: UploadFile = File(...), 
    target_language: str = Form(...)
):
    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        print("Google API Key:", api_key)
        text = await extract_text(file)

        # Indian languages with reliable support (Google Translate API + gtx/LibreTranslate/MyMemory)
        google_languages = {
            "english": "en",
            "hindi": "hi",
            "kannada": "kn",
            "tamil": "ta",
            "telugu": "te",
            "marathi": "mr",
            "malayalam": "ml",
            "bengali": "bn",
            "gujarati": "gu",
            "punjabi": "pa",
            "assamese": "as",
            "urdu": "ur",
            "odia": "or",
        }

        target_language_lower = target_language.lower()

        if target_language_lower not in google_languages:
            return JSONResponse(status_code=400, content={"message": "Unsupported language"})

        language_code = google_languages[target_language_lower]
        result = google_translate_text(text, language_code)

        return {"result": result, "full_text": text}
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})

@router.post("/draft/")
async def draft_endpoint(body: DraftRequest):
    """Generates a court-ready legal draft."""
    try:
        result = generate_draft(body.template_id, body.data, body.refine_tone)
        return {"result": result}
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})
