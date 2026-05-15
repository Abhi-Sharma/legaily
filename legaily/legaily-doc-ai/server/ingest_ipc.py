import os
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# Paths
DATA_DIR = "../../BharatLAW/data/"
INDEX_PATH = "ipc_index"

def ingest():
    print(f"Scanning directory {DATA_DIR} for legal data...")
    all_docs = []
    
    # Process all .txt files in the data directory
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.txt')]
    for filename in files:
        file_path = os.path.join(DATA_DIR, filename)
        print(f"Loading data from {file_path}...")
        loader = TextLoader(file_path)
        documents = loader.load()
        
        # Tag each document with its source filename
        for doc in documents:
            doc.metadata["source_file"] = filename
        
        all_docs.extend(documents)

    if not all_docs:
        print("No .txt files found to ingest.")
        return

    print(f"Splitting {len(all_docs)} documents into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=200)
    docs = text_splitter.split_documents(all_docs)
    print(f"Split into {len(docs)} chunks.")

    print("Initializing embeddings (law-ai/InLegalBERT)...")
    embeddings = HuggingFaceEmbeddings(model_name="law-ai/InLegalBERT")

    print("Creating FAISS index...")
    vectorstore = FAISS.from_documents(docs, embeddings)

    print(f"Saving index to {INDEX_PATH}...")
    vectorstore.save_local(INDEX_PATH)
    print("Ingestion complete.")

if __name__ == "__main__":
    ingest()
