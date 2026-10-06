import os
import uuid
import shutil
from fastapi import UploadFile
from app.config import get_settings

settings = get_settings()

def save_upload(file: UploadFile, subfolder: str = "") -> str:
    upload_dir = os.path.join(settings.upload_dir, subfolder)
    os.makedirs(upload_dir, exist_ok=True)
    
    ext = file.filename.split(".")[-1] if "." in file.filename else ""
    filename = f"{uuid.uuid4()}.{ext}"
    filepath = os.path.join(upload_dir, filename)
    
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    url_path = f"/uploads/{subfolder}/{filename}" if subfolder else f"/uploads/{filename}"
    # Replace double slashes just in case
    url_path = url_path.replace("//", "/")
    return f"{settings.public_base_url}{url_path}"

def delete_upload(url: str):
    if not url.startswith(settings.public_base_url):
        return
    
    path_part = url[len(settings.public_base_url):]
    if path_part.startswith("/"):
        path_part = path_part[1:]
        
    # path_part is something like uploads/images/123.jpg
    if os.path.exists(path_part):
        os.remove(path_part)
