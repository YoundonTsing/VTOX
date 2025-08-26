from datetime import datetime
from sqlalchemy.orm import Session
from typing import List, Optional

from backend.app.models.user import User
from backend.app.schemas.user import UserCreate, UserUpdate
from backend.app.core.security import get_password_hash

def get_user_by_username(db: Session, username: str):
    """根据用户名获取用户"""
    return db.query(User).filter(User.username == username).first()

def get_user_by_id(db: Session, user_id: int):
    """根据ID获取用户"""
    return db.query(User).filter(User.id == user_id).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    """获取用户列表和总数"""
    query = db.query(User)
    total = query.count()
    users = query.offset(skip).limit(limit).all()
    return users, total

def create_user(db: Session, user: UserCreate):
    """创建新用户"""
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username, 
        hashed_password=hashed_password,
        name=user.name,
        email=user.email,
        role=user.role,
        status=user.status
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user_id: int, user_update: UserUpdate):
    """更新用户信息"""
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return None
    
    update_data = user_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user

def update_password(db: Session, user_id: int, new_hashed_password: str):
    """更新用户密码"""
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return None
    
    db_user.hashed_password = new_hashed_password
    db.commit()
    db.refresh(db_user)
    return db_user

def update_login_time(db: Session, user_id: int):
    """更新用户登录时间"""
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return None
    
    db_user.last_login = datetime.now()
    db.commit()
    db.refresh(db_user)
    return db_user

def delete_user(db: Session, user_id: int):
    """删除用户"""
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return False
    
    db.delete(db_user)
    db.commit()
    return True