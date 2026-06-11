import re
import json

def parse_js():
    with open("scratch/ncert_script_0.js", "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Clean comments from lines
    cleaned_lines = []
    for line in lines:
        cleaned_line = re.sub(r'//.*', '', line).strip()
        if cleaned_line:
            cleaned_lines.append(cleaned_line)
    
    content = "\n".join(cleaned_lines)

    # Step 1: Parse the subjects listed per class in the change() function.
    class_subject_blocks = re.findall(r'else if\s*\(document\.test\.tclass\.value\s*==\s*(\d+)\)(.*?)(?=else if\s*\(document\.test\.tclass\.value|$)', content, re.DOTALL)
    
    class_subjects = {}
    for class_val, block in class_subject_blocks:
        class_id = int(class_val)
        subjects = []
        # Find all options assignment
        opt_matches = re.findall(r'document\.test\.tsubject\.options\[\d+\]\.text\s*=\s*"([^"]+)"', block)
        for opt in opt_matches:
            opt = opt.strip()
            opt_clean = opt.replace(".", "")
            if opt_clean and "Select Subject" not in opt_clean:
                subjects.append(opt_clean)
        class_subjects[class_id] = subjects

    print(f"Extracted subjects for {len(class_subjects)} classes.")

    # Step 2: Parse the book titles and codes inside change1()
    book_blocks = re.findall(r'else if\s*\(\(document\.test\.tclass\.value\s*==\s*(\d+)\)\s*&&\s*\(document\.test\.tsubject\.options\[sind\]\.text\s*==\s*"([^"]+)"\)\)(.*?)(?=else if|$)', content, re.DOTALL)

    extracted_books = []
    for class_val, subject_name, block in book_blocks:
        class_id = int(class_val)
        
        # Match option assignments by index:
        # document.test.tbook.options[idx].text = "..."
        # document.test.tbook.options[idx].value = "textbook.php?..."
        
        texts = {}
        values = {}
        
        text_matches = re.finditer(r'document\.test\.tbook\.options\[(\d+)\]\.text\s*=\s*"([^"]+)"', block)
        for m in text_matches:
            texts[int(m.group(1))] = m.group(2).strip()
            
        value_matches = re.finditer(r'document\.test\.tbook\.options\[(\d+)\]\.value\s*=\s*"textbook\.php\?([^"]+)"', block)
        for m in value_matches:
            values[int(m.group(1))] = m.group(2).strip()
            
        # Combine by index
        books_in_block = []
        indices = sorted(list(set(list(texts.keys()) + list(values.keys()))))
        for idx in indices:
            text = texts.get(idx)
            val = values.get(idx)
            if text and val and "Select Book" not in text:
                if "=" in val:
                    code, chap_range = val.split("=")
                    books_in_block.append({
                        "title": text,
                        "code": code,
                        "range": chap_range
                    })
        
        if books_in_block:
            extracted_books.append({
                "class_id": class_id,
                "subject": subject_name.strip(),
                "books": books_in_block
            })

    print(f"Extracted book configurations for {len(extracted_books)} class-subject pairs.")
    
    with open("scratch/ncert_parsed_meta.json", "w") as out:
        json.dump({
            "class_subjects": class_subjects,
            "class_subject_books": extracted_books
        }, out, indent=2)
    print("Saved metadata to scratch/ncert_parsed_meta.json")

if __name__ == "__main__":
    parse_js()
