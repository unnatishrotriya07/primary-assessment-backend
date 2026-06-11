import urllib.request
import json

def test_sync():
    base_url = "http://localhost:5001"
    
    # 1. Login
    login_url = f"{base_url}/api/auth/login"
    login_data = json.dumps({"email": "admin@example.com", "password": "admin123"}).encode("utf-8")
    req = urllib.request.Request(
        login_url,
        data=login_data,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req) as res:
            res_data = json.loads(res.read().decode("utf-8"))
            token = res_data.get("token")
            print("Login successful. Token acquired:", token[:10] + "...")
    except Exception as e:
        print("Login failed:", e)
        return

    # 2. Call sync-ncert for chapter 211
    sync_url = f"{base_url}/api/chapters/211/sync-ncert"
    req = urllib.request.Request(
        sync_url,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    )
    try:
        with urllib.request.urlopen(req) as res:
            res_data = json.loads(res.read().decode("utf-8"))
            print("Sync response keys:", list(res_data.keys()))
            text_content = res_data.get("textContent")
            if text_content:
                print("Sync successful!")
                print(f"Extracted textbook text length: {len(text_content)} characters")
                print("First 200 characters:")
                print(text_content[:200])
            else:
                print("Sync failed: textContent is empty or null")
    except Exception as e:
        print("Sync request failed:", e)

if __name__ == "__main__":
    test_sync()
