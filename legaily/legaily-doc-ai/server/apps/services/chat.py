"""
Legal AI Assistant: Cohere Chat API with a legal-focused system prompt.
"""
import os
import cohere


LEGAL_SYSTEM_PROMPT = """You are a helpful Legal AI Assistant focused on Indian law and general legal concepts.
- Give clear, accurate, and concise answers.
- Prefer bullet points when listing provisions or steps.
- If asked about the Indian Penal Code (IPC), Indian Contract Act, or other Indian laws, answer based on general knowledge and recommend consulting a qualified lawyer for specific advice.
- Always add a brief disclaimer that your answers are for general information only and not legal advice."""


def chat(message: str, history: list[dict] | None = None) -> str:
    """
    Send a user message to the Legal AI Assistant and return the assistant reply.
    history: list of {"role": "user"|"assistant", "content": "..."} for context.
    """
    if not message or not message.strip():
        return "Please enter a question."

    api_key = os.getenv("COHERE_API_KEY")
    if not api_key:
        return "Legal AI Assistant is not configured (missing COHERE_API_KEY)."

    try:
        co = cohere.ClientV2(api_key=api_key)
        model = os.getenv("COHERE_CHAT_MODEL", "command-a-03-2025")

        messages = [{"role": "system", "content": LEGAL_SYSTEM_PROMPT}]
        if history:
            for h in history[-10:]:  # keep last 10 turns
                messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": message.strip()})

        response = co.chat(model=model, messages=messages)

        if response.message and getattr(response.message, "content", None) and len(response.message.content) > 0:
            first = response.message.content[0]
            return getattr(first, "text", str(first)) or "No response."
        return "No response."
    except Exception as e:
        return f"Error from Legal AI Assistant: {str(e)}"
