import os
import uuid
import shutil
from urllib.parse import urlsplit
from pathlib import Path
from fastapi import UploadFile, HTTPException
from app.config import get_settings
from supabase import create_client, Client

settings = get_settings()
LISTING_PHOTOS_BUCKET = "listing_photos"

supabase: Client = None
_public_bucket_ready = False
if settings.supabase_url and settings.supabase_service_role_key:
    supabase = create_client(settings.supabase_url, settings.supabase_service_role_key)


def _ensure_public_bucket(bucket_name: str = LISTING_PHOTOS_BUCKET) -> None:
    """Check the configured existing bucket; never create or change bucket settings."""
    global _public_bucket_ready
    if _public_bucket_ready:
        return
    if bucket_name != LISTING_PHOTOS_BUCKET:
        raise HTTPException(status_code=500, detail="Unexpected listing photo bucket configuration.")
    try:
        bucket = supabase.storage.get_bucket(bucket_name)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"The existing Supabase Storage bucket '{bucket_name}' was not found or could not be checked.",
        ) from exc
    is_public = bucket.get("public") if isinstance(bucket, dict) else getattr(bucket, "public", None)
    if is_public is not True:
        raise HTTPException(
            status_code=503,
            detail=f"Make the existing Supabase Storage bucket '{bucket_name}' public to display listing photos.",
        )
    _public_bucket_ready = True


def _make_filename(original_filename: str) -> str:
    suffix = Path(original_filename or "").suffix.lower()
    return f"{uuid.uuid4()}{suffix}"


def is_public_listing_image_url(url: str) -> bool:
    """Return true only for public URLs in this app's configured Supabase bucket."""
    if not settings.supabase_url or not isinstance(url, str):
        return False
    try:
        expected = urlsplit(settings.supabase_url)
        actual = urlsplit(url)
        return (
            expected.scheme == "https"
            and actual.scheme == "https"
            and actual.hostname == expected.hostname
            and actual.username is None
            and actual.password is None
            and actual.port in (None, 443)
            and not actual.query
            and not actual.fragment
            and actual.path.startswith(f"/storage/v1/object/public/{LISTING_PHOTOS_BUCKET}/")
            and len(actual.path) > len(f"/storage/v1/object/public/{LISTING_PHOTOS_BUCKET}/")
        )
    except ValueError:
        return False


def _require_supabase_storage() -> None:
    if supabase is None:
        raise HTTPException(
            status_code=503,
            detail="Listing photo uploads require SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY on the backend.",
        )


def _upload_to_supabase(file_bytes: bytes, object_path: str, content_type: str) -> str:
    _require_supabase_storage()
    try:
        _ensure_public_bucket()
        supabase.storage.from_(LISTING_PHOTOS_BUCKET).upload(
            object_path,
            file_bytes,
            file_options={"content-type": content_type or "application/octet-stream", "upsert": "true"},
        )
        public_url = supabase.storage.from_(LISTING_PHOTOS_BUCKET).get_public_url(object_path)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Could not upload the image to Supabase Storage.") from exc

    if not is_public_listing_image_url(public_url):
        raise HTTPException(status_code=502, detail="Supabase returned an invalid public image URL.")
    return public_url

def save_upload(file: UploadFile, subfolder: str = "") -> str:
    filename = _make_filename(file.filename)
    
    if supabase:
        file_bytes = file.file.read()
        path_in_bucket = f"{subfolder}/{filename}" if subfolder else filename
        return _upload_to_supabase(file_bytes, path_in_bucket, file.content_type or "application/octet-stream")
    else:
        upload_dir = os.path.join(settings.upload_dir_abs, subfolder)
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
    subfolder: str = "",
    *,
    require_supabase: bool = False,
    object_path: str = None,
) -> str:
    filename = _make_filename(original_filename)

    if supabase or require_supabase or object_path:
        path_in_bucket = object_path or (f"{subfolder}/{filename}" if subfolder else filename)
        return _upload_to_supabase(file_bytes, path_in_bucket, content_type or "application/octet-stream")
    else:
        upload_dir = os.path.join(settings.upload_dir_abs, subfolder)
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
        bucket_name = LISTING_PHOTOS_BUCKET
        try:
            parts = url.split(f"/object/public/{bucket_name}/")
            if len(parts) == 2:
                path_in_bucket = parts[1]
                supabase.storage.from_(bucket_name).remove([path_in_bucket])
        except Exception:
            pass
        return

    if settings.public_base_url:
        if not url.startswith(settings.public_base_url):
            return
        path_part = url[len(settings.public_base_url):]
    else:
        path_part = url

    if not path_part.startswith("/uploads/"):
        return

    upload_root = os.path.abspath(settings.upload_dir_abs)
    filepath = os.path.abspath(
        os.path.join(upload_root, path_part.removeprefix("/uploads/"))
    )
    if os.path.commonpath((upload_root, filepath)) != upload_root:
        return
    if os.path.isfile(filepath):
        os.remove(filepath)
