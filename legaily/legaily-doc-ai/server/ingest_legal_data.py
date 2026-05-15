import os
import re
import pickle
from langchain_community.document_loaders import TextLoader
from apps.services.legal_splitter import LegalSectionSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from rank_bm25 import BM25Okapi

# Paths
DATA_DIR = "../../BharatLAW/data/"
INDEX_PATH = "legal_statutes_index"

# Gazette of India page-break noise found across all statute PDFs
_GAZETTE_NOISE = re.compile(
    r'(jftLVªh.*?\n'                              # Hindi registration line
    r'|xxxGIDE\w+xxx\n'                           # GID marker
    r'|vlk\/kkj\.k\n'                             # "Extraordinary" in Hindi
    r'|izkf\/[^\n]+\n'                            # Hindi authority line
    r'|lañ \d+\][^\n]+\n'                         # Devanagari page header
    r'|No\.\s*\d+\]\s+NEW DELHI[^\n]+\n'         # "No. 53] NEW DELHI..." line
    r'|bl Hkkx[^\n]+\n'                           # Hindi compilation note
    r'|Separate paging[^\n]+\n'                   # English compilation note
    r'|MINISTRY OF LAW[^\n]+\n'                   # Ministry line
    r'|New Delhi,\s*the\s*\d+[^\n]+\n'           # "New Delhi, the..." line
    r'|\(Legislative Department\)\n'              # Dept line
    r'|THE GAZETTE OF INDIA EXTRAORDINARY[^\n]+\n'
    r'|(?:Sec\.\s*\d+\])[^\n]+\n'               # "Sec. 1] THE GAZETTE..."
    r'|\[Part II[^\n]*\n'                          # "[Part II—"
    r'|_{5,}(?:\r?\n|$)'                          # Long underscores
    r'|\-{5,}(?:\r?\n|$))',                       # Long dashes
    re.MULTILINE
)

def clean_gazette_text(text: str) -> str:
    """Strip gazette header noise from statute text."""
    text = _GAZETTE_NOISE.sub('\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def get_law_name(filename):
    filename = filename.lower()
    if "ipc" in filename:
        return "Indian Penal Code (IPC)"
    if "bnss" in filename:
        return "Bharatiya Nagarik Suraksha Sanhita (BNSS)"
    if "bns" in filename:
        return "Bharatiya Nyaya Sanhita (BNS)"
    if "bsa" in filename:
        return "Bharatiya Sakshya Adhiniyam (BSA)"
    return "Other Legal Statute"

def tokenize_for_bm25(text: str) -> list[str]:
    """Simple alphanumeric tokenizer preserving citations."""
    # Convert to lowercase and split by non-alphanumeric (preserves numbers/sections)
    return [t for t in re.split(r'\W+', text.lower()) if t]

def ingest():
    print(f"Scanning directory {DATA_DIR} for legal data...")
    all_docs = []

    if not os.path.exists(DATA_DIR):
        print(f"Error: Data directory {DATA_DIR} not found.")
        return

    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.txt')]
    print(f"Found files: {files}")

    for filename in files:
        file_path = os.path.join(DATA_DIR, filename)
        law_name = get_law_name(filename)
        print(f"Loading {law_name} from {file_path}...")
        try:
            loader = TextLoader(file_path, encoding='utf-8')
            documents = loader.load()
            for doc in documents:
                doc.page_content = clean_gazette_text(doc.page_content)
                doc.metadata["source_file"] = filename
                doc.metadata["law_name"] = law_name
            all_docs.extend(documents)
        except Exception as e:
            print(f"Error loading {file_path}: {e}")

    if not all_docs:
        print("No legal documents found to ingest.")
        return

    print(f"Splitting {len(all_docs)} documents into granular sections...")
    text_splitter = LegalSectionSplitter()
    docs = text_splitter.split_documents(all_docs)
    print(f"Split into {len(docs)} sections.")

    # Report per-statute counts
    from collections import Counter
    counts = Counter(d.metadata.get('law_name', 'Unknown') for d in docs)
    for law, count in sorted(counts.items()):
        print(f"  {law}: {count} sections")

    print("Building BM25 index...")
    tokenized_corpus = [tokenize_for_bm25(d.page_content) for d in docs]
    bm25 = BM25Okapi(tokenized_corpus)

    print("Initializing embeddings (law-ai/InLegalBERT)...")
    embeddings = HuggingFaceEmbeddings(model_name="law-ai/InLegalBERT")

    print("Creating unified FAISS index (this may take a few minutes)...")
    vectorstore = FAISS.from_documents(docs, embeddings)

    # Ensure index path exists
    os.makedirs(INDEX_PATH, exist_ok=True)

    print(f"Saving combined FAISS index to {INDEX_PATH}...")
    vectorstore.save_local(INDEX_PATH)

    print(f"Saving BM25 index to {INDEX_PATH}/bm25_index.pkl...")
    with open(os.path.join(INDEX_PATH, "bm25_index.pkl"), "wb") as f:
        pickle.dump({"bm25": bm25, "docs": docs}, f)

    print("Ingestion complete successfully.")

if __name__ == "__main__":
    ingest()
