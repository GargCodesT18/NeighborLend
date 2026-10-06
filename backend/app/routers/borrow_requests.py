import math
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, BorrowRequest, BorrowRequestStatus
from app.schemas.borrow_request import BorrowRequestCreateIn, BorrowRequestOut, BorrowRequestUpdateIn
from app.services.auth import get_current_user

router = APIRouter()

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def _format_request_out(req: BorrowRequest, distance_km: Optional[float] = None) -> dict:
    return {
        "id": req.id,
        "borrower_id": req.borrower_id,
        "borrower_name": req.borrower.name if req.borrower else "Anonymous",
        "borrower_trust_score": req.borrower.trust_score if req.borrower else 50.0,
        "title": req.title,
        "category": req.category,
        "description": req.description,
        "max_price_per_day": req.max_price_per_day,
        "needed_from": req.needed_from,
        "needed_until": req.needed_until,
        "latitude": req.latitude,
        "longitude": req.longitude,
        "radius_km": req.radius_km,
        "address_text": req.address_text,
        "status": req.status,
        "distance_km": distance_km,
        "created_at": req.created_at
    }

@router.post("/", response_model=BorrowRequestOut)
def create_borrow_request(data: BorrowRequestCreateIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    req = BorrowRequest(
        borrower_id=current_user.id,
        title=data.title,
        category=data.category,
        description=data.description,
        max_price_per_day=data.max_price_per_day,
        needed_from=data.needed_from,
        needed_until=data.needed_until,
        latitude=data.latitude,
        longitude=data.longitude,
        radius_km=data.radius_km,
        address_text=data.address_text,
        status=BorrowRequestStatus.open
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return _format_request_out(req)

@router.get("/", response_model=List[BorrowRequestOut])
def list_borrow_requests(
    category: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    radius_km: float = 50.0,
    db: Session = Depends(get_db)
):
    query = db.query(BorrowRequest).filter(BorrowRequest.status == BorrowRequestStatus.open)
    if category:
        query = query.filter(BorrowRequest.category == category)
        
    all_reqs = query.order_by(BorrowRequest.created_at.desc()).all()
    if lat is not None and lon is not None:
        results = []
        for r in all_reqs:
            if r.latitude is not None and r.longitude is not None:
                dist = haversine(lat, lon, r.latitude, r.longitude)
                if dist <= radius_km:
                    results.append((dist, r))
        results.sort(key=lambda x: x[0])
        return [_format_request_out(r, dist) for dist, r in results]
    
    return [_format_request_out(r) for r in all_reqs]

@router.get("/my", response_model=List[BorrowRequestOut])
def list_my_requests(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    all_reqs = db.query(BorrowRequest).filter(
        BorrowRequest.borrower_id == current_user.id,
        BorrowRequest.status != BorrowRequestStatus.cancelled
    ).all()
    return [_format_request_out(r) for r in all_reqs]

@router.delete("/{request_id}")
def delete_borrow_request(request_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    req = db.query(BorrowRequest).filter(BorrowRequest.id == request_id, BorrowRequest.borrower_id == current_user.id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Borrow request not found")
    req.status = BorrowRequestStatus.cancelled
    db.commit()
    return {"status": "ok"}
