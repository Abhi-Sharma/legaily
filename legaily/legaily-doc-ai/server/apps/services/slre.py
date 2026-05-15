"""
TLIRAS — Trusted Legal Intelligence & Response Assurance System
Legaily Legal Query Backend | v4.0

Pipeline: Retrieve → Validate → Repair → Enrich → Generate → Verify

KEY GUARANTEES:
- No [value not provided] placeholders ever reach the user
- No [invalid section removed] gaps — decimal sections are repaired, not deleted
- Classification always resolved: section number → keyword → smart defaults
- Confidence expressed as percentage with explanation
- Context Guard: no hallucinated scenarios
"""
import os
import re
import json
import logging
import pickle
import hashlib
import cohere
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# ── Response Cache ──────────────────────────────────────────────────────────
# Keyed by SHA-256(query+mode). Stores up to 256 recent results in memory.
_RESPONSE_CACHE: dict = {}
_CACHE_MAX_SIZE = 256

def _cache_key(query: str, mode: str) -> str:
    return hashlib.sha256(f"{query.strip().lower()}|{mode}".encode()).hexdigest()

def _cache_get(query: str, mode: str):
    return _RESPONSE_CACHE.get(_cache_key(query, mode))

def _cache_set(query: str, mode: str, result: dict):
    key = _cache_key(query, mode)
    if len(_RESPONSE_CACHE) >= _CACHE_MAX_SIZE:
        # Evict the oldest entry
        oldest = next(iter(_RESPONSE_CACHE))
        del _RESPONSE_CACHE[oldest]
    _RESPONSE_CACHE[key] = result

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

INDEX_PATH = os.path.join(os.path.dirname(__file__), "../../legal_statutes_index")

def tokenize_for_bm25(text: str) -> list[str]:
    return [t for t in re.split(r'\W+', text.lower()) if t]

# ── Singletons ─────────────────────────────────────────────────────────────
_embeddings = None
_vectorstore = None
_cohere_client = None
_bm25_data = None

def _get_embeddings():
    global _embeddings
    if _embeddings is None:
        logger.info("Loading InLegalBERT (first call)...")
        _embeddings = HuggingFaceEmbeddings(model_name="law-ai/InLegalBERT")
    return _embeddings

def _get_vectorstore():
    global _vectorstore
    if _vectorstore is None:
        if not os.path.exists(INDEX_PATH):
            raise FileNotFoundError(f"FAISS index not found at {INDEX_PATH}.")
        logger.info("Loading FAISS index (first call)...")
        _vectorstore = FAISS.load_local(
            INDEX_PATH, _get_embeddings(), allow_dangerous_deserialization=True
        )
    return _vectorstore

def _get_bm25():
    global _bm25_data
    if _bm25_data is None:
        bm25_path = os.path.join(INDEX_PATH, "bm25_index.pkl")
        if not os.path.exists(bm25_path):
            raise FileNotFoundError(f"BM25 index not found at {bm25_path}.")
        logger.info("Loading BM25 index (first call)...")
        with open(bm25_path, "rb") as f:
            _bm25_data = pickle.load(f)
    return _bm25_data

def _get_cohere():
    global _cohere_client
    if _cohere_client is None:
        api_key = os.getenv("COHERE_API_KEY")
        if not api_key:
            raise EnvironmentError("COHERE_API_KEY is not set.")
        _cohere_client = cohere.ClientV2(api_key=api_key)
    return _cohere_client


