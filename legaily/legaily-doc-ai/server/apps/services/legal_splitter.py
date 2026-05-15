import re
from langchain_text_splitters import TextSplitter
from langchain_core.documents import Document
from typing import List, Any

# Gazette header patterns to strip before splitting
_GAZETTE_HEADERS = re.compile(
    r'(THE GAZETTE OF INDIA EXTRAORDINARY.*?\n'
    r'|Sec\.?\s*\d+\]\s*THE GAZETTE OF INDIA.*?\n'
    r'|\[Part\s*II.*?\n'
    r'|_{5,}\n'
    r'|\.{5,}\n'
    r'|_{5,})',
    re.IGNORECASE
)

# ── Section Type Classifier ─────────────────────────────────────────────────
# Keyword signals used to classify each chunk's legal role.
_PUNISHMENT_SIGNALS = re.compile(
    r'\b(shall be punished|punishable with|imprisonment|rigorous imprisonment|'
    r'fine|death|life imprisonment|both|whipping)\b',
    re.IGNORECASE
)
_EXCEPTION_SIGNALS = re.compile(
    r'\b(nothing in this (section|chapter|act)|exception|excuse|justified|'
    r'right of private defence|general exception|not an offence)\b',
    re.IGNORECASE
)
_PROCEDURAL_SIGNALS = re.compile(
    r'\b(court shall|magistrate shall|police officer|cognizance|FIR|warrant|'
    r'bail|trial|charge sheet|summons|inquiry|investigation)\b',
    re.IGNORECASE
)
_EVIDENTIARY_SIGNALS = re.compile(
    r'\b(evidence|presumption|admissible|proof|burden of proof|witness|'
    r'electronic record|document|shall be deemed)\b',
    re.IGNORECASE
)
_DEFINITION_SIGNALS = re.compile(
    r'\b(means|denotes|includes|whoever|any person who|is said to|defined as|'
    r'for the purposes of this)\b',
    re.IGNORECASE
)


# Strong exception signals — must be a clear defense clause, NOT just the word 'exception'
_STRONG_EXCEPTION_SIGNALS = re.compile(
    r'\b(nothing in this (section|chapter|act)|right of private defence|'
    r'general exception|not an offence|shall not constitute an offence|'
    r'excused from|justified by law|exempt from)\b',
    re.IGNORECASE
)

# High-priority offence section ranges that must NEVER be classified as exception
# even if the text happens to contain exception-like language in sub-clauses
_PUNISHMENT_VERB = re.compile(r'\bshall be punished\b', re.IGNORECASE)


def _classify_section(text: str) -> tuple[str, bool]:
    """Returns (section_type, contains_punishment) for a chunk.

    Priority order:
        1. punishment  — 'shall be punished' present → always punishment, never exception
        2. exception   — strong exception signal (not just the word 'exception')
        3. procedural  — court/police procedure language
        4. evidentiary — evidence rules
        5. definition  — defines a term or describes an offence
        6. general     — fallback
    """
    has_punishment = bool(_PUNISHMENT_SIGNALS.search(text))
    has_punishment_verb = bool(_PUNISHMENT_VERB.search(text))

    # Rule 1: 'shall be punished' is definitive — this is a punishment/offence chunk.
    # Exception language in sub-clauses (e.g. IPC 307's 'Exception') does NOT override.
    if has_punishment_verb:
        return 'punishment', True

    # Rule 2: Exception — require STRONG signals, not just the word 'exception'
    if _STRONG_EXCEPTION_SIGNALS.search(text):
        return 'exception', has_punishment

    if _PROCEDURAL_SIGNALS.search(text):
        return 'procedural', has_punishment
    if _EVIDENTIARY_SIGNALS.search(text):
        return 'evidentiary', has_punishment
    if _DEFINITION_SIGNALS.search(text):
        return 'definition', has_punishment
    return 'general', has_punishment


class LegalSectionSplitter(TextSplitter):
    """
    Custom splitter for Indian Legal Statutes (IPC, BNS, BNSS, BSA).
    Splits text based on statute-specific section markers and stores
    the extracted section number in metadata for direct-lookup queries.
    Implements PRD §7.1: one-section-one-chunk with Legal Taxonomy metadata.
    """
    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        # IPC markers: [s 1], [s 302], etc.
        self.ipc_pattern = re.compile(r'\n(?=\[s \d+[\w.]*\])')
        # BNS/BNSS/BSA markers: line starting with a number followed by a period
        # Handles: "4. Something", "4.(1) Something", "118A. Something"
        self.bns_pattern = re.compile(r'\n(?=\d+[A-Z]?\.\s)')

    # ------------------------------------------------------------------
    # Cleaning helpers
    # ------------------------------------------------------------------
    def _clean_bns_text(self, text: str) -> str:
        """Apply OCR fixes for the new Sanhita PDFs."""
        text = _GAZETTE_HEADERS.sub('', text)
        text = re.sub(r'(\d+\.)([A-Za-z])', r'\1 \2', text)
        text = re.sub(r'(:)([A-Za-z])', r'\1 \2', text)
        text = re.sub(r'(\))\s*([A-Za-z])', r'\1 \2', text)
        text = re.sub(r'[ \t]{2,}', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text

    def _clean_ipc_text(self, text: str) -> str:
        """Light cleanup for IPC (already well-formatted)."""
        text = _GAZETTE_HEADERS.sub('', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text

    # ------------------------------------------------------------------
    # Core splitting
    # ------------------------------------------------------------------
    def split_text(self, text: str) -> List[str]:
        if '[s 1]' in text[:5000]:
            chunks = self.ipc_pattern.split(text)
        else:
            chunks = self.bns_pattern.split(text)
        return [c.strip() for c in chunks if c.strip() and len(c.strip()) > 30]

    def split_documents(self, documents: List[Document]) -> List[Document]:
        resulting_docs = []
        for doc in documents:
            source_file = doc.metadata.get('source_file', '').lower()

            # Clean text based on statute type
            is_new_sanhita = any(k in source_file for k in ['bns', 'bnss', 'bsa'])
            text = self._clean_bns_text(doc.page_content) if is_new_sanhita \
                   else self._clean_ipc_text(doc.page_content)

            chunks = self.split_text(text)
            for i, chunk in enumerate(chunks):
                metadata = doc.metadata.copy()
                metadata['chunk_index'] = i

                # --- Extract section number for direct lookup ---
                ipc_match = re.match(r'^\[s (\d+[A-Z]?)\]', chunk)
                bns_match = re.match(r'^(\d+[A-Z]?)\.\s', chunk)
                if ipc_match:
                    metadata['section_number'] = ipc_match.group(1)
                elif bns_match:
                    metadata['section_number'] = bns_match.group(1)

                # --- PRD §7.1 Legal Taxonomy Metadata ---
                section_type, contains_punishment = _classify_section(chunk)
                metadata['section_type'] = section_type
                metadata['contains_punishment'] = contains_punishment

                resulting_docs.append(Document(page_content=chunk, metadata=metadata))

        return resulting_docs
