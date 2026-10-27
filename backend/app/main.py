import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import get_settings
from app.database import engine, Base
from app.routers import auth, listings, ai, uploads, borrow_requests, chat

settings = get_settings()

# Create tables on startup (MVP - replace with Alembic later)
Base.metadata.create_all(bind=engine)

# Ensure upload dir exists (use absolute path so it works regardless of CWD)
os.makedirs(settings.upload_dir_abs, exist_ok=True)

app = FastAPI(title="NeighborLend API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=settings.upload_dir_abs), name="uploads")

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(listings.router, prefix="/api/listings", tags=["Listings"])
app.include_router(borrow_requests.router, prefix="/api/borrow-requests", tags=["Borrow Requests"])
app.include_router(chat.router, prefix="/api", tags=["Chat & Negotiation"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI"])
app.include_router(uploads.router, prefix="/api", tags=["Uploads"])

@app.get("/api/health")
def health():
    return {"status": "ok"}
