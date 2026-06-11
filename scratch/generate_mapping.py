import json

def generate_mapping():
    with open("scratch/ncert_parsed_meta.json", "r") as f:
        data = json.load(f)

    # We want to build a dictionary mapping: (class_id, subject) -> book_code
    # Since there can be multiple books per class-subject (e.g., English, Hindi, Urdu versions),
    # we prefer the English version as the default standard, or the first available option.
    mapping = {}
    for entry in data["class_subject_books"]:
        class_id = entry["class_id"]
        subject = entry["subject"]
        books = entry["books"]
        
        # Pick the best default book code
        # If there is an English book (usually first or without suffix like "Hindi" or "Urdu"), pick it.
        selected_book = books[0] # Fallback
        for b in books:
            title = b["title"].lower()
            # If the title explicitly contains (English) or has standard English name, prefer it
            if "(english)" in title or "english" in title:
                selected_book = b
                break
            # Avoid Hindi/Urdu/Sanskrit versions if an English name is present
            if not ("hindi" in title or "urdu" in title or "sanskrit" in title or "ganit" in title or "vigyan" in title or "mela (hindi)" in title or "mela (urdu)" in title):
                selected_book = b
                break
                
        mapping[f"{class_id}_{subject}"] = selected_book["code"]

    # Write to a clean python file
    out_content = f"""# Auto-generated NCERT Book Mapping

NCERT_BOOK_MAPPING = {json.dumps(mapping, indent=4)}

def get_ncert_book_code(class_grade: str, subject_name: str) -> str:
    # Remove "Grade " prefix if present in class_grade
    grade_num = class_grade.lower().replace("grade", "").strip()
    key = f"{{grade_num}}_{{subject_name}}"
    return NCERT_BOOK_MAPPING.get(key)
"""

    with open("app/db/ncert_mapping.py", "w") as out:
        out.write(out_content)
    print("Generated app/db/ncert_mapping.py successfully.")

if __name__ == "__main__":
    generate_mapping()
