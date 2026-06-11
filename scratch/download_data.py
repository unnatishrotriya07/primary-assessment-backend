import urllib.request
import json

url = "https://raw.githubusercontent.com/aayushdutt/ncert-downloader/main/data.json"
try:
    print("Downloading data.json from GitHub...")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    response = urllib.request.urlopen(req)
    data = json.loads(response.read().decode('utf-8'))
    
    # Save the file locally
    with open("scratch/ncert_downloader_data.json", "w") as f:
        json.dump(data, f, indent=2)
    print("Downloaded successfully.")
    
    # Print basic info
    print("Keys in JSON:", list(data.keys()) if isinstance(data, dict) else "Data is a list")
    if isinstance(data, dict):
        # Print a sample key
        sample_key = list(data.keys())[0]
        print(f"Sample key: {sample_key}")
        print(f"Sample data for {sample_key}:", json.dumps(data[sample_key])[:500])
    elif isinstance(data, list):
        print("Length of list:", len(data))
        print("Sample element:", json.dumps(data[0])[:500])
except Exception as e:
    print("Error:", e)
