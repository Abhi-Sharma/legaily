import os
import uuid
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import cohere

# We will cache the embeddings model so it doesn't load every time
_embeddings_model = None

def get_embeddings_model():
    global _embeddings_model
    if _embeddings_model is None:
        _embeddings_model = HuggingFaceEmbeddings(model_name="law-ai/InLegalBERT")
    return _embeddings_model

from collections import OrderedDict

# We will keep a very simple in-memory LRU cache of FAISS indexes per summary to avoid rebuilding
# if the user asks multiple questions on the same summary, while preventing memory leaks.
MAX_CACHE_SIZE = 50
_vectorstore_cache = OrderedDict()

def get_or_create_vectorstore(summary_text: str, session_id: str):
    if session_id in _vectorstore_cache:
        # Move to end to mark as recently used
        vectorstore = _vectorstore_cache.pop(session_id)
        _vectorstore_cache[session_id] = vectorstore
        return vectorstore


    # More granular chunking for extreme precision on specific legal clauses
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=150)
    chunks = text_splitter.split_text(summary_text)

    # Fallback if summary is too short or chunking fails
    if not chunks:
        chunks = [summary_text]

    embeddings = get_embeddings_model()
    # Create the FAISS index
    vectorstore = FAISS.from_texts(chunks, embeddings)
    
    # Store in cache and maintain LRU size
    _vectorstore_cache[session_id] = vectorstore
    if len(_vectorstore_cache) > MAX_CACHE_SIZE:
        _vectorstore_cache.popitem(last=False)  # Remove oldest entry
        
    return vectorstore


def qa_over_summary(summary_text: str, question: str, history: list[dict] = None) -> str:
    """
    RAG pipeline:
    1. Create/Retrieve FAISS index for the summary.
    2. Retrieve relevant context.
    3. Ask Cohere LLM using the context.
    """
    if not summary_text or not summary_text.strip():
        return "No summary provided."
    if not question or not question.strip():
        return "No question provided."

    api_key = os.getenv("COHERE_API_KEY")
    if not api_key:
        return "Legal AI Assistant is not configured (missing COHERE_API_KEY)."

    try:
        co = cohere.ClientV2(api_key=api_key)
        
        # --- NEW OPTIMIZATION: Long-Context Strategy ---
        # If the document is small enough (arbitrary 60k chars ~15k tokens), 
        # bypass RAG and provide the WHOLE document for 100% precision.
        if len(summary_text) < 60000:
            print(f"Using Full-Context strategy for document of size {len(summary_text)}")
            context = summary_text
        else:
            # Fallback to RAG + Rerank for very large files
            print(f"Using RAG+Rerank strategy for large document of size {len(summary_text)}")
            session_id = str(hash(summary_text))
            vectorstore = get_or_create_vectorstore(summary_text, session_id)

            # 1. Broad Retrieval
            retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 25})
            candidate_docs = retriever.invoke(question)
            
            # 2. Precision Reranking
            doc_texts = [doc.page_content for doc in candidate_docs]
            rerank_response = co.rerank(
                model="rerank-english-v3.0",
                query=question,
                documents=doc_texts,
                top_n=8
            )
            
            relevant_chunks = []
            for result in rerank_response.results:
                relevant_chunks.append(doc_texts[result.index])
            
            context = "\n\n".join(relevant_chunks)

        # 3. Final Synthesis
        model = os.getenv("COHERE_CHAT_MODEL", "command-a-03-2025")

        system_prompt = f"""You are a High-Precision Legal AI Assistant. Your task is to provide extremely accurate answers based ONLY on the provided CASE DOCUMENT CONTEXT.
IMPORTANT RULES:
- You have the {'FULL TEXT' if len(summary_text) < 60000 else 'relevant excerpts'} of the case document provided below.
- If the answer is found, provide a detailed response citing specific names, dates, or clauses from the document.
- If the answer is NOT explicitly mentioned or cannot be inferred from the context, state: "The provided Case Document does not contain information regarding [user's query]." 
- Do not provide external legal advice or common knowledge.
- Focus on accuracy and evidence from the text.

CONTEXT FROM CASE DOCUMENT:
{context}
"""
        messages = [{"role": "system", "content": system_prompt}]
        
        if history:
            for h in history[-5:]:  # limit history depth
                role = "assistant" if h.get("role") == "assistant" else "user"
                messages.append({"role": role, "content": h.get("content", "")})
                
        messages.append({"role": "user", "content": question})

        # Using temperature 0.3 for a balance between factual accuracy and natural delivery
        response = co.chat(model=model, messages=messages, temperature=0.3)

        if response.message and getattr(response.message, "content", None) and len(response.message.content) > 0:
            first = response.message.content[0]
            answer = getattr(first, "text", str(first))
            return answer
            
        return "No response could be generated."
        
    except Exception as e:
        return f"Error in QA pipeline: {str(e)}"
