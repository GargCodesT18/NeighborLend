from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class NotificationOut(BaseModel):
    id: str
    notification_type: str
    title: str
    message: str
    link_url: str
    borrow_request_id: Optional[str] = None
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UnreadCountOut(BaseModel):
    unread_count: int


class DisputeCreateIn(BaseModel):
    description: str = Field(..., min_length=1, max_length=2000)


class HandoverIssueCreateIn(BaseModel):
    description: str = Field(..., min_length=1, max_length=2000)
