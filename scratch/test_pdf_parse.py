import urllib.request
import io
import subprocess
import os
from pypdf import PdfReader

url = "https://ncert.nic.in/textbook/pdf/aejm101.pdf"

def download_pdf(url: str) -> bytes:
    temp_file = "temp_download.pdf"
    cmd = [
        "curl", "-L", "-s",
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "-o", temp_file,
        url
    ]
    subprocess.run(cmd, check=True)
    with open(temp_file, "rb") as f:
        data = f.read()
    if os.path.exists(temp_file):
        os.remove(temp_file)
    return data

pdf_data = download_pdf(url)
pdf_file = io.BytesIO(pdf_data)
reader = PdfReader(pdf_file)

for idx, page in enumerate(reader.pages):
    print(f"=== PAGE {idx+1} ===")
    print(page.extract_text())
    print("\n")
