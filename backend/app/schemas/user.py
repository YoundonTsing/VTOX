from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr
from typing import List

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = "operator"
    status: Optional[str] = "active"

class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=50)

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    status: Optional[str] = None

class UserInDB(UserBase):
    id: int
    hashed_password: str
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True

class User(UserBase):
    id: int
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserPaginationResponse(BaseModel):
    total: int
    items: List[User] 