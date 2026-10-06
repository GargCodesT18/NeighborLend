import enum
import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.database import Base

def _uuid() -> str:
    return str(uuid.uuid4())

class ListingStatus(str, enum.Enum):
    draft = "draft"
    pending_review = "pending_review"
    published = "published"
    flagged = "flagged"
    paused = "paused"
    removed = "removed"

class BorrowRequestStatus(str, enum.Enum):
    open = "open"
    fulfilled = "fulfilled"
    closed = "closed"
    cancelled = "cancelled"

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    phone = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    avatar_url = Column(String, nullable=True)
    trust_score = Column(Float, default=50.0)
    avg_rating = Column(Float, default=0.0)
    rating_count = Column(Integer, default=0)
    completed_rentals_count = Column(Integer, default=0)
    disputes_against_count = Column(Integer, default=0)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    listings = relationship("Listing", back_populates="owner", foreign_keys="Listing.owner_id")
    borrow_requests = relationship("BorrowRequest", back_populates="borrower", foreign_keys="BorrowRequest.borrower_id")

class Listing(Base):
    __tablename__ = "listings"
    id = Column(String, primary_key=True, default=_uuid)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    description = Column(Text, default="")
    years_owned = Column(Float, default=0)
    price_bought = Column(Float, default=0)
    price_per_day = Column(Float, nullable=False)
    min_price_per_day = Column(Float, nullable=True)
    security_deposit = Column(Float, default=0)
    lending_radius_km = Column(Float, default=10)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    address_text = Column(String, default="")
    status = Column(Enum(ListingStatus), default=ListingStatus.published, index=True)
    moderation_reason = Column(String, nullable=True)
    ai_label = Column(String, nullable=True)
    ai_confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    owner = relationship("User", back_populates="listings", foreign_keys=[owner_id])
    photos = relationship("ListingPhoto", back_populates="listing", cascade="all, delete-orphan")

class ListingPhoto(Base):
    __tablename__ = "listing_photos"
    id = Column(String, primary_key=True, default=_uuid)
    listing_id = Column(String, ForeignKey("listings.id"), nullable=False, index=True)
    url = Column(String, nullable=False)
    is_cover = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    listing = relationship("Listing", back_populates="photos")

class BorrowRequest(Base):
    __tablename__ = "borrow_requests"
    id = Column(String, primary_key=True, default=_uuid)
    borrower_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    category = Column(String, nullable=False)
    description = Column(Text, default="")
    max_price_per_day = Column(Float, nullable=True)
    needed_from = Column(DateTime, nullable=True)
    needed_until = Column(DateTime, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    radius_km = Column(Float, default=10)
    address_text = Column(String, default="")
    status = Column(Enum(BorrowRequestStatus), default=BorrowRequestStatus.open, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    borrower = relationship("User", back_populates="borrow_requests", foreign_keys=[borrower_id])
