import os
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# Paths
IPC_FILE_PATH = "../../BharatLAW/data/ipc_law.txt"
INDEX_PATH = "ipc_index_sample"

def ingest():
    print(f"Loading data from {IPC_FILE_PATH}...")
    with open(IPC_FILE_PATH, 'r') as f:
        content = "".join([next(f) for _ in range(2000)]) # Take first 2000 lines

    with open("ipc_sample.txt", 'w') as f:
        f.write(content)

    loader = TextLoader("ipc_sample.txt")
    documents = loader.load()

    print("Splitting text into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs = text_splitter.split_documents(documents)
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