# ===========================================================================
# LEGAL KNOWLEDGE BASE  — Verified from Schedule 1, CrPC / BNSS Annexure
# ===========================================================================
LEGAL_KNOWLEDGE_BASE = {
    # General Exceptions / Defenses
    "100":  {"cognizable":"N/A (Legal Defense)","bailable":"N/A (Legal Defense)", "compoundable":"N/A (Legal Defense)","triable_by":"N/A (Depends on offence accused)", "bns":"Section 38 BNS"},
    "101":  {"cognizable":"N/A (Legal Defense)","bailable":"N/A (Legal Defense)", "compoundable":"N/A (Legal Defense)","triable_by":"N/A (Depends on offence accused)", "bns":"Section 39 BNS"},
    # Culpable Homicide / Murder
    "299":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 100 BNS"},
    "300":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 101 BNS"},
    # Section 301 — Culpable Homicide by Transferred Malice (Non-Bailable; BNS Sec 102)
    "301":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 102 BNS"},
    "302":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 103 BNS"},
    "303":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 104 BNS"},
    "304":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 105 BNS"},
    "304A": {"cognizable":"Yes","bailable":"Yes","compoundable":"No","triable_by":"Chief Judicial Magistrate", "bns":"Section 106 BNS"},
    "304B": {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 80 BNS"},
    "306":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 108 BNS"},
    "307":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 109 BNS"},
    # Section 309 — Attempt to commit suicide (bailable IPC offence; BNS Sec 226 is narrower: punishes suicide attempt to compel/restrain a public servant)
    "309":  {"cognizable":"Yes","bailable":"Yes","compoundable":"No","triable_by":"Chief Judicial Magistrate", "bns":"Section 226 BNS (narrowed scope — applies only when attempt is to compel/restrain a public servant)"},
    # Section 310 — Definition of a Thug (NOT a procedural rule; BNS: Omitted / reorganised under organised crime)
    "310":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Omitted in BNS (reorganised under organised crime provisions)"},
    # Section 311 — Punishment for Thuggery (Life imprisonment + fine)
    "311":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Omitted in BNS (reorganised under organised crime provisions)"},
    # Hurt / Grievous Hurt
    "323":  {"cognizable":"No", "bailable":"Yes","compoundable":"Yes","triable_by":"Magistrate of First Class","bns":"Section 115 BNS"},
    # Section 324 — Voluntarily causing hurt by dangerous weapons (Non-Bailable per CrPC Amendment Act 2005; compoundable only with court permission)
    "324":  {"cognizable":"Yes","bailable":"No", "compoundable":"Yes","triable_by":"Magistrate of First Class","bns":"Section 117 BNS"},
    "325":  {"cognizable":"No", "bailable":"Yes","compoundable":"Yes","triable_by":"Magistrate of First Class","bns":"Section 116 BNS"},
    "326":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 117 BNS"},
    "326A": {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 124 BNS"},
    "326B": {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 125 BNS"},
    # Assault / Criminal Force
    "351":  {"cognizable":"No", "bailable":"Yes","compoundable":"Yes","triable_by":"Magistrate of First Class","bns":"Section 131 BNS"},
    "352":  {"cognizable":"No", "bailable":"Yes","compoundable":"Yes","triable_by":"Magistrate of First Class","bns":"Section 132 BNS"},
    "354":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Chief Judicial Magistrate", "bns":"Section 74 BNS"},
    "354A": {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Magistrate of First Class", "bns":"Section 75 BNS"},
    "354B": {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 76 BNS"},
    "354C": {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Magistrate of First Class", "bns":"Section 77 BNS"},
    "354D": {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Magistrate of First Class", "bns":"Section 78 BNS"},
    # Sexual Offences
    "375":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 63 BNS"},
    "376":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 64 BNS"},
    "376A": {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 66 BNS"},
    # Section 377 — Unnatural Offences (consensual adult acts omitted in BNS post-Navtej Singh Johar; non-consensual/bestiality aspects remain cognizable)
    "377":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Partially omitted in BNS (consensual acts decriminalised; non-consensual / bestiality under other provisions)"},
    # Kidnapping / Abduction
    "363":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Chief Judicial Magistrate", "bns":"Section 137 BNS"},
    "364":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 140 BNS"},
    "364A": {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 141 BNS"},
    "366":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 142 BNS"},
    # Theft
    "378":  {"cognizable":"Yes","bailable":"Yes","compoundable":"No","triable_by":"Magistrate of First Class", "bns":"Section 303 BNS"},
    "379":  {"cognizable":"Yes","bailable":"Yes","compoundable":"No","triable_by":"Magistrate of First Class", "bns":"Section 303 BNS"},
    "380":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Magistrate of First Class", "bns":"Section 305 BNS"},
    "381":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Magistrate of First Class", "bns":"Section 306 BNS"},
    "382":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Magistrate of First Class", "bns":"Section 307 BNS"},
    # Robbery / Dacoity
    "390":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 309 BNS"},
    "392":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 309 BNS"},
    "395":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 310 BNS"},
    "396":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 310 BNS"},
    # Cheating / Fraud
    "415":  {"cognizable":"No", "bailable":"Yes","compoundable":"Yes","triable_by":"Magistrate of First Class","bns":"Section 318 BNS"},
    "416":  {"cognizable":"No", "bailable":"Yes","compoundable":"Yes","triable_by":"Magistrate of First Class","bns":"Section 319 BNS"},
    "417":  {"cognizable":"No", "bailable":"Yes","compoundable":"Yes","triable_by":"Magistrate of First Class","bns":"Section 318 BNS"},
    "418":  {"cognizable":"No", "bailable":"Yes","compoundable":"Yes","triable_by":"Magistrate of First Class","bns":"Section 318 BNS"},
    "419":  {"cognizable":"Yes","bailable":"Yes","compoundable":"Yes","triable_by":"Magistrate of First Class","bns":"Section 319 BNS"},
    "420":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Magistrate of First Class", "bns":"Section 318 BNS"},
    # Forgery
    "463":  {"cognizable":"No", "bailable":"Yes","compoundable":"No","triable_by":"Magistrate of First Class", "bns":"Section 334 BNS"},
    "465":  {"cognizable":"No", "bailable":"Yes","compoundable":"No","triable_by":"Magistrate of First Class", "bns":"Section 335 BNS"},
    "467":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 336 BNS"},
    "468":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Chief Judicial Magistrate", "bns":"Section 336 BNS"},
    "471":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Magistrate of First Class", "bns":"Section 340 BNS"},
    # Criminal Conspiracy
    "107":  {"cognizable":"No", "bailable":"Yes","compoundable":"No","triable_by":"Magistrate of First Class", "bns":"Section 45 BNS"},
    "120A": {"cognizable":"No", "bailable":"Yes","compoundable":"No","triable_by":"Magistrate of First Class", "bns":"Section 61 BNS"},
    "120B": {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 61 BNS"},
    # Defamation
    "499":  {"cognizable":"No", "bailable":"Yes","compoundable":"Yes","triable_by":"Magistrate of First Class","bns":"Section 356 BNS"},
    "500":  {"cognizable":"No", "bailable":"Yes","compoundable":"Yes","triable_by":"Magistrate of First Class","bns":"Section 356 BNS"},
    # Mischief / Trespass
    "425":  {"cognizable":"No", "bailable":"Yes","compoundable":"Yes","triable_by":"Magistrate of First Class","bns":"Section 324 BNS"},
    "426":  {"cognizable":"No", "bailable":"Yes","compoundable":"Yes","triable_by":"Magistrate of First Class","bns":"Section 324 BNS"},
    "427":  {"cognizable":"No", "bailable":"Yes","compoundable":"No","triable_by":"Magistrate of First Class", "bns":"Section 324 BNS"},
    "441":  {"cognizable":"No", "bailable":"Yes","compoundable":"Yes","triable_by":"Magistrate of First Class","bns":"Section 329 BNS"},
    "447":  {"cognizable":"Yes","bailable":"Yes","compoundable":"Yes","triable_by":"Magistrate of First Class","bns":"Section 329 BNS"},
    "451":  {"cognizable":"Yes","bailable":"Yes","compoundable":"Yes (with Court permission)","triable_by":"Any Magistrate", "bns":"Section 331(2) BNS"},
    # Domestic Violence / Dowry
    "498A": {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Magistrate of First Class", "bns":"Section 85 BNS"},
    # Public Order
    # Section 124A — Sedition (omitted in BNS; replaced by Section 152 BNS — Acts endangering sovereignty, unity and integrity of India)
    "124A": {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 152 BNS (replaces Sedition — endangering sovereignty, unity and integrity of India)"},
    "153A": {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 196 BNS"},
    # Property / Trust
    "406":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Magistrate of First Class", "bns":"Section 316 BNS"},
    "409":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 316 BNS"},
    "411":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Magistrate of First Class", "bns":"Section 317 BNS"},
    # Road / Negligence
    "279":  {"cognizable":"Yes","bailable":"Yes","compoundable":"Yes","triable_by":"Magistrate of First Class","bns":"Section 281 BNS"},
    # Section 277 — Fouling water of public spring or reservoir (Non-Cognizable; BNS Sec 279)
    "277":  {"cognizable":"No", "bailable":"Yes","compoundable":"No", "triable_by":"Any Magistrate", "bns":"Section 279 BNS"},
    # Common Intention / Unlawful Assembly
    "34":   {"cognizable":"Depends on offence","bailable":"Depends on offence","compoundable":"Depends on offence","triable_by":"Depends on offence", "bns":"Section 3(5) BNS"},
    "149":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 190 BNS"},
    "141":  {"cognizable":"No", "bailable":"Yes","compoundable":"No","triable_by":"Any Magistrate",            "bns":"Section 189 BNS"},
    # Public Servant Obstruction
    "186":  {"cognizable":"No", "bailable":"Yes","compoundable":"No","triable_by":"Any Magistrate",            "bns":"Section 221 BNS"},
    "189":  {"cognizable":"No", "bailable":"Yes","compoundable":"No","triable_by":"Any Magistrate",            "bns":"Section 224 BNS"},
    # Perjury / False Evidence
    "191":  {"cognizable":"No", "bailable":"Yes","compoundable":"No","triable_by":"Magistrate of First Class", "bns":"Section 227 BNS"},
    "193":  {"cognizable":"No", "bailable":"Yes","compoundable":"No","triable_by":"Magistrate of First Class", "bns":"Section 229 BNS"},
    "194":  {"cognizable":"No", "bailable":"Yes","compoundable":"No","triable_by":"Court of Session",          "bns":"Section 230 BNS"},
    # Currency Forgery (FICN)
    "489A": {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 178 BNS"},
    "489B": {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 179 BNS"},
    "489C": {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Magistrate of First Class", "bns":"Section 180 BNS"},
    # Rioting
    "147":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Magistrate of First Class", "bns":"Section 191 BNS"},
    "148":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 191 BNS"},
    # Wrongful Confinement / Restraint
    "339":  {"cognizable":"No", "bailable":"Yes","compoundable":"Yes","triable_by":"Any Magistrate",           "bns":"Section 126 BNS"},
    "340":  {"cognizable":"No", "bailable":"Yes","compoundable":"Yes","triable_by":"Any Magistrate",           "bns":"Section 127 BNS"},
    "342":  {"cognizable":"Yes","bailable":"Yes","compoundable":"Yes","triable_by":"Any Magistrate",           "bns":"Section 127 BNS"},
    "343":  {"cognizable":"No", "bailable":"Yes","compoundable":"Yes","triable_by":"Any Magistrate",           "bns":"Section 128 BNS"},
    "344":  {"cognizable":"No", "bailable":"No", "compoundable":"No", "triable_by":"Magistrate of First Class","bns":"Section 128 BNS"},
    "345":  {"cognizable":"No", "bailable":"No", "compoundable":"No", "triable_by":"Magistrate of First Class","bns":"Section 128 BNS"},
    "346":  {"cognizable":"No", "bailable":"No", "compoundable":"No", "triable_by":"Magistrate of First Class","bns":"Section 128 BNS"},
    "347":  {"cognizable":"No", "bailable":"No", "compoundable":"No", "triable_by":"Magistrate of First Class","bns":"Section 129 BNS"},
    "348":  {"cognizable":"No", "bailable":"No", "compoundable":"No", "triable_by":"Magistrate of First Class","bns":"Section 129 BNS"},
    # Chapter XIV — Public Health, Safety, Nuisance (IPC 268–278)
    "268":  {"cognizable":"No", "bailable":"Yes","compoundable":"No", "triable_by":"Any Magistrate",           "bns":"Section 281 BNS"},
    "269":  {"cognizable":"No", "bailable":"Yes","compoundable":"No", "triable_by":"Any Magistrate",           "bns":"Section 282 BNS"},
    "270":  {"cognizable":"No", "bailable":"No", "compoundable":"No", "triable_by":"Magistrate of First Class","bns":"Section 283 BNS"},
    "271":  {"cognizable":"No", "bailable":"No", "compoundable":"No", "triable_by":"Magistrate of First Class","bns":"Section 284 BNS"},
    "272":  {"cognizable":"No", "bailable":"Yes","compoundable":"No", "triable_by":"Any Magistrate",           "bns":"Section 285 BNS"},
    "273":  {"cognizable":"No", "bailable":"Yes","compoundable":"No", "triable_by":"Any Magistrate",           "bns":"Section 286 BNS"},
    "274":  {"cognizable":"No", "bailable":"Yes","compoundable":"No", "triable_by":"Any Magistrate",           "bns":"Section 287 BNS"},
    "275":  {"cognizable":"No", "bailable":"Yes","compoundable":"No", "triable_by":"Any Magistrate",           "bns":"Section 288 BNS"},
    "276":  {"cognizable":"No", "bailable":"Yes","compoundable":"No", "triable_by":"Any Magistrate",           "bns":"Section 289 BNS"},
    "277":  {"cognizable":"No", "bailable":"Yes","compoundable":"No", "triable_by":"Any Magistrate",           "bns":"Section 290 BNS"},
    "278":  {"cognizable":"No", "bailable":"Yes","compoundable":"Yes","triable_by":"Any Magistrate",           "bns":"Section 291 BNS"},
    # Chapter IX — Public Servants engaging in trade / bid-rigging
    "168":  {"cognizable":"No", "bailable":"Yes","compoundable":"No","triable_by":"Any Magistrate",           "bns":"Section 202 BNS"},
    "169":  {"cognizable":"No", "bailable":"Yes","compoundable":"No","triable_by":"Any Magistrate",           "bns":"Section 203 BNS"},
    # Robbery and Dacoity (IPC Chapter XVII)
    "390":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 309 BNS"},
    "391":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 310 BNS"},
    "392":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 309 BNS"},
    "393":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 309 BNS"},
    "394":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 309 BNS"},
    "395":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 310 BNS"},
    "396":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 310 BNS"},
    # Attempt to Murder / Attempt to Culpable Homicide
    "307":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 109 BNS"},
    "308":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Magistrate of First Class","bns":"Section 110 BNS"},
    # Armed Forces offences (IPC Chapter VII)
    "131":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 67 BNS"},
    "132":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 68 BNS"},
    "133":  {"cognizable":"No", "bailable":"Yes","compoundable":"No","triable_by":"Court of Session",          "bns":"Section 69 BNS"},
    # Defamation (IPC 499–502)
    "499":  {"cognizable":"No", "bailable":"Yes","compoundable":"Yes","triable_by":"Any Magistrate",           "bns":"Section 356 BNS"},
    "500":  {"cognizable":"No", "bailable":"Yes","compoundable":"Yes","triable_by":"Any Magistrate",           "bns":"Section 356 BNS"},
    "501":  {"cognizable":"No", "bailable":"Yes","compoundable":"Yes","triable_by":"Any Magistrate",           "bns":"Section 354 BNS"},
    "502":  {"cognizable":"No", "bailable":"Yes","compoundable":"Yes","triable_by":"Any Magistrate",           "bns":"Section 355 BNS"},
    # Criminal Intimidation
    "503":  {"cognizable":"No", "bailable":"Yes","compoundable":"No","triable_by":"Any Magistrate",           "bns":"Section 351 BNS"},
    "506":  {"cognizable":"No", "bailable":"Yes","compoundable":"No","triable_by":"Any Magistrate",           "bns":"Section 351 BNS"},
    # Using forged document as genuine
    "471":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Magistrate of First Class", "bns":"Section 340 BNS"},
    # General Attempt Provision
    "511":  {"cognizable":"No", "bailable":"Yes","compoundable":"No","triable_by":"Any Magistrate",           "bns":"Section 62 BNS"},
    # False Information / Defamation of Justice
    "203":  {"cognizable":"No", "bailable":"Yes","compoundable":"No","triable_by":"Any Magistrate",           "bns":"Section 237 BNS"},
    "204":  {"cognizable":"No", "bailable":"Yes","compoundable":"No","triable_by":"Any Magistrate",           "bns":"Section 238 BNS"},
    "211":  {"cognizable":"No", "bailable":"Yes","compoundable":"No","triable_by":"Magistrate of First Class","bns":"Section 245 BNS"},
    # Dishonest Misappropriation of Property
    "403":  {"cognizable":"No", "bailable":"Yes","compoundable":"Yes","triable_by":"Any Magistrate",           "bns":"Section 316 BNS"},
    "404":  {"cognizable":"No", "bailable":"Yes","compoundable":"No", "triable_by":"Any Magistrate",           "bns":"Section 317 BNS"},
    # Criminal Breach of Trust
    "405":  {"cognizable":"No", "bailable":"Yes","compoundable":"No","triable_by":"Any Magistrate",           "bns":"Section 316 BNS"},
    "406":  {"cognizable":"No", "bailable":"Yes","compoundable":"Yes","triable_by":"Any Magistrate",           "bns":"Section 316 BNS"},
    "409":  {"cognizable":"Yes","bailable":"No", "compoundable":"No","triable_by":"Court of Session",          "bns":"Section 316 BNS"},
    # General Exceptions (IPC Chapter IV — Defenses, not offences)
    "76":   {"cognizable":"N/A (General Exception)","bailable":"N/A (General Exception)","compoundable":"N/A (General Exception)","triable_by":"N/A (General Exception)","bns":"Section 22 BNS"},
    "77":   {"cognizable":"N/A (General Exception)","bailable":"N/A (General Exception)","compoundable":"N/A (General Exception)","triable_by":"N/A (General Exception)","bns":"Section 23 BNS"},
    "78":   {"cognizable":"N/A (General Exception)","bailable":"N/A (General Exception)","compoundable":"N/A (General Exception)","triable_by":"N/A (General Exception)","bns":"Section 24 BNS"},
    "79":   {"cognizable":"N/A (General Exception)","bailable":"N/A (General Exception)","compoundable":"N/A (General Exception)","triable_by":"N/A (General Exception)","bns":"Section 25 BNS"},
    "80":   {"cognizable":"N/A (General Exception)","bailable":"N/A (General Exception)","compoundable":"N/A (General Exception)","triable_by":"N/A (General Exception)","bns":"Section 26 BNS"},
    "81":   {"cognizable":"N/A (General Exception)","bailable":"N/A (General Exception)","compoundable":"N/A (General Exception)","triable_by":"N/A (General Exception)","bns":"Section 27 BNS"},
    "96":   {"cognizable":"N/A (General Exception)","bailable":"N/A (General Exception)","compoundable":"N/A (General Exception)","triable_by":"N/A (General Exception)","bns":"Section 34 BNS"},
    "97":   {"cognizable":"N/A (General Exception)","bailable":"N/A (General Exception)","compoundable":"N/A (General Exception)","triable_by":"N/A (General Exception)","bns":"Section 35 BNS"},
    "100":  {"cognizable":"N/A (General Exception)","bailable":"N/A (General Exception)","compoundable":"N/A (General Exception)","triable_by":"N/A (General Exception)","bns":"Section 38 BNS"},
}

# ===========================================================================
# SECTION CONTENT HINTS — Authoritative statutory descriptions injected into
# the verified data block to prevent the LLM from mischaracterising a section.
# ===========================================================================
SECTION_CONTENT_HINTS: dict = {
    "100": (
        "Section 100 IPC — Right of private defence of the body extending to causing death: "
        "Enumerates circumstances where the right of private defence extends to voluntarily causing death "
        "or any other harm to the assailant. STATUTORY ROLE: This is a General Exception/Defense, not an offence. "
        "It carries no punishment. BNS Equivalent: Section 38 BNS."
    ),
    "101": (
        "Section 101 IPC — Right of private defence extending to causing any harm other than death: "
        "When the offence is not one of the descriptions enumerated in Section 100 IPC, "
        "the right of private defence extends only to causing any harm other than death. "
        "STATUTORY ROLE: This is a General Exception/Defense, not an offence. "
        "It carries no punishment and has no cognizable/bailable classification. "
        "BNS Equivalent: Section 39 BNS."
    ),
    "301": (
        "Section 301 IPC — Culpable Homicide by Transferred Malice: "
        "If a person, by doing an act with the intention or knowledge to cause death "
        "of one person, accidentally causes the death of another person, the act is "
        "treated as culpable homicide (not murder). This doctrine is called 'Transferred Malice'. "
        "It is a NON-BAILABLE offence punished under Section 304 IPC. "
        "BNS Equivalent: Section 102 BNS."
    ),
    "302": (
        "Section 302 IPC — Punishment for Murder: "
        "Whoever commits murder shall be punished with death or imprisonment for life "
        "and shall also be liable to fine. It is cognizable, non-bailable, and triable "
        "exclusively by the Court of Session. "
        "BNS Equivalent: Section 103 BNS (NOT omitted — Section 103 BNS covers punishment for murder; "
        "Section 103(2) BNS specifically addresses mob lynching with enhanced punishment)."
    ),
    "309": (
        "Section 309 IPC — Attempt to commit suicide: "
        "Whoever attempts to commit suicide and does any act towards the commission of such offence, "
        "shall be punished with simple imprisonment up to one year, or fine, or both. "
        "IMPORTANT BNS NUANCE: Section 226 BNS is NOT a general substitute for Section 309 IPC. "
        "Section 226 BNS specifically punishes a person who attempts suicide with the intent to "
        "compel or restrain a public servant from discharging their legal duty. "
        "General attempted suicide is largely decriminalised under the Mental Healthcare Act, 2017 (Section 115)."
    ),
    "324": (
        "Section 324 IPC — Voluntarily causing hurt by dangerous weapons or means: "
        "Whoever, except in the case provided for by Section 334, voluntarily causes hurt by means "
        "of any instrument for shooting, stabbing or cutting, or by fire or heated substance, "
        "or by any poison or corrosive substance, etc., shall be punished with imprisonment up to "
        "3 years, or fine, or both. "
        "BAILABILITY NOTE: Section 324 was made NON-BAILABLE by the Code of Criminal Procedure "
        "(Amendment) Act, 2005. It is cognizable and non-bailable. BNS Equivalent: Section 117 BNS."
    ),
    "377": (
        "Section 377 IPC — Unnatural Offences: "
        "Whoever voluntarily has carnal intercourse against the order of nature with any man, "
        "woman or animal, shall be punished with imprisonment for life or imprisonment up to "
        "10 years and fine. "
        "CRITICAL BNS STATUS: Following the Supreme Court ruling in Navtej Singh Johar v. Union of India (2018), "
        "consensual same-sex acts between adults were decriminalised. The BNS has omitted Section 377 "
        "as a standalone provision; non-consensual acts are covered under rape/sexual assault provisions "
        "(Sections 63–66 BNS), and bestiality may be addressed under residual provisions. "
        "It is NOT a general carryover in the BNS."
    ),
    "124A": (
        "Section 124A IPC — Sedition: "
        "Whoever, by words either spoken or written, or by signs, or by visible representation, "
        "or otherwise, brings or attempts to bring into hatred or contempt, or excites or attempts "
        "to excite disaffection towards the Government established by law in India, shall be punished "
        "with imprisonment for life, to which fine may be added, or with imprisonment up to 3 years. "
        "BNS REPLACEMENT: Section 124A IPC (Sedition) has been OMITTED in the BNS. It is replaced by "
        "Section 152 BNS — 'Acts endangering sovereignty, unity and integrity of India', which is "
        "broader in scope and carries imprisonment up to 7 years or life imprisonment."
    ),
    "310": (
        "Section 310 IPC — Definition of a 'Thug': "
        "Whoever at any time after the passing of this Act shall have been habitually "
        "associated with any other or others for the purpose of committing robbery or "
        "child-stealing by means of or accompanied with murder, is a Thug. "
        "CRITICAL: This section defines THUGGERY — it has nothing to do with previous "
        "convictions or procedural rules. Do NOT confuse with Section 310 CrPC or Section 75 IPC. "
        "Section 311 IPC prescribes the punishment (imprisonment for life and fine). "
        "BNS Status: The specific offence of Thuggery has been omitted/reorganised under organised crime provisions in the BNS."
    ),
    "311": (
        "Section 311 IPC — Punishment for Being a Thug: "
        "Whoever is a Thug (as defined in Section 310 IPC) shall be punished with "
        "imprisonment for life and shall also be liable to fine. "
        "BNS Status: Omitted/reorganised under organised crime provisions in the BNS."
    ),
    "277": (
        "Section 277 IPC — Fouling water of public spring or reservoir: "
        "Whoever voluntarily corrupts or fouls the water of any public spring or reservoir, "
        "so as to render it less fit for the purpose for which it is ordinarily used, "
        "shall be punished with imprisonment up to 3 months, or with fine up to 500 Rupees, or both. "
        "LEGAL CLASSIFICATION: It is a NON-COGNIZABLE and bailable offence. "
        "BNS Equivalent: Section 279 BNS (Note: The BNS has increased the fine amount significantly)."
    ),
    "451": (
        "Section 451 IPC — House-trespass in order to commit offence punishable with imprisonment: "
        "Whoever commits house-trespass in order to the committing of any offence punishable with "
        "imprisonment, shall be punished with imprisonment up to 2 years and fine. "
        "TIERED PUNISHMENT: If the offence intended to be committed is theft, the term of "
        "imprisonment may be extended to 7 years. "
        "LEGAL CLASSIFICATION: It is cognizable, bailable, and COMPOUNDABLE with the permission "
        "of the court. BNS Equivalent: Section 331(2) BNS."
    ),
    "391": (
        "Section 391 IPC — Definition of Dacoity: "
        "When five or more persons conjointly commit or attempt to commit a robbery, "
        "or where the whole number of persons conjointly committing or attempting to commit a robbery, "
        "and persons present and aiding such commission or attempt, amount to five or more, "
        "every person so committing, attempting or aiding, is said to commit dacoity. "
        "IMPORTANT: Section 391 is a DEFINITION section only — it does NOT prescribe punishment. "
        "The punishment for dacoity is prescribed under Section 395 IPC "
        "(imprisonment for life OR rigorous imprisonment up to 10 years AND fine). "
        "Both Sections 391 and 395 are cognizable, non-bailable, triable by Court of Session. "
        "BNS Equivalent: Section 310 BNS."
    ),
    "395": (
        "Section 395 IPC — Punishment for Dacoity: "
        "Whoever commits dacoity (as defined in Section 391 IPC) shall be punished with "
        "imprisonment for life, or with rigorous imprisonment for a term which may extend to "
        "ten years, and shall also be liable to fine. "
        "Cognizable, non-bailable, non-compoundable, triable exclusively by Court of Session. "
        "BNS Equivalent: Section 310 BNS."
    ),
    "501": (
        "Section 501 IPC — Printing or Engraving Matter Known to be Defamatory: "
        "Whoever prints or engraves any matter, knowing or having good reason to believe that "
        "such matter is defamatory of any person, shall be punished with simple imprisonment "
        "for a term which may extend to TWO YEARS, or with fine, or with both. "
        "CRITICAL: This section is about DEFAMATION (printing/engraving), NOT attempts to commit offences. "
        "DO NOT confuse with Section 511 IPC, which is the general attempt provision. "
        "BNS Equivalent: Section 354 BNS."
    ),
    "511": (
        "Section 511 IPC — Punishment for Attempting to Commit Offences Punishable with Imprisonment for Life or Other Imprisonment: "
        "Whoever attempts to commit an offence punishable by this Code with imprisonment for life or "
        "imprisonment, or to cause such an offence to be committed, and in such attempt does any act "
        "towards the commission of the offence, shall, where no express provision is made by this Code "
        "for the punishment of such attempt, be punished with imprisonment of any description provided "
        "for the offence, for a term which may extend to one-half of the imprisonment for life or, "
        "as the case may be, one-half of the longest term of imprisonment provided for that offence, "
        "or with fine, or with both. "
        "BNS Equivalent: Section 62 BNS."
    ),
    "132": (
        "Section 132 IPC — Abetment of Mutiny (if mutiny is committed in consequence thereof): "
        "Whoever abets the committing of mutiny by an officer, soldier, sailor or airman, in the Army, "
        "Navy or Air Force of the Government of India, shall, if mutiny be committed in consequence of "
        "that abetment, be punished with death or with imprisonment for life, and shall also be liable to fine. "
        "CRITICAL: Section 132 IPC is about ABETMENT OF MUTINY in the Armed Forces. "
        "It has NOTHING to do with unlawful assembly, riots, or public disorder. "
        "DO NOT confuse with Sections 141–149 IPC (Unlawful Assembly). "
        "Classification: Cognizable, Non-bailable, Non-compoundable, Court of Session. "
        "BNS Equivalent: Section 68 BNS."
    ),
    "307": (
        "Section 307 IPC — Attempt to commit Murder: "
        "Whoever does any act with such intention or knowledge, and under such circumstances that, "
        "if he by that act caused death, he would be guilty of murder, shall be punished with "
        "imprisonment of either description for a term which may extend to ten years, and shall also "
        "be liable to fine; and if hurt is caused to any person by such act, the offender shall be "
        "liable either to imprisonment for life, or to such punishment as is hereinbefore mentioned. "
        "CRITICAL: Section 307 IPC is a CRIMINAL OFFENCE (Attempt to Murder), NOT a defense or exception. "
        "It carries punishment of up to 10 years, or life imprisonment if hurt is caused. "
        "It is Cognizable, Non-bailable, Non-compoundable, triable by Court of Session. "
        "BNS Equivalent: Section 109 BNS."
    ),
    "299": (
        "Section 299 IPC — Culpable Homicide: "
        "Whoever causes death by doing an act with the intention of causing death, or with the "
        "intention of causing such bodily injury as is likely to cause death, or with the knowledge "
        "that he is likely by such act to cause death, commits the offence of culpable homicide. "
        "CRITICAL: Section 299 IPC defines CULPABLE HOMICIDE — the base offence of unlawful killing. "
        "It is NOT about sedition, religion, or public order. "
        "It is Cognizable, Non-bailable, Non-compoundable, triable by Court of Session. "
        "Punishment is prescribed under Section 304 IPC (up to 10 years or life imprisonment). "
        "BNS Equivalent: Section 100 BNS."
    ),
    "300": (
        "Section 300 IPC — Murder (definition): "
        "Culpable homicide is MURDER if the act by which death is caused is done with the intention "
        "of causing death; or with the intention of causing such bodily injury as the offender knows "
        "to be likely to cause death; or with the intention of causing bodily injury sufficient in "
        "the ordinary course of nature to cause death; or if the doer of the act knows it to be so "
        "imminently dangerous that it must in all probability cause death or such bodily injury as is "
        "likely to cause death. "
        "CRITICAL: Section 300 IPC defines when culpable homicide AMOUNTS TO MURDER. "
        "Punishment for murder is prescribed in Section 302 IPC (death or life imprisonment). "
        "It is Cognizable, Non-bailable, Non-compoundable, triable by Court of Session. "
        "BNS Equivalent: Section 101 BNS."
    ),
    "364A": (
        "Section 364A IPC — Kidnapping for Ransom: "
        "Whoever kidnaps or abducts any person or keeps a person in detention after such kidnapping "
        "or abduction, and threatens to cause death or hurt to such person, or by his conduct gives "
        "rise to a reasonable apprehension that such person may be put to death or hurt, or causes "
        "hurt to such person in order to compel the Government or any other person to pay ransom, "
        "shall be punishable with death, or imprisonment for life, and shall also be liable to fine. "
        "CRITICAL: Section 364A is specifically about KIDNAPPING FOR RANSOM — it requires a demand for "
        "ransom or coercion as an element. It is NOT a general kidnapping + murder provision; "
        "that is covered by Section 364 IPC. "
        "It is Cognizable, Non-bailable, Non-compoundable, triable by Court of Session. "
        "BNS Equivalent: Section 141 BNS."
    ),
    "471": (
        "Section 471 IPC — Using as Genuine a Forged Document or Electronic Record: "
        "Whoever fraudulently or dishonestly uses as genuine any document or electronic record "
        "which he knows or has reason to believe to be a forged document or electronic record, "
        "shall be punished in the same manner as if he had forged such document or electronic record. "
        "CRITICAL: Section 471 IPC is about USING a forged document — it is a distinct offence from "
        "forgery (Section 465/467/468). The KEY element is knowingly presenting a forged document as genuine. "
        "It is Cognizable, Non-bailable, Non-compoundable, triable by Magistrate of First Class. "
        "BNS Equivalent: Section 340 BNS. "
        "DO NOT confuse with recovery proceedings, money statutes, or Sanhita financial provisions."
    ),
    "503": (
        "Section 503 IPC — Criminal Intimidation: "
        "Whoever threatens another person with any injury to his person, reputation or property, "
        "or to the person or reputation of any one in whom that person is interested, with intent "
        "to cause alarm to that person, or to cause that person to do any act which he is not "
        "legally bound to do, or to omit to do any act which that person is legally entitled to do, "
        "as the means of avoiding the execution of such threat, commits criminal intimidation. "
        "CRITICAL: Section 503 IPC defines CRIMINAL INTIMIDATION by threats. It is NOT about "
        "property seizure, financial recovery, or police procedure. "
        "It is Non-Cognizable, Bailable, Non-compoundable, triable by Any Magistrate. "
        "Punishment is prescribed in Section 506 IPC (up to 2 years, or 7 years for threat of death/grievous hurt). "
        "BNS Equivalent: Section 351 BNS."
    ),
}

# BNS reverse lookup
BNS_TO_IPC = {}
for _s, _d in LEGAL_KNOWLEDGE_BASE.items():
    _bns = _d.get("bns", "")
    _m = re.match(r'Section (\d+[A-Z]?) BNS', _bns)
    if _m:
        BNS_TO_IPC[_m.group(1)] = _s


# ===========================================================================
# CRIME KEYWORD MAP (for natural language queries without section numbers)
# Maps crime keywords → primary IPC section → LEGAL_KNOWLEDGE_BASE lookup
# ===========================================================================
CRIME_KEYWORD_MAP = {
    # Cheating / Fraud
    "cheating":           "420",
    "cheat":              "420",
    "fraud":              "420",
    "fraudulent":         "420",
    "deception":          "420",
    "deceit":             "420",
    "dishonest inducement":"420",
    "forgery":            "468",
    "forged":             "468",
    "fake document":      "468",
    "personation":        "419",
    "impersonation":      "419",
    # Murder / Homicide
    "murder":                 "302",
    "homicide":               "302",
    "killing":                "302",
    "culpable homicide":      "304",
    "transferred malice":     "301",
    "transferred intent":     "301",
    "private defense":        "100",
    "private defence":        "100",
    "self defense":           "100",
    "self defence":           "100",
    "right of private defense":"100",
    "right of private defence":"100",
    "attempt to murder":      "307",
    "abetment of suicide":    "306",
    "suicide":                "309",
    "dowry death":            "304B",
    "negligent death":        "304A",
    "negligent driving":      "304A",
    # Thuggery / Organised Crime
    "thug":                   "310",
    "thuggery":               "310",
    "thuggee":                "310",
    "habitual robbery murder":"310",
    "organized crime":        "310",
    "organised crime":        "310",
    # BNS-era specific offences
    "mob lynching":           "302",  # Sec 103(2) BNS specifically addresses mob lynching
    "lynching":               "302",
    "snatching":              "379",  # Now a specific offence under Section 304 BNS
    "chain snatching":        "379",
    "hit and run":            "304A", # Now specifically Section 106(2) BNS
    "hit-and-run":            "304A",
    # Hurt
    "hurt":               "325",
    "grievous hurt":      "326",
    "acid attack":        "326A",
    "voluntarily causing hurt":"323",
    # Assault
    "assault":            "352",
    "criminal force":     "352",
    "outrage modesty":    "354",
    "voyeurism":          "354C",
    "stalking":           "354D",
    # Sexual
    "rape":                  "376",
    "sexual assault":        "376",
    "sexual harassment":     "354A",
    "unnatural offence":     "377",
    "unnatural sex":         "377",
    "bestiality":            "377",
    # Trespass
    "house trespass":        "451",
    "house-trespass":        "451",
    "trespass in house":     "451",
    # Public Nuisance
    "fouling water":         "277",
    "polluting water":       "277",
    "poisoning spring":      "277",
    # Kidnapping
    "kidnapping":         "363",
    "abduction":          "363",
    "ransom":             "364A",
    # Theft / Property
    "theft":              "379",
    "stealing":           "379",
    "burglary":           "380",
    "robbery":            "392",
    "dacoity":            "395",
    "extortion":          "390",
    "mischief":           "426",
    "criminal trespass":  "447",
    "trespass":           "447",
    "criminal breach of trust":"406",
    "embezzlement":       "409",
    "misappropriation":   "406",
    "receiving stolen":   "411",
    # Domestic
    "domestic violence":  "498A",
    "cruelty by husband": "498A",
    "dowry":              "498A",
    "dowry harassment":   "498A",
    # Public order
    "sedition":           "124A",
    "hate speech":        "153A",
    "defamation":         "500",
    "criminal defamation":"500",
    # Conspiracy
    "criminal conspiracy":"120B",
    "conspiracy":         "120B",
    "abetment":           "107",
    # Negligence / Roads
    "rash driving":       "279",
    "reckless driving":   "279",
    "road accident":      "279",
    "negligent accident": "304A",
    # Fix #8: Extended keyword map for common/colloquial legal queries
    # Assault / Modesty
    "eve teasing":              "354A",
    "sexual harassment at workplace": "354A",
    "outraging modesty":        "354",
    # Sexual Offences
    "attempt to rape":          "376",
    "gang rape":                "376",
    "marital rape":             "375",
    # Acid / Grievous
    "acid attack":              "326A",
    "acid throwing":            "326A",
    "grievous hurt acid":       "326A",
    # Homicide
    "dowry murder":             "304B",
    "aiding suicide":           "306",
    "abetment to suicide":      "306",
    # Rioting / Assembly
    "rioting":                  "147",
    "riot":                     "147",
    "unlawful assembly":        "149",
    "common intention":         "34",
    # Perjury
    "perjury":                  "193",
    "false evidence":           "191",
    "false statement":          "191",
    # Currency
    "counterfeit currency":     "489A",
    "fake note":                "489B",
    "fake currency":            "489A",
    "ficn":                     "489A",
    # Confinement
    "wrongful confinement":     "342",
    "wrongful restraint":       "339",
    "illegal detention":        "342",
    # Cyber / Fraud
    "online fraud":             "420",
    "cybercrime":               "420",
    "phishing":                 "420",
    # Public Servant
    "obstructing public servant": "186",
    "threatening public servant": "189",
    # Encounter
    "fake encounter":           "302",
    "encounter killing":        "302",
    # Police brutality
    "police brutality":         "323",
}


def _resolve_classification(query: str, section_number: str = None, code_hint: str = None) -> tuple:
    """
    Returns (section_key, verified_classification_dict, resolution_method).
    Tries 3 strategies in order:
    1. Direct section number lookup in LEGAL_KNOWLEDGE_BASE
    2. Crime keyword match → LEGAL_KNOWLEDGE_BASE
    3. None (graceful fallback)
    """
    # Strategy 1: exact section number
    if section_number:
        sec = section_number
        if code_hint == "BNS":
            ipc_sec = BNS_TO_IPC.get(sec)
            if ipc_sec:
                sec = ipc_sec
        data = LEGAL_KNOWLEDGE_BASE.get(sec)
        if data:
            return sec, data, "verified_db"

    # Strategy 2: crime keyword scan (longest match first for specificity)
    query_lower = query.lower()
    best_key, best_sec = None, None
    best_len = 0
    for kw, sec in CRIME_KEYWORD_MAP.items():
        if kw in query_lower and len(kw) > best_len:
            best_len = len(kw)
            best_key = kw
            best_sec = sec

    if best_sec and best_sec in LEGAL_KNOWLEDGE_BASE:
        return best_sec, LEGAL_KNOWLEDGE_BASE[best_sec], "keyword_map"

    # Strategy 3: no match
    return None, None, "general_principles"


# ===========================================================================
# Section Query Detection
# ===========================================================================
_SECTION_RE = re.compile(
    # No-space: "ipc302", "ipc56", "BNS123" — must be first to match before word boundaries split them
    r'(?:IPC|BNS|BNSS|BSA)(\d+[A-Z]?)'
    # Spaced with law code before number: "IPC 302", "BNS 56"
    r'|(?:IPC|BNS|BNSS|BSA)\s+(\d+[A-Z]?)'
    # Number after code: "302 IPC", "56 BNS"
    r'|(\d+[A-Z]?)\s+(?:IPC|BNS|BNSS|BSA)'
    # "section 302", "sec 56", "s.302"
    r'|(?:section|sec|s\.?)\s*(\d+[A-Z]?)',
    re.IGNORECASE
)
_CODE_RE = re.compile(r'\b(IPC|BNS|BNSS|BSA)\b', re.IGNORECASE)

def _extract_section_query(query: str):
    m = _SECTION_RE.search(query)
    if not m:
        return None, None
    # Pick whichever group matched (groups 1–4 across the 4 alternatives)
    section = next((g for g in m.groups() if g is not None), None)
    if not section:
        return None, None
    cm = _CODE_RE.search(query)
    code = cm.group(1).upper() if cm else None
    return section.upper(), code


def _direct_section_lookup(section_number: str, preferred_law: str = None):
    """
    Search FAISS docstore for chunks matching section_number.
    When preferred_law is 'IPC', rank IPC chunks first and BNS/BNSS/BSA last.
    This prevents cross-statute collision: IPC §85 vs BNS §85 are different provisions.
    """
    vs = _get_vectorstore()
    matches = []
    for doc_id, doc in vs.docstore._dict.items():
        if str(doc.metadata.get('section_number', '')).upper() == section_number:
            matches.append(doc)

    if not matches:
        return matches

    # Sort: preferred statute first, everything else after
    def _statute_rank(doc):
        law = doc.metadata.get('law_name', '').upper()
        if preferred_law and preferred_law.upper() in law:
            return 0   # exact match → top
        # BNS/BNSS/BSA are cross-statute noise when user asked for IPC
        for noise in ('BNS', 'BNSS', 'BSA'):
            if noise in law:
                return 2   # push to bottom
        return 1           # neutral (IPC without explicit label, etc.)

    matches.sort(key=_statute_rank)
    return matches


# ===========================================================================
# SLRESL System Prompts — Domain-Specific Templates
# ===========================================================================
CRIMINAL_TEMPLATE = """You are the Structured Legal Response Enhancement & Safety Layer (SLRESL) for Legaily.

You produce concise, legally accurate responses for Indian criminal law queries suitable for legal datasets and structured summaries.

══════════════════════════════════════════
MANDATORY 7-PART RESPONSE FORMAT
══════════════════════════════════════════
Write each section in ORDER. Do NOT skip, merge, or reorder any section.

📌 Quick Summary
Write exactly 2 bullet lines using "- " prefix. No inline blocks. Example format:
- [What this offence is in plain language — no classification terms.]
- Punishment: [key punishment in one short phrase.]

⚖️ Applicable Law
- Lead with the IPC section as the primary reference (e.g., "Section 420 IPC (Cheating)").
- ONLY add BNS equivalent if it is present in the VERIFIED DATA block.

📝 Legal Explanation
- Precise 3–5 sentence explanation of what this provision covers.
- If it is a 'Defense', explain the justification it provides.

✅ Essential Ingredients / Conditions
- Bullet list of the legal elements the prosecution must prove OR the conditions required for this defense to apply.

⛓️ Punishment
- State ONE unified punishment as prescribed in applicable law.
- CRITICAL INSTRUCTION: If this is a 'Liability Attribution' section (e.g., Section 34, 149, 301), state: "No standalone punishment; punishment depends on the substantive offence committed."
- CRITICAL INSTRUCTION: If this is a 'Defense' or 'General Exception' (e.g., Sections 76–106 IPC), state: "None. This is a legal justification/defense which exempts the act from being a crime."

📊 Legal Classification
[REPRODUCE CLASSIFICATION EXACTLY FROM THE VERIFIED DATA BLOCK — DO NOT MODIFY]
- Cognizable: [from VERIFIED DATA]
- Bailable: [from VERIFIED DATA]
- Compoundable: [from VERIFIED DATA]
- Triable By: [from VERIFIED DATA]

🔍 Illustrative Example
- Generate a legally neutral hypothetical fact pattern (e.g. "Person A does X to Person B") demonstrating the offence or doctrine in a realistic way. No real names.

📑 Legal Authorities
- List ONLY the IPC/BNS sections that are the direct subject of or explicitly define this specific provision.
- Maximum 3 entries. Format: "Section [Number] IPC" or "Section [Number] BNS".
- DO NOT list CrPC sections, general sections like Section 34 or 149, or any section not directly cited in the retrieved legal context.
- DO NOT fabricate or infer section relationships not present in the retrieved text.

══════════════════════════════════════════
ABSOLUTE GOVERNANCE RULES
1. NEVER output placeholders like [value not provided].
2. NEVER fabricate a scenario outside the designated illustrative example.
3. NEVER output decimal section numbers.
4. NEVER skip, shorten, or merge ANY of the 7 sections above.
5. ALWAYS reproduce VERIFIED DATA classification exactly.
6. NEVER add a disclaimer or 'Note' section.
7. NEVER include the words cognizable, non-cognizable, bailable, non-bailable, or compoundable in the Quick Summary. Those terms belong ONLY in the Legal Classification section.
8. If the user message says [UNVERIFIED SECTION], you MUST write "Refer to Schedule 1, CrPC / BNSS" for EVERY classification field (Cognizable, Bailable, Compoundable, Triable By). NEVER guess or infer these values.
"""

CIVIL_TEMPLATE = """You are the Structured Legal Response Enhancement & Safety Layer (SLRESL) for Legaily.
You produce lawyer-grade, concise, and legally accurate responses for Indian civil law queries (e.g., CPC, Contracts, Family Law, Property).

══════════════════════════════════════════
MANDATORY RESPONSE FORMAT
══════════════════════════════════════════
Write each section in ORDER. Do NOT skip, merge, or reorder any section.

📌 Quick Summary
Write exactly 3 lines:
- Line 1: What this civil concept/remedy is.
- Line 2: The primary relief or court action involved.
- Line 3: Confirmation that this is civil in nature.

⚖️ Applicable Law
- Lead with the primary statute (e.g., "Order 39 Rule 1 CPC").

📝 Legal Meaning
- Precise 3–5 sentence explanation of this principle.

✅ Conditions & Ingredients
- Bullet list of conditions that must be satisfied to claim this remedy.

🔍 Illustrative Example
- Generate a legally neutral hypothetical fact pattern demonstrating how this civil rule works in practice. No real names.

⚠️ Consequences of Violation
- What happens if an order/contract is breached (e.g., civil contempt, damages, attachment of property).

📑 Legal Authorities
- Explicitly list the bare acts or case laws retrieved and used for the response. Format: "Statute Name, Section [Number]". Minimum 1 authority.

📝 Note
"This information is provided for general legal education and research purposes only. It does not constitute legal advice."

══════════════════════════════════════════
ABSOLUTE GOVERNANCE RULES
1. NEVER output criminal terms like FIR, Arrest, Charge Sheet, Bailable, or Cognizable.
2. NEVER skip any headings.
"""

GENERAL_TEMPLATE = """You are the Structured Legal Response Enhancement & Safety Layer (SLRESL) for Legaily.
You produce lawyer-grade, general legal responses for queries involving constitutional law, administrative law, or regulatory frameworks.

Produce a structured legal memo covering ONLY these sections in order:
- Summary (2-3 sentences on what the query is about)
- Applicable Laws & Frameworks (specific statutes, articles, or regulations)
- Key Principles (the core legal rules that apply)
- Enforcement / Administrative Body (which authority governs this)

📝 Note
"This information is provided for general legal education and research purposes only. It does not constitute legal advice."

ABSOLUTE GOVERNANCE RULES
1. NEVER generate responses for non-legal queries (greetings, opinions, personal advice).
2. NEVER fabricate case laws or statutes not present in the retrieved context.
3. Keep the response concise and factual.
"""

INTENT_DETECTION_PROMPT = """You are a legal query intent classifier.
Analyze the user's intent and output exactly ONE WORD:
- CRIMINAL (if involves IPC, BNSS, BNS, BSA, murder, theft, police, bail, FIR)
- CIVIL (if involves CPC, contracts, injunctions, family law matters, property disputes, damages)
- GENERAL (for constitutional analysis, administrative queries, or unclear intents)

Output ONLY the category name.
"""

def detect_query_intent(query: str) -> str:
    try:
        q_lower = query.lower()
        criminal_keywords = [
            "ipc", "bns", "bnss", "bsa", "murder", "theft", "police", "bail", "fir",
            "arrest", "crime", "criminal", "homicide", "assault", "rape", "robbery",
            "kidnapping", "dowry", "cheat", "fraud"
        ]
        civil_keywords = [
            "cpc", "contract", "injunction", "family law", "property", "damages",
            "civil", "divorce", "specific relief", "tort", "decree", "breach"
        ]

        for kw in criminal_keywords:
            if kw in q_lower:
                return "CRIMINAL"
        # Fix #7: Also check CRIME_KEYWORD_MAP for extended criminal triggers
        # (catches queries like "bail for acid attack", "stalking case" etc.)
        for kw in CRIME_KEYWORD_MAP:
            if kw in q_lower:
                return "CRIMINAL"
        for kw in civil_keywords:
            if kw in q_lower:
                return "CIVIL"

        return "GENERAL"
    except Exception as e:
        logger.error(f"Intent detection failed, defaulting to CRIMINAL. Error: {e}")
        return "CRIMINAL"

def apply_guardrails(content: str, domain: str, docs: list = None) -> str:
    """Legal Validation & Guardrails Layer — PRD §7.6"""
    if domain == "CIVIL":
        criminal_terms = [
            r"\bFIR\b", r"\barrests?\b", r"\bcharge sheet\b",
            r"\bbailable\b", r"\bcognizable\b", r"\bpolice station\b"
        ]
        for term in criminal_terms:
            if re.search(term, content, re.IGNORECASE):
                logger.warning("Guardrail triggered! Forbidden term '%s' in CIVIL response.", term)
                content = re.sub(term, "[Term restricted by Legal Guardrails]", content, flags=re.IGNORECASE)

    elif domain == "CRIMINAL":
        # ── PRD §7.6: Section-Type Validation ─────────────────────────────
        # Rule: if ALL retrieved chunks are definition-type (no punishment signal),
        # then the LLM cannot lawfully invent a punishment. Strip it.
        if docs:
            types = [d.metadata.get('section_type', 'general') for d in docs]
            has_punishment_chunk = any(
                d.metadata.get('contains_punishment', False) for d in docs
            )
            all_definition = all(t in ('definition', 'general') for t in types)

            if all_definition and not has_punishment_chunk:
                # No punishment chunk was retrieved — strip any fabricated punishment
                punishment_match = re.search(
                    r'(⛓️ Punishment\s*)(.*?)(?=📊 Legal Classification|🔍 Illustrative)',
                    content, re.DOTALL | re.IGNORECASE
                )
                if punishment_match:
                    pun_text = punishment_match.group(2)
                    if re.search(r'imprisonment|death|rigorous|jail|fine', pun_text, re.IGNORECASE):
                        logger.warning(
                            "PRD Guardrail §7.6: Definition-only retrieval — stripping hallucinated punishment."
                        )
                        corrected = (
                            "\n- Punishment is prescribed in a linked section. "
                            "Refer to the punishment section of the applicable statute.\n\n"
                        )
                        content = (
                            content[:punishment_match.start(2)]
                            + corrected
                            + content[punishment_match.end(2):]
                        )

        # ── Liability Attribution punishment guard ─────────────────────────
        # IMPORTANT: only scan the Quick Summary block for the liability signal.
        # Scanning the full response causes false triggers when "Section 34 IPC"
        # appears innocuously in the Legal Authorities list (bug fix for IPC 203/403).
        summary_block = ""
        summary_match = re.search(
            r'(📌 Quick Summary\s*)(.*?)(?=\u2696\ufe0f Applicable Law|\u26d3\ufe0f Punishment|\u2705 Essential)',
            content, re.DOTALL | re.IGNORECASE
        )
        if summary_match:
            summary_block = summary_match.group(2)

        punishment_match = re.search(
            r'(⛓️ Punishment\s*)(.*?)(?=📊 Legal Classification)',
            content, re.DOTALL | re.IGNORECASE
        )
        if punishment_match:
            pun_text = punishment_match.group(2)
            if re.search(r'imprisonment|death|rigorous|jail', pun_text, re.IGNORECASE):
                if "no standalone punishment" not in pun_text.lower():
                    # Only flag if the SUMMARY mentions liability attribution terms
                    if re.search(
                        r'\b(common intention|unlawful assembly|liability attribution|'
                        r'vicariously liable|acts in furtherance)\b',
                        summary_block, re.IGNORECASE
                    ):
                        logger.warning("Guardrail: standalone punishment on Liability section.")
                        replaced = (
                            "\n- No standalone punishment; punishment depends on "
                            "the substantive offence committed.\n\n"
                        )
                        content = (
                            content[:punishment_match.start(2)]
                            + replaced
                            + content[punishment_match.end(2):]
                        )
    return content



# ===========================================================================
# Post-Processing: Section Recovery, Field Repair, Classification Enforcement
# ===========================================================================

# Repair decimal section numbers (e.g., Section 420.11 → Section 420)
_DECIMAL_SEC_RE = re.compile(r'\bSection\s+(\d+[A-Z]?)\.\d+', re.IGNORECASE)

# Classification terms that must not appear in the Quick Summary block
_SUMMARY_CLASS_RE = re.compile(
    r',?\s*\b(non-cognizable|cognizable|non-bailable|bailable|non-compoundable|compoundable)\b,?',
    re.IGNORECASE
)

def _repair_sections(text: str) -> str:
    """Repair decimal section numbers by stripping sub-clause suffix."""
    return _DECIMAL_SEC_RE.sub(lambda m: f"Section {m.group(1)}", text)


def _strip_summary_classification(text: str) -> str:
    """Remove cognizable/bailable terms from the Quick Summary block.
    These belong only in the Legal Classification section (Governance Rule 7).
    """
    def clean_summary(m):
        cleaned = _SUMMARY_CLASS_RE.sub('', m.group(0))
        # Collapse double spaces/commas left behind
        cleaned = re.sub(r'\s{2,}', ' ', cleaned)
        cleaned = re.sub(r',\s*\.', '.', cleaned)
        cleaned = re.sub(r'^\s*,\s*', '', cleaned, flags=re.MULTILINE)
        return cleaned

    return re.sub(
        r'(📌 Quick Summary.*?)(?=⚖️ Applicable Law)',
        clean_summary, text, flags=re.DOTALL | re.IGNORECASE
    )


_CLASS_RE = {
    "cognizable":   re.compile(r'(Cognizable:\s*)([^\n]+)', re.IGNORECASE),
    "bailable":     re.compile(r'(Bailable:\s*)([^\n]+)', re.IGNORECASE),
    "compoundable": re.compile(r'(Compoundable:\s*)([^\n]+)', re.IGNORECASE),
    "triable_by":   re.compile(r'(Triable By:\s*)([^\n]+)', re.IGNORECASE),
}
_PLACEHOLDER_RE = re.compile(r'\[value not provided\]|\[not provided\]|\[data missing\]|\[information unavailable\]', re.IGNORECASE)

def _enforce_and_repair(text: str, verified: dict) -> str:
    """
    When section IS in KB:   hard-enforce all 4 classification fields from verified data.
    When section NOT in KB:  hard-overwrite all 4 fields with 'Refer to Schedule 1, CrPC / BNSS'
                             so the LLM cannot silently output incorrect guessed values.

    Additionally: if the LLM skipped the 📊 Legal Classification block entirely,
    INSERT it before 🔍 Illustrative Example so the fields are never absent.
    """
    _UNVERIFIED = "Refer to Schedule 1, CrPC / BNSS"

    if not verified:
        # Replace any existing labels with UNVERIFIED marker
        text = _CLASS_RE["cognizable"].sub(  lambda m: f"{m.group(1)}{_UNVERIFIED}", text)
        text = _CLASS_RE["bailable"].sub(    lambda m: f"{m.group(1)}{_UNVERIFIED}", text)
        text = _CLASS_RE["compoundable"].sub(lambda m: f"{m.group(1)}{_UNVERIFIED}", text)
        text = _CLASS_RE["triable_by"].sub(  lambda m: f"{m.group(1)}{_UNVERIFIED}", text)
        text = _PLACEHOLDER_RE.sub(_UNVERIFIED, text)

        # ── Always inject the classification block for UNVERIFIED sections ──────────
        # The LLM frequently skips it for general-exception / defense-type sections
        # (e.g. IPC 82, 92, 93) because the exception constraint says "N/A — defense".
        # Instead of fighting the LLM, we always ensure it ends up in the output.
        _has_class = bool(
            re.search(r'Cognizable:', text, re.IGNORECASE) or
            re.search(r'Legal Classification', text, re.IGNORECASE)
        )
        if not _has_class:
            block = (
                "\n\n📊 Legal Classification\n"
                f"- Cognizable:   {_UNVERIFIED}\n"
                f"- Bailable:     {_UNVERIFIED}\n"
                f"- Compoundable: {_UNVERIFIED}\n"
                f"- Triable By:   {_UNVERIFIED}\n"
            )
            # Best anchor: insert before Illustrative Example; fallback: before Legal Authorities; last: append
            for anchor in (r'🔍 Illustrative Example', r'📑 Legal Authorities'):
                insert_re = re.compile(rf'(?={re.escape(anchor)})', re.IGNORECASE)
                if insert_re.search(text):
                    text = insert_re.sub(block + "\n", text, count=1)
                    break
            else:
                text += block
            logger.warning(
                "_enforce_and_repair [UNVERIFIED]: Classification block absent — injected."
            )
        return text

    # Replace existing labels with KB-verified values
    text = _CLASS_RE["cognizable"].sub(  lambda m: f"{m.group(1)}{verified['cognizable']}", text)
    text = _CLASS_RE["bailable"].sub(    lambda m: f"{m.group(1)}{verified['bailable']}", text)
    text = _CLASS_RE["compoundable"].sub(lambda m: f"{m.group(1)}{verified['compoundable']}", text)
    text = _CLASS_RE["triable_by"].sub(  lambda m: f"{m.group(1)}{verified['triable_by']}", text)
    text = _PLACEHOLDER_RE.sub("Refer to verified classification above", text)

    # ── INSERT guard: LLM skipped the classification block entirely ───────────
    # This happens when the model generates a valid-looking response but omits
    # the 📊 Legal Classification heading (seen on IPC 300, 392 in stress test).
    if "Legal Classification" not in text and "Cognizable:" not in text:
        block = (
            "\n\n📊 Legal Classification\n"
            f"- Cognizable:   {verified['cognizable']}\n"
            f"- Bailable:     {verified['bailable']}\n"
            f"- Compoundable: {verified['compoundable']}\n"
            f"- Triable By:   {verified['triable_by']}\n"
        )
        insert_re = re.compile(r'(?=🔍 Illustrative Example)', re.IGNORECASE)
        if insert_re.search(text):
            text = insert_re.sub(block + "\n", text, count=1)
        else:
            text += block
        logger.warning("_enforce_and_repair: Classification block was absent — injected.")

    return text


REQUIRED_HEADINGS = [
    "Quick Summary", "Applicable Law", "Legal Explanation",
    "Essential Ingredients", "Punishment", "Legal Classification",
    "Illustrative Example", "Legal Authorities"
]

def _validate_completeness(text: str) -> list:
    """Return list of headings that are missing from the response."""
    return [h for h in REQUIRED_HEADINGS if h.lower() not in text.lower()]


# ===========================================================================
# Confidence Score — Percentage with Explanation
# ===========================================================================
def _calculate_confidence(valid_sections: set, stat_coverage: set,
                           resolution_method: str) -> str:
    """
    3-signal confidence: statute coverage + section validation + DB resolution quality.
    Returns a professional label with explanation (not a raw percentage).
    """
    score_a = min(len(stat_coverage) / 4.0, 1.0) * 35
    score_b = min(len(valid_sections) / 6.0, 1.0) * 35
    score_c = {"verified_db": 30, "keyword_map": 20, "general_principles": 8}.get(resolution_method, 8)
    score = int(score_a + score_b + score_c)
    
    # LAQE confidence deduction for lack of sources
    if len(stat_coverage) == 0:
        score -= min(score, 20)  # Penalize up to 20 points

    if resolution_method == "verified_db" and score >= 60:
        label  = "High"
        reason = "Validated section mapping + verified classification + consistent legal reasoning"
    elif resolution_method == "keyword_map" and score >= 55:
        label  = "High"
        reason = "Verified classification from knowledge base + multi-statute context"
    elif score >= 25:
        label  = "Medium"
        reason = "Keyword-resolved classification + partial statute coverage"
    else:
        label  = "Low"
        reason = "General legal principles applied — weak contextual retrieval. Verify independently."

    return f"{label} ({reason})"


# ===========================================================================
# TLIRAS Main Engine
# ===========================================================================
def get_structured_response(query: str, mode: str = "detailed") -> dict:
    """
    TLIRAS: Retrieve → Validate → Repair → Enrich → Generate → Verify
    Complete 6-stage pipeline ensuring no placeholder, no hallucination.
    """
    try:
        import time
        start_t = time.time()

        # ── Guard: intercept greetings and off-topic non-legal queries ────────
        _GREETINGS = {
            "hi", "hii", "hiii", "hello", "hey", "yo", "howdy", "sup",
            "good morning", "good evening", "good afternoon", "good night",
            "how are you", "what's up", "whats up", "who are you",
            "thanks", "thank you", "ok", "okay", "bye", "goodbye",
            "test", "testing", "ping", "help"
        }
        q_stripped = query.strip().lower().rstrip("!?.")
        if q_stripped in _GREETINGS or len(q_stripped) < 5:
            logger.info("Non-legal query intercepted: '%s'", query[:40])
            return {
                "type": "info",
                "data": (
                    "Hello! I'm Legaily, your Indian legal research assistant.\n\n"
                    "I can help you with:\n"
                    "- \u2696\ufe0f IPC / BNS criminal law (e.g., \"What is punishment for IPC 302?\")\n"
                    "- \ud83d\udcc4 Civil law questions (e.g., \"How to file for injunction under CPC?\")\n"
                    "- \ud83d\udcd6 Constitutional and regulatory law\n\n"
                    "Please ask a specific legal question to get a detailed response."
                )
            }

        # ── Cache check (instant return for repeated queries) ──────────────
        cached = _cache_get(query, mode)
        if cached is not None:
            logger.info("Cache HIT for query: %.60s", query)
            return cached

        vs = _get_vectorstore()
        co = _get_cohere()
        logger.info(f"Loaded instances: {time.time() - start_t:.2f}s")

        # ── Stage 1: Intent Detection & Classification Resolution ──────────
        t1 = time.time()
        domain = detect_query_intent(query)
        logger.info(f"TLIRAS Intent Detected: {domain}")
        
        section_number, code_hint = _extract_section_query(query)
        sec_key, verified_class, resolution = _resolve_classification(
            query, section_number, code_hint
        )
        db_hit = verified_class is not None
        # Fix #9: Log KB misses so we know which sections to add next
        if not db_hit:
            logger.warning("KB MISS — Section not in verified DB: query='%.80s'", query)
            try:
                _miss_path = os.path.join(os.path.dirname(__file__), "../../kb_misses.log")
                with open(_miss_path, "a") as _f:
                    _f.write(f"{query.strip()}\n")
            except Exception:
                pass
        logger.info(f"Stage 1 Intent: {time.time() - t1:.2f}s")

        # ── Stage 2: Multi-Statute Retrieval (Hybrid: FAISS + BM25 + RRF) ──
        t2 = time.time()
        bm25_data = _get_bm25()
        bm25_model = bm25_data["bm25"]
        bm25_docs = bm25_data["docs"]

        direct_docs = _direct_section_lookup(section_number, preferred_law=code_hint) if section_number else []

        # ── FAST PATH: direct section match found → pin it, then enrich with FAISS ──
        # Fix #3: Previously skipped FAISS entirely, losing related context (exceptions,
        # punishment schedules, neighbouring sections). Now we always enrich.
        DIRECT_DOCS_THRESHOLD = 1
        if len(direct_docs) >= DIRECT_DOCS_THRESHOLD:
            t_faiss = time.time()
            faiss_results = vs.similarity_search(query, k=8)
            logger.info(f"FAISS enrichment (fast-path): {time.time() - t_faiss:.2f}s")
            seen = set(hash(d.page_content) for d in direct_docs)
            for d in faiss_results:
                if hash(d.page_content) not in seen:
                    direct_docs.append(d)
                    seen.add(hash(d.page_content))
            docs = direct_docs[:10]  # direct match pinned at top
            logger.info(f"Stage 2 Fast-path+FAISS enrichment ({len(docs)} docs): {time.time() - t2:.2f}s")
        else:
            # Fix #5: HyDE — rewrite query as hypothetical statute text for better
            # InLegalBERT embedding alignment with the statute corpus.
            try:
                hyde_resp = co.chat(
                    model="command-r7b-12-2024",
                    messages=[
                        {"role": "system", "content":
                         "You are a legal indexing assistant. Given a legal question, write "
                         "ONE sentence that mimics how an Indian Penal Code section describes "
                         "this scenario. Start with 'Whoever' or 'Any person who'. Be concise."},
                        {"role": "user", "content": query}
                    ],
                    max_tokens=80
                )
                expanded_query = hyde_resp.message.content[0].text.strip()
                logger.info("HyDE expansion: %.80s", expanded_query)
            except Exception as _hyde_err:
                expanded_query = query
                logger.warning("HyDE failed, using raw query: %s", _hyde_err)
            t_faiss = time.time()
            faiss_results = vs.similarity_search(expanded_query, k=10)
            logger.info(f"FAISS search: {time.time() - t_faiss:.2f}s")

            # BM25 keyword retrieval — top 10
            tokenized_query = tokenize_for_bm25(query)
            bm25_scores = bm25_model.get_scores(tokenized_query)
            top_bm25_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:10]
            bm25_results = [bm25_docs[i] for i in top_bm25_indices if bm25_scores[i] > 0]

            # Candidate Fusion (Reciprocal Rank Fusion - RRF)
            all_docs_dict = {}
            faiss_ranks = {}
            bm25_ranks = {}

            for idx, doc in enumerate(faiss_results):
                h = hash(doc.page_content)
                all_docs_dict[h] = doc
                if h not in faiss_ranks:
                    faiss_ranks[h] = idx + 1

            for idx, doc in enumerate(bm25_results):
                h = hash(doc.page_content)
                all_docs_dict[h] = doc
                if h not in bm25_ranks:
                    bm25_ranks[h] = idx + 1

            k_rrf = 60
            rrf_scores = {}
            for h in all_docs_dict:
                score = 0.0
                if h in faiss_ranks:
                    score += 1.0 / (k_rrf + faiss_ranks[h])
                if h in bm25_ranks:
                    score += 1.0 / (k_rrf + bm25_ranks[h])
                rrf_scores[h] = score

            sorted_rrf = sorted(rrf_scores.keys(), key=lambda h: rrf_scores[h], reverse=True)[:10]
            unique_docs = list(direct_docs)
            seen_contents = set([hash(d.page_content) for d in direct_docs])

            for h in sorted_rrf:
                if h not in seen_contents:
                    unique_docs.append(all_docs_dict[h])
                    seen_contents.add(h)

            doc_texts = [d.page_content for d in unique_docs]
            t_rerank = time.time()
            rerank = co.rerank(model="rerank-v3.5", query=query, documents=doc_texts, top_n=8)
            logger.info(f"Cohere rerank: {time.time() - t_rerank:.2f}s")
            docs = [unique_docs[r.index] for r in rerank.results]
            logger.info(f"Stage 2 Retrieval (full hybrid): {time.time() - t2:.2f}s")

        # ── Stage 3: Structured Context Assembly (PRD §7.5) ──────────────────
        # Group retrieved chunks by section_type so the LLM sees separated
        # Definition / Punishment / Exception blocks instead of a flat dump.
        # This directly prevents IPC 321 (definition) + IPC 323 (punishment) fusion.
        t3 = time.time()
        MAX_DOC_CHARS = 1200
        MAX_CTX_CHARS = 6000
        valid_sections, stat_coverage = set(), set()

        # Bucket docs by their legal taxonomy type
        buckets: dict[str, list] = {
            'punishment':  [],
            'definition':  [],
            'exception':   [],
            'procedural':  [],
            'evidentiary': [],
            'general':     [],
        }
        total_ctx_chars = 0
        for d in docs:
            sec  = str(d.metadata.get('section_number', '?')).upper()
            law  = d.metadata.get('law_name', 'Unknown')
            stype = d.metadata.get('section_type', 'general')
            valid_sections.add(sec)
            stat_coverage.add(law.split()[0] if law else 'Unknown')
            snippet = d.page_content[:MAX_DOC_CHARS]
            entry   = f"[{law} | Section {sec}]\n{snippet}"
            if total_ctx_chars + len(entry) <= MAX_CTX_CHARS:
                buckets.get(stype, buckets['general']).append(entry)
                total_ctx_chars += len(entry)

        # Build structured context string with labeled sections (PRD §7.5)
        ctx_parts = []
        _BUCKET_LABELS = {
            'punishment':  '--- PUNISHMENT PROVISIONS ---',
            'definition':  '--- DEFINITION / OFFENCE DESCRIPTION ---',
            'exception':   '--- EXCEPTIONS / DEFENSES ---',
            'procedural':  '--- PROCEDURAL PROVISIONS ---',
            'evidentiary': '--- EVIDENTIARY PROVISIONS ---',
            'general':     '--- GENERAL PROVISIONS ---',
        }
        for btype, label in _BUCKET_LABELS.items():
            entries = buckets[btype]
            if entries:
                ctx_parts.append(label)
                ctx_parts.extend(entries)
        context_str = "\n\n".join(ctx_parts)

        # ── Stage 4: Calculate confidence + build Verified Classification Block ────
        confidence_label = _calculate_confidence(valid_sections, stat_coverage, resolution)
        if verified_class:
            ipc_ref = f"Section {sec_key} IPC"
            bns_raw = verified_class.get("bns", "")
            # Only surface BNS mapping if it is a confirmed section (not "Omitted" or blank)
            if bns_raw and not bns_raw.startswith("Omitted"):
                bns_note = f"BNS Equivalent: {bns_raw} (use this mapping; do not invent alternatives)"
            else:
                bns_note = f"BNS Status: {bns_raw if bns_raw else 'Corresponding provisions apply under the Bharatiya Nyaya Sanhita.'}"
            # Inject authoritative statutory description hint if available
            content_hint = SECTION_CONTENT_HINTS.get(sec_key, "")
            content_hint_line = f"\nStatutory Description Hint: {content_hint}" if content_hint else ""
            classification_block = (
                f"\n\n╔══ VERIFIED CLASSIFICATION DATA (REPRODUCE EXACTLY — DO NOT ALTER) ══╗\n"
                f"Primary Law:   {ipc_ref}\n"
                f"{bns_note}{content_hint_line}\n"
                f"Cognizable:    {verified_class['cognizable']}\n"
                f"Bailable:      {verified_class['bailable']}\n"
                f"Compoundable:  {verified_class['compoundable']}\n"
                f"Triable By:    {verified_class['triable_by']}\n"
                f"Confidence:    {confidence_label}\n"
                f"Source:        Schedule 1, CrPC / BNSS — Verified DB\n"
                f"╚══════════════════════════════════════════════════════════╝"
            )
        else:
            classification_block = (
                "\n\n[UNVERIFIED SECTION — CLASSIFICATION RULES]\n"
                "This section is NOT in the verified database.\n"
                "For the Legal Classification section, you MUST write exactly:\n"
                "  Cognizable:   Refer to Schedule 1, CrPC / BNSS\n"
                "  Bailable:     Refer to Schedule 1, CrPC / BNSS\n"
                "  Compoundable: Refer to Schedule 1, CrPC / BNSS\n"
                "  Triable By:   Refer to Schedule 1, CrPC / BNSS\n"
                "DO NOT guess, infer, or fill in any of these values from general knowledge.\n"
                "[END UNVERIFIED SECTION]"
            )

        logger.info(f"Stage 3/4 Context & Confidence: {time.time() - t3:.2f}s")

        # ── Stage 4b: Section-Type Analysis + Mismatch Detection ────────────
        # Determine the dominant section_type from the primary retrieved chunk.
        # Detects TWO classes of mismatch:
        #   A) Section-number mismatch: user asked §X but top doc is §Y (different number)
        #   B) Cross-statute mismatch: user asked IPC §85 but top doc is BNS §85 (same number,
        #      different statute — completely different legal provisions that share a number)
        primary_stype = docs[0].metadata.get('section_type', 'general') if docs else 'general'
        has_punishment_in_context = bool(buckets['punishment'])

        _mismatch_constraint = ""
        if section_number and docs:
            top_retrieved_sec = str(docs[0].metadata.get('section_number', '')).upper()
            top_retrieved_law = docs[0].metadata.get('law_name', '').upper()
            queried_sec  = str(section_number).upper()
            queried_code = (code_hint or 'IPC').upper()   # default to IPC

            # ── Case A: Different section number ──────────────────────────────
            if top_retrieved_sec and top_retrieved_sec != queried_sec:
                logger.warning(
                    "Section mismatch: queried=%s but top retrieved=%s. Injecting constraint.",
                    queried_sec, top_retrieved_sec
                )
                _mismatch_constraint = (
                    f"\n\n[SECTION MISMATCH WARNING — MANDATORY]\n"
                    f"The user asked about Section {queried_sec} IPC/BNS.\n"
                    f"The retrieved context contains Section {top_retrieved_sec}, which is a DIFFERENT section.\n"
                    f"RULES:\n"
                    f"- ONLY respond about Section {queried_sec}.\n"
                    f"- DO NOT use any facts, punishment, or details from Section {top_retrieved_sec}.\n"
                    f"- If your knowledge of Section {queried_sec} is insufficient, state: "
                    f"'Detailed corpus entry for Section {queried_sec} was not retrieved. "
                    f"Please verify this section directly in the IPC/BNS text.'\n"
                    f"[END WARNING]"
                )

            # ── Case B: Cross-statute collision (same number, different law) ──
            # E.g. user queries 'ipc 85' but FAISS returns BNS §85 (cruelty by husband)
            # instead of IPC §85 (act of intoxicated person). These are different provisions.
            elif queried_code == 'IPC' and top_retrieved_sec == queried_sec:
                cross_statute_noise = any(
                    noise in top_retrieved_law
                    for noise in ('BNS', 'BNSS', 'BSA')
                )
                if cross_statute_noise:
                    logger.warning(
                        "Cross-statute collision: user asked IPC §%s but top doc is from %s. "
                        "Injecting cross-statute constraint.",
                        queried_sec, top_retrieved_law
                    )
                    _mismatch_constraint = (
                        f"\n\n[CROSS-STATUTE WARNING — MANDATORY]\n"
                        f"The user asked about Section {queried_sec} IPC (Indian Penal Code, 1860).\n"
                        f"The retrieved context is from {top_retrieved_law}, which is a DIFFERENT statute.\n"
                        f"Section {queried_sec} IPC and Section {queried_sec} BNS/BNSS/BSA are "
                        f"ENTIRELY DIFFERENT legal provisions that happen to share the same number.\n"
                        f"RULES:\n"
                        f"- ONLY respond about Section {queried_sec} IPC (Indian Penal Code, 1860).\n"
                        f"- DO NOT use facts, punishment, or classification from the {top_retrieved_law} context.\n"
                        f"- Rely on your knowledge of Section {queried_sec} IPC.\n"
                        f"- If insufficient, state: 'Direct corpus entry for Section {queried_sec} IPC "
                        f"was not retrieved. Please verify in the IPC text.'\n"
                        f"[END WARNING]"
                    )

        # Fix: definition → actively retrieve the related punishment section
        # If we retrieved a definition chunk but no punishment chunk, search for
        # the punishment section in the next 3 section numbers (e.g. IPC 321 → 323).
        if primary_stype == 'definition' and not has_punishment_in_context and section_number:
            try:
                base_num = int(''.join(filter(str.isdigit, section_number)))
                for offset in [1, 2, 3, 4, 5]:
                    candidate = str(base_num + offset)
                    for _doc_id, _doc in vs.docstore._dict.items():
                        if (str(_doc.metadata.get('section_number', '')).upper() == candidate
                                and _doc.metadata.get('contains_punishment', False)):
                            entry = (
                                f"[{_doc.metadata.get('law_name','IPC')} | Section {candidate}]\n"
                                f"{_doc.page_content[:MAX_DOC_CHARS]}"
                            )
                            buckets['punishment'].append(entry)
                            ctx_parts.insert(0, '--- PUNISHMENT PROVISIONS ---')
                            ctx_parts.insert(1, entry)
                            context_str = "\n\n".join(ctx_parts)
                            has_punishment_in_context = True
                            logger.info(
                                "Definition+Punishment fix: injected Section %s as punishment for Section %s",
                                candidate, section_number
                            )
                            break
                    if has_punishment_in_context:
                        break
            except (ValueError, AttributeError):
                pass

        # ── Stage 4c: Build Section-Type-Aware Generation Constraints ───────
        # Injected as a hard instruction block in user_msg so the LLM cannot
        # violate the legal taxonomy even if the prompt template doesn't explicitly cover it.
        _type_constraints = ""

        # KB OVERRIDE: if the section is verified in the KB as a real criminal offence
        # (cognizable != "N/A"), override the splitter's section_type label.
        # This prevents exception-constraint from firing on offence sections whose
        # statutory text happens to contain exception sub-clauses (e.g. IPC 300, 392).
        _kb_is_real_offence = (
            verified_class is not None
            and not verified_class.get("cognizable", "N/A").startswith("N/A")
            and not verified_class.get("cognizable", "").startswith("Depends")
        )
        if _kb_is_real_offence and primary_stype == 'exception':
            logger.info(
                "KB override: section %s is a criminal offence (KB cognizable=%s) — "
                "ignoring splitter exception label on retrieved chunk.",
                section_number, verified_class.get("cognizable")
            )
            primary_stype = 'punishment'  # treat as offence for constraint purposes

        if primary_stype == 'exception':
            _type_constraints = (
                "\n\n[SECTION-TYPE CONSTRAINT — MANDATORY]\n"
                "This section is a GENERAL EXCEPTION or DEFENSE provision.\n"
                "RULES:\n"
                "- DO NOT include any Punishment field. State: 'None — this is a legal defense.'\n"
                "- DO NOT include Cognizable / Bailable / Compoundable / Triable By classification.\n"
                "  State: 'N/A — General Exceptions are defenses, not offences.'\n"
                "- Focus the response on: (a) what the exception covers, "
                "(b) conditions for its applicability, (c) its limitations.\n"
                "[END CONSTRAINT]"
            )
        elif primary_stype == 'definition' and has_punishment_in_context:
            _type_constraints = (
                "\n\n[SECTION-TYPE CONSTRAINT — MANDATORY]\n"
                "The PRIMARY retrieved section is a DEFINITION section. "
                "It defines the offence but does NOT itself prescribe punishment.\n"
                "RULES:\n"
                "- For the Punishment field, USE ONLY the punishment section "
                "injected under '--- PUNISHMENT PROVISIONS ---' in the legal context.\n"
                "- DO NOT invent or infer a punishment not present in the retrieved context.\n"
                "- The Classification fields (Cognizable, Bailable, etc.) apply to the "
                "OFFENCE defined by this section, not to the definition itself.\n"
                "[END CONSTRAINT]"
            )
        elif primary_stype == 'definition' and not has_punishment_in_context:
            _type_constraints = (
                "\n\n[SECTION-TYPE CONSTRAINT — MANDATORY]\n"
                "This section is a DEFINITION section. No punishment section was retrieved.\n"
                "RULES:\n"
                "- For the Punishment field, state: "
                "'Punishment is prescribed in a linked section of the same statute. "
                "Refer to the relevant punishment provision.'\n"
                "- DO NOT fabricate any imprisonment term or fine amount.\n"
                "[END CONSTRAINT]"
            )
        elif primary_stype == 'procedural':
            _type_constraints = (
                "\n\n[SECTION-TYPE CONSTRAINT — MANDATORY]\n"
                "This section is a PROCEDURAL provision (court/police powers, bail, cognizance).\n"
                "RULES:\n"
                "- DO NOT apply IPC/BNS punishment classifications to this section.\n"
                "- Classification (Cognizable/Bailable) refers to the offence it governs, "
                "not the procedural section itself.\n"
                "[END CONSTRAINT]"
            )

        # ── Stage 5: Generate ──────────────────────────────────────────────
        t5 = time.time()
        model = os.getenv("COHERE_CHAT_MODEL", "command-r-08-2024")
        user_msg = (
            f"User Query: {query}"
            f"{classification_block if domain == 'CRIMINAL' else ''}"
            f"{_mismatch_constraint}"
            f"{_type_constraints}"
            f"\n\nLegal Context:\n{context_str}"
        )

        if domain == "CRIMINAL":
            system_prompt = CRIMINAL_TEMPLATE
        elif domain == "CIVIL":
            system_prompt = CIVIL_TEMPLATE
        else:
            system_prompt = GENERAL_TEMPLATE

        response = co.chat(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_msg},
            ],
            max_tokens=2500,   # 7-section response fits in ~1500-2000 tokens
            temperature=0.1,   # PRD §8: deterministic legal output (0.0–0.2)
        )

        content = ""
        if response.message and response.message.content:
            content = response.message.content[0].text
        logger.info(f"Stage 5 Chat Gen: {time.time() - t5:.2f}s")

        # ── Stage 6: Post-Process Verification ────────────────────────────
        t6 = time.time()
        # 6a. Repair decimal sections (420.11 → 420)
        content = _repair_sections(content)
        # 6b. Strip classification terms from Quick Summary (Governance Rule 7)
        content = _strip_summary_classification(content)
        # 6c. Enforce classification + replace placeholders (Criminal only)
        if domain == "CRIMINAL":
            content = _enforce_and_repair(content, verified_class)
        # 6d. Strip markdown ### heading prefixes (render as clean plain text)
        content = re.sub(r'^#{1,4}\s+', '', content, flags=re.MULTILINE)
        # 6e. Apply guardrails based on domain
        content = apply_guardrails(content, domain, docs=docs)
        # 6e. Completeness check (internal log only)
        if domain == "CRIMINAL":
            missing = _validate_completeness(content)
            if missing:
                logger.warning("TLIRAS: Missing sections: %s", missing)

        logger.info(f"Stage 6 Post-Process: {time.time() - t6:.2f}s")
        logger.info(f"Total structured_response time: {time.time() - start_t:.2f}s")
        result = {"type": "detailed", "data": content}
        _cache_set(query, mode, result)  # Store in cache for future identical queries
        return result

    except Exception as e:
        logger.exception("TLIRAS error: %s", e)
        return {"error": str(e)}


if __name__ == "__main__":
    for q in ["IPC 420", "punishment for cheating", "IPC 302", "theft"]:
        r = get_structured_response(q)
        print(f"\n{'='*60}\n{q}\n{'='*60}")
        print(r.get("data", r)[:900])
