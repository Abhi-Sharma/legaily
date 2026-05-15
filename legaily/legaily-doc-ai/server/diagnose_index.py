import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

INDEX_PATH = "legal_statutes_index"

def diagnose(query):
    embeddings = HuggingFaceEmbeddings(model_name="law-ai/InLegalBERT")
    vectorstore = FAISS.load_local(INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
    
    print(f"\nQuery: {query}")
    docs = vectorstore.similarity_search(query, k=15)
    for i, doc in enumerate(docs):
        print(f"{i+1}. Law: {doc.metadata.get('law_name')} | Section: {doc.metadata.get('section_number')}")
        print(f"   Content: {doc.page_content[:150]}...")
        print("-" * 10)

if __name__ == "__main__":
    diagnose("cheating")
