import os
import sys

# Setup project path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.s3 import upload_to_s3, s3_file_exists, download_from_s3, PAUSE_S3

def test_local_s3():
    print(f"PAUSE_S3 = {PAUSE_S3}")
    assert PAUSE_S3 is True, "PAUSE_S3 should be True"
    
    test_filename = "test_folder/test_file.txt"
    test_content = b"Hello Antigravity!"
    
    # 1. Test uploading
    print("Testing upload_to_s3...")
    url = upload_to_s3(test_content, test_filename, "text/plain")
    print(f"Uploaded URL: {url}")
    assert url == "/static/test_folder/test_file.txt", "Returned URL should match local static mount format"
    
    # Check if file exists on disk
    local_path = os.path.join("static", test_filename)
    assert os.path.exists(local_path), f"File should be created on disk at {local_path}"
    with open(local_path, "rb") as f:
        assert f.read() == test_content, "Content of created file does not match"
    print("Upload verification passed!")
    
    # 2. Test file existence check
    print("Testing s3_file_exists...")
    exists = s3_file_exists(test_filename)
    assert exists is True, "File should exist"
    
    exists_false = s3_file_exists("nonexistent_file.txt")
    assert exists_false is False, "File should not exist"
    print("Existence check verification passed!")
    
    # 3. Test downloading
    print("Testing download_from_s3...")
    dest_path = "static/test_folder/downloaded_copy.txt"
    if os.path.exists(dest_path):
        os.remove(dest_path)
        
    downloaded = download_from_s3(test_filename, dest_path)
    assert downloaded is True, "Download should succeed"
    assert os.path.exists(dest_path), "Downloaded file should exist at dest_path"
    with open(dest_path, "rb") as f:
        assert f.read() == test_content, "Content of downloaded file should match"
    print("Download verification passed!")
    
    # Clean up test files
    os.remove(local_path)
    os.remove(dest_path)
    print("All checks passed successfully!")

if __name__ == "__main__":
    test_local_s3()
