import os
import sys
import io
import re
import argparse
import urllib.request
import subprocess
import json
import logging
from sqlalchemy.orm import Session
from pypdf import PdfReader

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("sync_content")

# Setup project path so we can import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.models.book import Book, BookChapter, ChapterSection, ChapterAsset
from app.models.chapter import Chapter
from app.models.subject import Subject
from app.models.class_model import Class
from app.ai.openai_provider import OpenAIProvider

# List of NCERT textbooks for Classes 1-5 (English, Math, EVS, Hindi)
SUPPORTED_BOOKS = [
    # Grade 1
    {"class": "Grade 1", "subject": "Mathematics", "code": "aejm1", "chapters": 13, "title": "Joyful Mathematics"},
    {"class": "Grade 1", "subject": "Hindi", "code": "ahsr1", "chapters": 5, "title": "Sarangi"},
    {"class": "Grade 1", "subject": "English", "code": "aemr1", "chapters": 10, "title": "Mridang"},
    # Grade 2
    {"class": "Grade 2", "subject": "Mathematics", "code": "bejm1", "chapters": 15, "title": "Joyful Mathematics"},
    {"class": "Grade 2", "subject": "Hindi", "code": "bhsr1", "chapters": 5, "title": "Sarangi"},
    {"class": "Grade 2", "subject": "English", "code": "bemr1", "chapters": 10, "title": "Mridang"},
    # Grade 3
    {"class": "Grade 3", "subject": "Mathematics", "code": "cemm1", "chapters": 14, "title": "Maths Mela"},
    {"class": "Grade 3", "subject": "Hindi", "code": "chve1", "chapters": 5, "title": "Veena"},
    {"class": "Grade 3", "subject": "English", "code": "cesa1", "chapters": 7, "title": "Santoor"},
    {"class": "Grade 3", "subject": "Environmental Studies", "code": "ceap1", "chapters": 10, "title": "Our Wondrous World"},
    # Grade 4
    {"class": "Grade 4", "subject": "Mathematics", "code": "demm1", "chapters": 14, "title": "Maths Mela"},
    {"class": "Grade 4", "subject": "Hindi", "code": "dhve1", "chapters": 5, "title": "Veena"},
    {"class": "Grade 4", "subject": "English", "code": "desa1", "chapters": 7, "title": "Santoor"},
    {"class": "Grade 4", "subject": "Environmental Studies", "code": "deap1", "chapters": 10, "title": "Our Wondrous World"},
    # Grade 5
    {"class": "Grade 5", "subject": "Mathematics", "code": "eemh1", "chapters": 14, "title": "Maths Mela"},
    {"class": "Grade 5", "subject": "Hindi", "code": "ehhn1", "chapters": 5, "title": "Veena"},
    {"class": "Grade 5", "subject": "English", "code": "eeen1", "chapters": 7, "title": "Santoor"},
    {"class": "Grade 5", "subject": "Environmental Studies", "code": "ehap1", "chapters": 10, "title": "Our Wondrous World"},
]

# Cache and Static directory setup
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache", "pdf")
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

