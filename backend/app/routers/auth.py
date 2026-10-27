from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas.auth import CaptchaOut, RegisterIn, LoginIn, UserOut, TokenOut, UpdateProfileIn
from app.services.auth import issue_captcha, require_valid_captcha, hash_password, verify_password, create_access_token, get_current_user

router = APIRouter()

@router.get("/captcha", response_model=CaptchaOut)
def get_captcha(db: Session = Depends(get_db)):
    return issue_captcha(db)

@router.post("/register", response_model=TokenOut)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    require_valid_captcha(data.captcha_id, data.captcha_answer, db)
    
    if db.query(User).filter((User.username == data.username) | (User.email == data.email)).first():
        raise HTTPException(status_code=400, detail="Username or email already exists")
    
    new_user = User(
        name=data.name,
        username=data.username,
        email=data.email,
        phone=data.phone,
        password_hash=hash_password(data.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    access_token = create_access_token(new_user.id)
    return {"access_token": access_token, "user": new_user}

@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        (User.username == data.username_or_email) | (User.email == data.username_or_email)
    ).first()
    
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(user.id)
    return {"access_token": access_token, "user": user}

@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.patch("/me", response_model=UserOut)
def update_me(data: UpdateProfileIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if data.name is not None:
        current_user.name = data.name
    if data.phone is not None:
        current_user.phone = data.phone
    if data.avatar_url is not None:
        current_user.avatar_url = data.avatar_url
        
    db.commit()
    db.refresh(current_user)
    return current_user
