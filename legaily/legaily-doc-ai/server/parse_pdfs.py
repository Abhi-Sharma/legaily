import pdfplumber
import os

DATA_DIR = "/home/bhavesh/Mini Project/legaily/legaily/BharatLAW/data/"

FILES = {
    "250882_english_01042024_0.pdf": "bsa_law.txt",
    "250883_english_01042024.pdf": "bns_law.txt",
    "250884_2_english_01042024.pdf": "bnss_law.txt"
}

def parse_pdf(pdf_path, txt_path):
    print(f"Parsing {pdf_path} ...")
    full_text = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                full_text.append(text)
            if i % 10 == 0:
                print(f"  Processed {i} pages...")
    
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(full_text))
    print(f"Saved to {txt_path}")

if __name__ == "__main__":
    for pdf_name, txt_name in FILES.items():
        pdf_path = os.path.join(DATA_DIR, pdf_name)
        txt_path = os.path.join(DATA_DIR, txt_name)
        if os.path.exists(pdf_path):
            parse_pdf(pdf_path, txt_path)
        else:
            print(f"File not found: {pdf_path}")
