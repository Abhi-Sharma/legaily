from fastapi import APIRouter, File, UploadFile, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
from apps.services.ocr import extract_text
from apps.services.summarizer import summarize_text
from apps.services.translator import google_translate_text
from apps.services.chat import chat as legal_chat

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    history: list[dict] | None = None


@router.post("/chat/")
async def chat_endpoint(body: ChatRequest):
    """Legal AI Assistant: reply using Cohere Chat API."""
    try:
        reply = legal_chat(body.message, body.history)
        return {"reply": reply}
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})

# Summarization endpoint (unchanged)
@router.post("/process/")
async def process_file(file: UploadFile = File(...), action: str = Form("summarize")):
    try:
        text = await extract_text(file)

        if action == "summarize":
            result = summarize_text(text)
        else:
            return JSONResponse(status_code=400, content={"message": "Invalid action specified"})

        return {"result": result}
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

        return {"result": result}
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})