def download_pdf(url: str, dest_path: str) -> bool:
    """Downloads a file from url to dest_path using urllib and curl fallback."""
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    if os.path.exists(dest_path):
        logger.info(f"Using cached file: {dest_path}")
        return True

    logger.info(f"Downloading {url} to {dest_path}...")
    try:
        req = urllib.request.Request(
            url, 
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            with open(dest_path, "wb") as f:
                f.write(response.read())
        return True
    except Exception as e:
        logger.warning(f"urllib download failed: {e}. Trying curl fallback...")
        try:
            cmd = [
                "curl", "-L", "-s",
                "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "-o", dest_path,
                url
            ]
            subprocess.run(cmd, check=True)
            if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1000:
                return True
            else:
                logger.error(f"Downloaded file is empty or too small.")
                if os.path.exists(dest_path):
                    os.remove(dest_path)
                return False
        except Exception as curl_err:
            logger.error(f"Curl download failed: {curl_err}")
            if os.path.exists(dest_path):
                os.remove(dest_path)
            return False

def clean_extracted_text(text: str) -> str:
    """Cleans NCERT-specific headers, footers, and duplicates from extracted raw text."""
    lines = text.split("\n")
    cleaned_lines = []
    
    # Matches typical NCERT page footnotes/headers (e.g. Chapter 1.indd 2, Date, Reprint etc.)
    indd_pattern = re.compile(r"Chapter\s+\d+\.indd.*", re.IGNORECASE)
    reprint_pattern = re.compile(r"Reprint\s+\d{4}-\d{2}", re.IGNORECASE)
    page_num_pattern = re.compile(r"^\s*\d+\s*$") # Only a number on the line
    
    for line in lines:
        line_stripped = line.strip()
        # Skip empty lines
        if not line_stripped:
            cleaned_lines.append("")
            continue
            
        # Skip header/footer patterns
        if indd_pattern.search(line_stripped) or reprint_pattern.search(line_stripped):
            continue
        if page_num_pattern.match(line_stripped):
            continue
        if "1/17/2025" in line_stripped or "24-05-2023" in line_stripped:
            continue
            
        # Deduplicate duplicated titles (e.g. "Think and AnswerThink and Answer")
        n = len(line_stripped)
        if n > 4 and n % 2 == 0:
            half = n // 2
            if line_stripped[:half] == line_stripped[half:]:
                line_stripped = line_stripped[:half]
                
        cleaned_lines.append(line_stripped)
        
    return "\n".join(cleaned_lines).strip()

def extract_images(pdf_path: str, book_id: int, chapter_num: int) -> list:
    """Extracts images from PDF pages using pypdf and saves them to static folder."""
    reader = PdfReader(pdf_path)
    image_infos = []
    
    # Destination directory: backend/static/books/{book_id}/chapter_{chapter_num}/images/
    img_dir = os.path.join(STATIC_DIR, "books", str(book_id), f"chapter_{chapter_num}", "images")
    os.makedirs(img_dir, exist_ok=True)
    
    for page_idx, page in enumerate(reader.pages):
        for img_idx, image_file_object in enumerate(page.images):
            filename = f"page_{page_idx+1}_img_{img_idx+1}.png"
            filepath = os.path.join(img_dir, filename)
            
            # Serve path relative to static mount (e.g., /static/books/1/chapter_1/images/...)
            relative_url = f"/static/books/{book_id}/chapter_{chapter_num}/images/{filename}"
            
            try:
                with open(filepath, "wb") as f:
                    f.write(image_file_object.data)
                image_infos.append({
                    "page": page_idx + 1,
                    "url": relative_url,
                    "filename": filename
                })
            except Exception as e:
                logger.error(f"Failed to extract image {filename} from {pdf_path}: {e}")
                
    logger.info(f"Extracted {len(image_infos)} images to {img_dir}")
    return image_infos

def generate_sections_heuristically(cleaned_text: str, page_images: list, book_id: int, chapter_num: int) -> list:
    """Splits chapter text into sections deterministically using common NCERT subheadings."""
    # List of common NCERT primary school subheadings
    section_patterns = [
        r"Let us Sing", r"Let us Play", r"Let us Do", r"Think and Answer", 
        r"Project Work", r"Exercises", r"Examples", r"Talk Time", 
        r"Practice Time", r"Activity", r"Summary"
    ]
    
    # Combine patterns to match
    heading_regex = re.compile(r"^(" + "|".join(section_patterns) + r")(?:\s*—\s*.*)?$", re.IGNORECASE)
    
    lines = cleaned_text.split("\n")
    sections = []
    current_section = {
        "heading": "Introduction",
        "lines": [],
        "order": 1
    }
    
    order_counter = 1
    for line in lines:
        line_stripped = line.strip()
        if heading_regex.match(line_stripped):
            # Save previous section if it has content
            if current_section["lines"] or current_section["heading"] != "Introduction":
                sections.append(current_section)
                
            order_counter += 1
            current_section = {
                "heading": line_stripped,
                "lines": [],
                "order": order_counter
            }
        else:
            current_section["lines"].append(line)
            
    # Append final section
    if current_section["lines"] or current_section["heading"] != "Introduction":
        sections.append(current_section)
        
    # Format sections as HTML and Plain Text
    formatted_sections = []
    for sec in sections:
        plain_text = "\n".join(sec["lines"]).strip()
        if not plain_text:
            continue
            
        # Basic plain-text-to-HTML parser
        paragraphs = []
        current_para = []
        for line in sec["lines"]:
            l_strip = line.strip()
            if not l_strip:
                if current_para:
                    paragraphs.append("<p>" + " ".join(current_para) + "</p>")
                    current_para = []
            elif l_strip.startswith("●") or l_strip.startswith("*") or l_strip.startswith("-"):
                if current_para:
                    paragraphs.append("<p>" + " ".join(current_para) + "</p>")
                    current_para = []
                # bullet list item
                item_text = l_strip.lstrip("●*-").strip()
                paragraphs.append(f"<ul><li>{item_text}</li></ul>")
            elif re.match(r"^[A-Z]\.\s+.*", l_strip) or re.match(r"^\d+\.\s+.*", l_strip):
                if current_para:
                    paragraphs.append("<p>" + " ".join(current_para) + "</p>")
                    current_para = []
                # list item
                paragraphs.append(f"<ol><li>{l_strip}</li></ol>")
            else:
                current_para.append(l_strip)
                
        if current_para:
            paragraphs.append("<p>" + " ".join(current_para) + "</p>")
            
        # Insert any images belonging to this section (using basic heuristic mapping)
        # For simplicity, we just distribute images evenly or append them
        html_content = "\n".join(paragraphs)
        
        # Simple inline images display at the end of the section HTML
        section_imgs = []
        # If section order corresponds to page numbers roughly
        for img in page_images:
            # Simple heuristic: map images on page P to sections that are nearby
            # (or just show page images)
            pass
            
        formatted_sections.append({
            "heading": sec["heading"],
            "order": sec["order"],
            "html_content": html_content,
            "plain_text": plain_text
        })
        
    return formatted_sections

def generate_sections_with_ai(openai_prov: OpenAIProvider, cleaned_text: str, page_images: list, book_id: int, chapter_num: int) -> dict:
    """Uses GPT-4o-mini to clean up, section-split, and generate beautiful HTML content with inline images."""
    image_list_str = "\n".join([f"- Page {img['page']}: {img['filename']} (url: {img['url']})" for img in page_images])
    
    prompt = f"""
We have parsed an NCERT primary school textbook chapter PDF.
Below is the cleaned, raw text of the chapter. We have also extracted the following images from the PDF pages:
{image_list_str}

Please structure this raw textbook chapter text into a high-quality educational reading workspace.
Your output MUST be a valid JSON object matching the JSON schema below. 

JSON SCHEMA:
{{
  "summary": "A 2-3 sentence overview of the chapter, highlighting the main learning concepts.",
  "learning_objectives": [
    "Learning objective 1",
    "Learning objective 2"
  ],
  "sections": [
    {{
      "heading": "Section Heading (e.g. Let us Sing, Let us Do, Activity, Exercises, Think and Answer)",
      "order": 1,
      "html_content": "Beautiful, semantic HTML markup for this section. Include paragraphs, bullet points (ul/li), questions (ol/li), and bold text. You MUST insert the page images inline at the most appropriate positions using <img src='IMAGE_URL' alt='Caption' class='chapter-image' />. Wrap activities and warnings in styled divs like <div class='activity-card'>...</div>.",
      "plain_text": "Plain text content of this section."
    }}
  ]
}}

CRITICAL RULES:
1. Preserve all educational content, exercises, questions, and activities.
2. The HTML content should look clean, professional, and readable (closer to a Medium article or Notion page).
3. Do NOT use inline styles. Use clean HTML tags (p, ul, li, h3, h4, ol, strong, em, img, div class='activity-card', div class='example-card').
4. Make sure images are embedded using their exact URLs as provided above. Place them at contextually correct positions.
5. All text in the JSON must be properly escaped.

RAW CHAPTER TEXT:
{cleaned_text}
"""
    system_instruction = "You are an expert curriculum engineer. You output only valid JSON matching the requested schema."
    
    logger.info("Structuring chapter content with OpenAI...")
    try:
        response_text = openai_prov.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            json_mode=True
        )
        data = json.loads(response_text)
        return data
    except Exception as e:
        logger.error(f"OpenAI structuring failed: {e}")
        return None

