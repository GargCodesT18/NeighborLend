import math
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import (
    User, BorrowRequest, BorrowRequestStatus, HandoverStatus, Listing,
    ListingStatus, Message, NegotiationOffer, OfferStatus,
)
from app.schemas.borrow_request import BorrowRequestCreateIn, BorrowRequestOut, BorrowRequestUpdateIn
from app.schemas.notification import DisputeCreateIn, HandoverIssueCreateIn
from app.services.auth import get_current_user
from app.services.notifications import create_notification
from app.services.negotiation import calculate_rental_duration_and_cost

router = APIRouter()

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def _format_request_out(
    req: BorrowRequest,
    distance_km: Optional[float] = None,
    *,
    include_private_handover: bool = False,
) -> dict:
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
        "listing_id": req.listing_id,
        "lender_id": req.listing.owner_id if req.listing else None,
        "returned_at": req.returned_at,
        "disputed_at": req.disputed_at,
        "handover_status": req.handover_status,
        "handover_marked_at": req.handover_marked_at,
        "handover_confirmed_at": req.handover_confirmed_at,
        "handover_confirmed_by": req.handover_confirmed_by,
        "handover_issue_description": req.handover_issue_description if include_private_handover else None,
        "handover_issue_reported_at": req.handover_issue_reported_at,
        "borrowing_started_at": req.borrowing_started_at,
        "return_due_at": req.return_due_at,
        "conversation_id": _handover_conversation_id(req) if include_private_handover else None,
        "distance_km": distance_km,
        "created_at": req.created_at
    }


def _handover_conversation_id(req: BorrowRequest) -> Optional[str]:
    offer = next(
        (offer for offer in req.negotiation_offers if offer.status == OfferStatus.accepted),
        None,
    )
    return offer.conversation_id if offer else None


def _get_handover_request(request_id: str, db: Session, current_user: User, *, lock: bool = False):
    query = db.query(BorrowRequest)
    if lock:
        query = query.with_for_update()
    req = query.filter(BorrowRequest.id == request_id).first()
    if req is None:
        raise HTTPException(status_code=404, detail="Borrow request not found")
    lender_id = req.listing.owner_id if req.listing else None
    if current_user.id not in (req.borrower_id, lender_id):
        raise HTTPException(status_code=403, detail="Not authorized for this handover")
    if req.listing_id is None or lender_id is None:
        raise HTTPException(status_code=409, detail="This request is not a negotiated rental")
    return req, lender_id


def _record_handover_event(db: Session, req: BorrowRequest, actor: User, content: str) -> None:
    conversation_id = _handover_conversation_id(req)
    if conversation_id:
        db.add(Message(
            conversation_id=conversation_id,
            sender_id=actor.id,
            content=content,
            is_system=True,
        ))


