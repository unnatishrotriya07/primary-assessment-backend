import os
import boto3
from botocore.exceptions import ClientError
from app.core.config import settings

# Global toggle to pause S3 uploads and route them to local storage
PAUSE_S3 = os.getenv("PAUSE_S3", "true").lower() == "true"

def get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION
    )

def upload_to_s3(file_bytes: bytes, filename: str, content_type: str = "image/png") -> str:
    if PAUSE_S3:
        clean_filename = filename.lstrip("/")
        local_path = os.path.join("static", clean_filename)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        try:
            with open(local_path, "wb") as f:
                f.write(file_bytes)
            print(f"Local Storage (S3 Paused): Saved '{clean_filename}' locally.", flush=True)
            return f"/static/{clean_filename}"
        except Exception as e:
            print(f"Local Storage (S3 Paused): Failed to save '{clean_filename}' locally. Error: {e}", flush=True)
            return None

    s3 = get_s3_client()
    bucket = settings.AWS_STORAGE_BUCKET_NAME
    
    # Verify/create bucket
    try:
        s3.head_bucket(Bucket=bucket)
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        # 404 means bucket does not exist, 403 means forbidden (it exists but we can't access metadata, or we lack head_bucket permission)
        if error_code == "404":
            print(f"S3: Bucket '{bucket}' not found. Attempting to create it...", flush=True)
            try:
                if settings.AWS_REGION == "us-east-1":
                    s3.create_bucket(Bucket=bucket)
                else:
                    s3.create_bucket(
                        Bucket=bucket,
                        CreateBucketConfiguration={"LocationConstraint": settings.AWS_REGION}
                    )
                print(f"S3: Bucket '{bucket}' created successfully.", flush=True)
            except Exception as ce:
                print(f"S3: Failed to create bucket '{bucket}'. Error: {ce}", flush=True)
        else:
            print(f"S3: Head bucket returned error code {error_code}: {e}", flush=True)
            
    # Upload the file
    try:
        # We try to upload with public-read ACL.
        # If public-read ACL is blocked by bucket settings, we fall back to uploading without ACL.
        try:
            s3.put_object(
                Bucket=bucket,
                Key=filename,
                Body=file_bytes,
                ContentType=content_type,
                ACL="public-read"
            )
            print(f"S3: Uploaded '{filename}' with public-read ACL.", flush=True)
        except ClientError as acl_err:
            print(f"S3: Public ACL upload failed (likely BlockPublicAcls is enabled), trying upload without ACL... Error: {acl_err}", flush=True)
            s3.put_object(
                Bucket=bucket,
                Key=filename,
                Body=file_bytes,
                ContentType=content_type
            )
            print(f"S3: Uploaded '{filename}' without ACL.", flush=True)
        
        # Construct public URL
        if settings.AWS_REGION == "us-east-1":
            url = f"https://{bucket}.s3.amazonaws.com/{filename}"
        else:
            url = f"https://{bucket}.s3.{settings.AWS_REGION}.amazonaws.com/{filename}"
        return url
    except Exception as e:
        print(f"S3: Failed to upload file '{filename}' to S3. Error: {e}", flush=True)
        return None

def s3_file_exists(filename: str) -> bool:
    """Checks if a file exists in the S3 bucket (or local static folder if S3 is paused)."""
    if PAUSE_S3:
        clean_filename = filename.lstrip("/")
        local_path = os.path.join("static", clean_filename)
        return os.path.exists(local_path)

    if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
        return False
    s3 = get_s3_client()
    bucket = settings.AWS_STORAGE_BUCKET_NAME
    try:
        s3.head_object(Bucket=bucket, Key=filename)
        return True
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == "404":
            return False
        print(f"S3: Head object returned error code {error_code} for {filename}: {e}", flush=True)
        return False
    except Exception as e:
        print(f"S3: Failed to check if {filename} exists on S3. Error: {e}", flush=True)
        return False

def download_from_s3(filename: str, dest_path: str) -> bool:
    """Downloads a file from S3 (or copies from local static folder if S3 is paused) to dest_path."""
    if PAUSE_S3:
        clean_filename = filename.lstrip("/")
        local_path = os.path.join("static", clean_filename)
        if os.path.exists(local_path):
            try:
                import shutil
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy2(local_path, dest_path)
                print(f"Local Storage (S3 Paused): Successfully copied '{clean_filename}' to '{dest_path}'.", flush=True)
                return True
            except Exception as e:
                print(f"Local Storage (S3 Paused): Failed to copy '{clean_filename}' to '{dest_path}'. Error: {e}", flush=True)
                return False
        print(f"Local Storage (S3 Paused): '{clean_filename}' not found locally.", flush=True)
        return False

    if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
        return False
    s3 = get_s3_client()
    bucket = settings.AWS_STORAGE_BUCKET_NAME
    try:
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        s3.download_file(bucket, filename, dest_path)
        print(f"S3: Successfully downloaded '{filename}' to '{dest_path}'.", flush=True)
        return True
    except Exception as e:
        print(f"S3: Failed to download '{filename}' from S3. Error: {e}", flush=True)
        return False
