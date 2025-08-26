from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..crud import user as crud_user
from ..schemas.user import UserCreate, User, UserUpdate, UserPaginationResponse
from ..models.user import User as DBUser, UserRole, UserStatus
from .auth import get_current_user # 引入认证依赖

router = APIRouter(tags=["用户管理"], prefix="/users")

@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """创建新用户"""
    db_user = crud_user.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="用户名已被注册")
    return crud_user.create_user(db=db, user=user)

@router.get("/", response_model=UserPaginationResponse)
def read_users(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db), 
    current_user: Annotated[DBUser, Depends(get_current_user)] = None # 需要认证
):
    """获取所有用户列表，支持分页"""
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有管理员才能查看用户列表")
    users, total = crud_user.get_users(db, skip=skip, limit=limit)
    return {"items": users, "total": total}

@router.get("/{user_id}", response_model=User)
def read_user(
    user_id: int, 
    db: Session = Depends(get_db), 
    current_user: Annotated[DBUser, Depends(get_current_user)] = None # 需要认证
):
    """根据ID获取单个用户信息"""
    if current_user.role != UserRole.admin and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限查看此用户")
    db_user = crud_user.get_user_by_id(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="用户未找到")
    return db_user

@router.put("/{user_id}", response_model=User)
def update_user(
    user_id: int, 
    user: UserUpdate, 
    db: Session = Depends(get_db), 
    current_user: Annotated[DBUser, Depends(get_current_user)] = None # 需要认证
):
    """更新用户信息"""
    if current_user.role != UserRole.admin and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限修改此用户")
    db_user = crud_user.get_user_by_id(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="用户未找到")
    return crud_user.update_user(db=db, user_id=user_id, user_update=user)

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int, 
    db: Session = Depends(get_db), 
    current_user: Annotated[DBUser, Depends(get_current_user)] = None # 需要认证
):
    """删除用户"""
    if current_user.role != UserRole.admin: # 只有管理员才能删除用户
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有管理员才能删除用户")
    if current_user.id == user_id: # 禁止删除自己
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能删除当前登录的用户")

    db_user = crud_user.get_user_by_id(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="用户未找到")
    crud_user.delete_user(db=db, user_id=user_id)
    return {"message": "用户删除成功"} 