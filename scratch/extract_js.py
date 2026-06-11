import urllib.request
import re

url = "https://ncert.nic.in/textbook.php"
try:
    html = urllib.request.urlopen(url).read().decode('utf-8', errors='ignore')
    
    # Find all <script> blocks
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
    
    # Find scripts that contain "tclass.value" or "change()" or "tsubject"
    matching_scripts = []
    for s in scripts:
        if "tclass.value" in s or "tsubject" in s or "change1" in s:
            matching_scripts.append(s)
            
    print(f"Found {len(matching_scripts)} scripts matching.")
    for idx, s in enumerate(matching_scripts):
        filename = f"scratch/ncert_script_{idx}.js"
        with open(filename, "w") as f:
            f.write(s)
        print(f"Saved to {filename} ({len(s)} bytes)")
except Exception as e:
    print("Error:", e)