def sync_chapter(db: Session, book: Book, chapter_num: int, code: str, title: str, summary_content: str) -> None:
    """Downloads, parses, cleans, structures, and saves a chapter to the Content Engine database."""
    # Format chapter URL
    chap_idx_str = f"{chapter_num:02d}"
    url = f"https://ncert.nic.in/textbook/pdf/{code}{chap_idx_str}.pdf"
    
    pdf_path = os.path.join(CACHE_DIR, code, f"chapter_{chapter_num}.pdf")
    
    # Download
    success = download_pdf(url, pdf_path)
    if not success:
        logger.error(f"Skipping Chapter {chapter_num} because download failed.")
        return

    # Parse raw text
    try:
        reader = PdfReader(pdf_path)
        raw_text_parts = []
        for idx, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                raw_text_parts.append(page_text)
        raw_text = "\n\n".join(raw_text_parts)
    except Exception as e:
        logger.error(f"Failed to read PDF file {pdf_path}: {e}")
        return
        
    if not raw_text.strip():
        logger.warning(f"No text extracted from PDF {pdf_path}. Skipping.")
        return

    # Clean text
    cleaned_text = clean_extracted_text(raw_text)
    
    # Extract images
    images = extract_images(pdf_path, book.id, chapter_num)
    
    # Structure sections (AI-assisted or Heuristic)
    openai_prov = OpenAIProvider()
    structured_data = None
    if openai_prov.is_configured():
        structured_data = generate_sections_with_ai(openai_prov, cleaned_text, images, book.id, chapter_num)
        
    if not structured_data:
        logger.info("Falling back to heuristic section extraction...")
        heuristic_sections = generate_sections_heuristically(cleaned_text, images, book.id, chapter_num)
        # Basic objectives
        objectives = [f"Understand the core concepts of {title}"]
        # Simple summary
        summary = summary_content or cleaned_text[:200] + "..."
        structured_data = {
            "summary": summary,
            "learning_objectives": objectives,
            "sections": heuristic_sections
        }

    # Generate slug
    slug = f"class-{book.class_.lower().replace(' ', '-')}-{book.subject.lower()}-ch-{chapter_num}-{re.sub(r'[^a-z0-9]+', '-', title.lower())}".strip("-")

    # Save BookChapter
    # Delete existing to prevent duplication
    existing_chapter = db.query(BookChapter).filter(BookChapter.book_id == book.id, BookChapter.chapter_number == chapter_num).first()
    if existing_chapter:
        logger.info(f"Removing existing chapter entry for overwrite: Ch {chapter_num}")
        db.delete(existing_chapter)
        db.commit()

    # Create new
    book_chap = BookChapter(
        book_id=book.id,
        chapter_number=chapter_num,
        title=title,
        slug=slug,
        summary=structured_data.get("summary", "")
    )
    db.add(book_chap)
    db.commit()
    db.refresh(book_chap)

    # Save ChapterSections and ChapterAssets
    for sec_data in structured_data.get("sections", []):
        sec = ChapterSection(
            chapter_id=book_chap.id,
            heading=sec_data.get("heading", "Section"),
            order=sec_data.get("order", 1),
            html_content=sec_data.get("html_content", ""),
            plain_text=sec_data.get("plain_text", "")
        )
        db.add(sec)
        db.commit()
        db.refresh(sec)

        # Parse html_content to locate images and add asset references
        # Find any <img src="IMAGE_URL" ... /> tags in HTML
        img_srcs = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', sec.html_content)
        for src in img_srcs:
            # Find caption
            caption_match = re.search(r'alt=["\']([^"\']+)["\']', sec.html_content)
            caption = caption_match.group(1) if caption_match else None
            
            asset = ChapterAsset(
                section_id=sec.id,
                asset_type="image",
                image=src,
                caption=caption
            )
            db.add(asset)
            
    db.commit()
    logger.info(f"Saved BookChapter ID {book_chap.id}: {title} with {len(structured_data.get('sections', []))} sections.")

    # Link school tenant's Chapter records to this global BookChapter
    # Find classes matching book's class name (e.g. "Grade 1")
    classes = db.query(Class).filter(Class.name == book.class_).all()
    for cls in classes:
        # Find subjects matching book's subject (e.g. "Mathematics")
        subjects = db.query(Subject).filter(Subject.name == book.subject, Subject.class_id == cls.id).all()
        for subj in subjects:
            # Find the chapter matching chapter number
            tenant_chap = db.query(Chapter).filter(
                Chapter.subject_id == subj.id,
                Chapter.number == str(chapter_num)
            ).first()
            if tenant_chap:
                tenant_chap.book_chapter_id = book_chap.id
                db.add(tenant_chap)
                logger.info(f"Linked tenant chapter ID {tenant_chap.id} (Subject: {subj.name}, Class: {cls.name}) to BookChapter ID {book_chap.id}")
                
    db.commit()

