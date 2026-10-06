from fastapi import APIRouter, UploadFile, File
from app.services.storage_service import save_upload

router = APIRouter()

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    url = save_upload(file, 'images')
    return {"url": url}
