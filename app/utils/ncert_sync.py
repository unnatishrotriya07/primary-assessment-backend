import urllib.request
import io
import logging
from typing import Optional
from pypdf import PdfReader
from app.db.ncert_mapping import get_ncert_book_code

logger = logging.getLogger(__name__)

def fetch_ncert_chapter_text(class_grade: str, subject_name: str, chapter_number: str) -> Optional[str]:
    book_code = get_ncert_book_code(class_grade, subject_name)
    if not book_code:
        logger.warning(f"No NCERT book code found for Class: {class_grade}, Subject: {subject_name}")
        return None
        
    try:
        # Convert to int to strip leading zeroes if any and format to two digits (e.g. 1 -> '01')
        chap_idx = int(chapter_number)
        chap_str = f"{chap_idx:02d}"
    except ValueError:
        # Fallback to string formatting
        chap_str = chapter_number.zfill(2)
        
    # Construct URL
    pdf_url = f"https://ncert.nic.in/textbook/pdf/{book_code}{chap_str}.pdf"
    logger.info(f"Syncing NCERT content from URL: {pdf_url}")
    
    try:
        req = urllib.request.Request(
            pdf_url, 
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
        )
        # 15 seconds timeout to prevent blocking indefinitely
        with urllib.request.urlopen(req, timeout=15) as response:
            pdf_data = response.read()
            
        # Parse PDF and extract text page by page
        pdf_file = io.BytesIO(pdf_data)
        reader = PdfReader(pdf_file)
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
                
        full_text = "\n".join(text_parts).strip()
        if not full_text:
            logger.warning(f"Extracted empty text from PDF: {pdf_url}")
            return None
            
        logger.info(f"Successfully extracted {len(full_text)} characters from {pdf_url}")
        return full_text
    except Exception as e:
        logger.error(f"Failed to fetch or parse NCERT PDF from {pdf_url}: {e}")
        return None
