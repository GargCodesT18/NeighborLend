from datetime import datetime
from typing import Optional, Union
from pydantic import BaseModel, EmailStr

class CaptchaOut(BaseModel):
    captcha_id: str
    question: str

class RegisterIn(BaseModel):
    name: str
    username: str
    email: EmailStr
    phone: Optional[str] = None
    password: str
    captcha_id: str
    captcha_answer: Union[int, str]

class LoginIn(BaseModel):
    username_or_email: str
    password: str

class UserOut(BaseModel):
    id: str
    name: str
    username: str
    email: str
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    trust_score: float
    avg_rating: float
    rating_count: int
    completed_rentals_count: int
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

class UpdateProfileIn(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