@router.get("/{request_id}/handover", response_model=BorrowRequestOut)
def get_handover(
    request_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    req, _ = _get_handover_request(request_id, db, current_user)
    return _format_request_out(req, include_private_handover=True)


@router.post("/{request_id}/handover/mark-given", response_model=BorrowRequestOut)
def mark_handover_given(
    request_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    req, lender_id = _get_handover_request(request_id, db, current_user, lock=True)
    if current_user.id != lender_id:
        raise HTTPException(status_code=403, detail="Only the lender can mark the item as handed over")
    if req.handover_status != HandoverStatus.pending.value:
        raise HTTPException(status_code=409, detail="This handover is not awaiting lender action")

    req.handover_status = HandoverStatus.marked_given.value
    req.handover_marked_at = datetime.utcnow()
    create_notification(
        db, req.borrower_id, "handover_marked", "Product Handover Confirmation Required",
        f"The lender has marked {req.title} as handed over. Please inspect it and confirm its condition.",
        f"/borrow-requests/{req.id}", req.id,
    )
    _record_handover_event(db, req, current_user, f"{current_user.name} marked {req.title} as handed over. Awaiting borrower confirmation.")
    db.commit()
    db.refresh(req)
    return _format_request_out(req, include_private_handover=True)


@router.post("/{request_id}/handover/confirm", response_model=BorrowRequestOut)
def confirm_handover(
    request_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    req, lender_id = _get_handover_request(request_id, db, current_user, lock=True)
    if current_user.id != req.borrower_id:
        raise HTTPException(status_code=403, detail="Only the borrower can confirm receipt")
    if req.handover_status != HandoverStatus.marked_given.value:
        raise HTTPException(status_code=409, detail="The lender must mark the item as handed over first")
    if req.needed_from is None or req.needed_until is None:
        raise HTTPException(status_code=409, detail="Agreed rental dates are missing")

    try:
        days, _ = calculate_rental_duration_and_cost(
            req.max_price_per_day or 0, req.needed_from, req.needed_until
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=f"Invalid agreed rental dates: {exc}") from exc
    now = datetime.utcnow()
    req.handover_status = HandoverStatus.confirmed.value
    req.handover_confirmed_at = now
    req.handover_confirmed_by = current_user.id
    req.borrowing_started_at = now
    req.return_due_at = now + timedelta(days=days)
    req.status = BorrowRequestStatus.fulfilled
    create_notification(
        db, lender_id, "handover_confirmed", "Borrower Confirmed Receipt",
        f"{current_user.name} confirmed receipt of {req.title} in the agreed condition.",
        f"/borrow-requests/{req.id}", req.id,
    )
    _record_handover_event(db, req, current_user, f"{current_user.name} confirmed receipt of {req.title}. Borrowing is now active.")
    db.commit()
    db.refresh(req)
    return _format_request_out(req, include_private_handover=True)


@router.post("/{request_id}/handover/report-issue", response_model=BorrowRequestOut)
def report_handover_issue(
    request_id: str,
    data: HandoverIssueCreateIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    req, lender_id = _get_handover_request(request_id, db, current_user, lock=True)
    if current_user.id != req.borrower_id:
        raise HTTPException(status_code=403, detail="Only the borrower can report a handover issue")
    if req.handover_status != HandoverStatus.marked_given.value:
        raise HTTPException(status_code=409, detail="The item must be marked as handed over first")
    description = data.description.strip()
    if not description:
        raise HTTPException(status_code=422, detail="Issue description cannot be blank")

    req.handover_status = HandoverStatus.issue_reported.value
    req.handover_issue_description = description
    req.handover_issue_reported_at = datetime.utcnow()
    create_notification(
        db, lender_id, "handover_issue_reported", "Borrower Reported a Handover Issue",
        f"{current_user.name} reported an issue with {req.title}. Open the request and conversation to resolve it.",
        f"/borrow-requests/{req.id}", req.id,
    )
    _record_handover_event(db, req, current_user, f"{current_user.name} reported a handover issue for {req.title}: {description}")
    db.commit()
    db.refresh(req)
    return _format_request_out(req, include_private_handover=True)

@router.post("", response_model=BorrowRequestOut)
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
    db.flush()
    matching_owners = db.query(Listing.owner_id).filter(
        Listing.status == ListingStatus.published,
        Listing.category == req.category,
        Listing.owner_id != current_user.id,
    )
    if req.max_price_per_day is not None:
        matching_owners = matching_owners.filter(Listing.price_per_day <= req.max_price_per_day)
    for (owner_id,) in matching_owners.distinct().all():
        create_notification(
            db,
            owner_id,
            "borrowing_request",
            "A neighbor needs an item",
            f"{current_user.name} is looking for: {req.title}",
            f"/borrow-requests/{req.id}",
            req.id,
        )
    db.commit()
    db.refresh(req)
    return _format_request_out(req)

@router.get("", response_model=List[BorrowRequestOut])
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


@router.get("/{request_id}", response_model=BorrowRequestOut)
def get_borrow_request(request_id: str, db: Session = Depends(get_db)):
    req = db.query(BorrowRequest).filter(
        BorrowRequest.id == request_id,
        BorrowRequest.status != BorrowRequestStatus.cancelled,
    ).first()
    if req is None:
        raise HTTPException(status_code=404, detail="Borrow request not found")
    return _format_request_out(req)


def _get_rental_participants(request_id: str, db: Session, current_user: User):
    req = db.query(BorrowRequest).with_for_update().filter(
        BorrowRequest.id == request_id
    ).first()
    if req is None:
        raise HTTPException(status_code=404, detail="Borrow request not found")
    if req.listing_id is None or req.listing is None:
        raise HTTPException(status_code=400, detail="This request is not a confirmed rental")
    if current_user.id not in (req.borrower_id, req.listing.owner_id):
        raise HTTPException(status_code=403, detail="Not authorized for this rental")
    other_user_id = req.listing.owner_id if current_user.id == req.borrower_id else req.borrower_id
    return req, other_user_id


@router.post("/{request_id}/return")
def report_return(
    request_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    req, other_user_id = _get_rental_participants(request_id, db, current_user)
    if req.handover_status not in (HandoverStatus.not_applicable.value, HandoverStatus.confirmed.value):
        raise HTTPException(status_code=409, detail="The rental is not active until handover is confirmed")
    if req.returned_at is not None:
        raise HTTPException(status_code=409, detail="This rental has already been reported as returned")
    req.returned_at = datetime.utcnow()
    create_notification(
        db,
        other_user_id,
        "return",
        "Item return reported",
        f"{current_user.name} reported the return for {req.title}.",
        f"/borrow-requests/{req.id}",
        req.id,
    )
    db.commit()
    return {"status": "ok", "returned_at": req.returned_at}


@router.post("/{request_id}/dispute")
def report_dispute(
    request_id: str,
    data: DisputeCreateIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    req, other_user_id = _get_rental_participants(request_id, db, current_user)
    if req.handover_status not in (HandoverStatus.not_applicable.value, HandoverStatus.confirmed.value):
        raise HTTPException(status_code=409, detail="The rental is not active until handover is confirmed")
    if req.disputed_at is not None:
        raise HTTPException(status_code=409, detail="A dispute has already been reported for this rental")
    description = data.description.strip()
    if not description:
        raise HTTPException(status_code=422, detail="Dispute description cannot be blank")
    req.disputed_at = datetime.utcnow()
    req.dispute_description = description
    create_notification(
        db,
        other_user_id,
        "dispute",
        "A rental dispute was reported",
        f"{current_user.name} reported a dispute for {req.title}.",
        f"/borrow-requests/{req.id}",
        req.id,
    )
    db.commit()
    return {"status": "ok", "disputed_at": req.disputed_at}

@router.delete("/{request_id}")
def delete_borrow_request(request_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    req = db.query(BorrowRequest).filter(BorrowRequest.id == request_id, BorrowRequest.borrower_id == current_user.id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Borrow request not found")
    req.status = BorrowRequestStatus.cancelled
    db.commit()
    return {"status": "ok"}
