import os
import uuid
import shutil
from fastapi import UploadFile, HTTPException
from app.config import get_settings
from supabase import create_client, Client

settings = get_settings()

supabase: Client = None
if settings.supabase_url and settings.supabase_service_role_key:
    supabase = create_client(settings.supabase_url, settings.supabase_service_role_key)

def save_upload(file: UploadFile, subfolder: str = "") -> str:
    ext = file.filename.split(".")[-1] if "." in file.filename else ""
    filename = f"{uuid.uuid4()}.{ext}"
    
    if supabase:
        bucket_name = "listing-images"
        path_in_bucket = f"{subfolder}/{filename}" if subfolder else filename
        file_bytes = file.file.read()
        try:
            # We try to create the bucket just in case it doesn't exist, ignore errors if it does
            try:
                supabase.storage.create_bucket(bucket_name, options={"public": True})
            except Exception:
                pass
            
            res = supabase.storage.from_(bucket_name).upload(path_in_bucket, file_bytes, file_options={"content-type": file.content_type})
            public_url = supabase.storage.from_(bucket_name).get_public_url(path_in_bucket)
            return public_url
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error uploading to Supabase: {str(e)}")
    else:
        upload_dir = os.path.join(settings.upload_dir, subfolder)
        os.makedirs(upload_dir, exist_ok=True)
        filepath = os.path.join(upload_dir, filename)
        
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        url_path = f"/uploads/{subfolder}/{filename}" if subfolder else f"/uploads/{filename}"
        url_path = url_path.replace("//", "/")
        return f"{settings.public_base_url}{url_path}"
    
    
def save_upload_from_bytes(
    file_bytes: bytes,
    original_filename: str,
    content_type: str,
    subfolder: str = ""
) -> str:
    ext = original_filename.split(".")[-1] if "." in original_filename else ""
    filename = f"{uuid.uuid4()}.{ext}"

    if supabase:
        bucket_name = "listing-images"
        path_in_bucket = f"{subfolder}/{filename}" if subfolder else filename

        try:
            try:
                supabase.storage.create_bucket(
                    bucket_name,
                    options={"public": True}
                )
            except Exception:
                pass

            supabase.storage.from_(bucket_name).upload(
                path_in_bucket,
                file_bytes,
                file_options={"content-type": content_type}
            )

            return supabase.storage.from_(
                bucket_name
            ).get_public_url(path_in_bucket)

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error uploading to Supabase: {str(e)}"
            )

    else:
        upload_dir = os.path.join(settings.upload_dir, subfolder)
        os.makedirs(upload_dir, exist_ok=True)

        filepath = os.path.join(upload_dir, filename)

        with open(filepath, "wb") as buffer:
            buffer.write(file_bytes)

        url_path = (
            f"/uploads/{subfolder}/{filename}"
            if subfolder
            else f"/uploads/{filename}"
        )

        return f"{settings.public_base_url}{url_path}"

def delete_upload(url: str):
    if supabase and url.startswith(settings.supabase_url):
        bucket_name = "listing-images"
        try:
            parts = url.split(f"/object/public/{bucket_name}/")
            if len(parts) == 2:
                path_in_bucket = parts[1]
                supabase.storage.from_(bucket_name).remove([path_in_bucket])
        except Exception:
            pass
        return
        
    if not url.startswith(settings.public_base_url):
        return
    
    path_part = url[len(settings.public_base_url):]
    if path_part.startswith("/"):
        path_part = path_part[1:]
        
    if os.path.exists(path_part):
        os.remove(path_part)