def main():
    parser = argparse.ArgumentParser(description="Momentum Content Engine Importer")
    parser.add_argument("--class-name", type=str, help="Grade/Class to sync (e.g. 'Grade 1')")
    parser.add_argument("--subject", type=str, help="Subject to sync (e.g. 'Mathematics')")
    parser.add_argument("--chapter", type=int, help="Specific chapter number to sync (requires class-name and subject)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        # Load the seed syllabus to grab chapter titles/summaries
        from app.db.seed_ncert import NCERT_SYLLABUS
    except ImportError:
        logger.error("seed_ncert.py not found or NCERT_SYLLABUS not defined.")
        sys.exit(1)

    # Filter books to import
    books_to_sync = SUPPORTED_BOOKS
    if args.class_name:
        books_to_sync = [b for b in books_to_sync if b["class"].lower() == args.class_name.lower()]
    if args.subject:
        books_to_sync = [b for b in books_to_sync if b["subject"].lower() == args.subject.lower()]

    if not books_to_sync:
        logger.warning("No books match the filters.")
        return

    logger.info(f"Starting Content Engine Importer for {len(books_to_sync)} books...")

    for book_info in books_to_sync:
        # Verify or create the Book record
        book = db.query(Book).filter(Book.class_ == book_info["class"], Book.subject == book_info["subject"]).first()
        if not book:
            book = Book(
                class_=book_info["class"],
                subject=book_info["subject"],
                title=book_info["title"],
                language="Hindi" if book_info["subject"].lower() == "hindi" else "English",
                edition="2026-27",
                source="NCERT"
            )
            db.add(book)
            db.commit()
            db.refresh(book)
            logger.info(f"Created Book entry: {book.title} (Class: {book.class_}, Subject: {book.subject})")
        else:
            logger.info(f"Using existing Book entry ID {book.id}: {book.title}")

        # Find syllabus details for this book in seed_ncert structure
        syllabus_class = next((c for c in NCERT_SYLLABUS if c["class_name"].lower() == book.class_.lower()), None)
        syllabus_subject = None
        if syllabus_class:
            syllabus_subject = next((s for s in syllabus_class["subjects"] if s["name"].lower() == book.subject.lower()), None)

        chapters_range = range(1, book_info["chapters"] + 1)
        if args.chapter:
            chapters_range = [args.chapter]

        for chap_num in chapters_range:
            # Find the title and temporary summary from seed_ncert
            chap_title = f"Chapter {chap_num}"
            chap_summary = ""
            if syllabus_subject:
                syllabus_chap = next((ch for ch in syllabus_subject["chapters"] if str(ch["number"]) == str(chap_num)), None)
                if syllabus_chap:
                    chap_title = syllabus_chap["title"]
                    chap_summary = syllabus_chap.get("content", "")

            logger.info(f"--- Syncing {book.class_} {book.subject} - Chapter {chap_num}: {chap_title} ---")
            sync_chapter(db, book, chap_num, book_info["code"], chap_title, chap_summary)

    db.close()
    logger.info("Content Engine Importer finished successfully!")

if __name__ == "__main__":
    main()
