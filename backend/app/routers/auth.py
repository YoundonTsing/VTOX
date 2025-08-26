from datetime import timedelta
from typing import Annotated
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from pydantic import BaseModel

from ..core.config import settings
from ..core.database import get_db
from ..core.security import create_access_token, verify_password
from ..crud.user import get_user_by_username, create_user
from ..schemas.token import Token, TokenData
from ..schemas.user import UserCreate, UserInDB
from ..models.user import User

# 获取日志记录器
logger = logging.getLogger(__name__)

# 定义登录请求体模型
class LoginRequest(BaseModel):
    username: str
    password: str

router = APIRouter(tags=["认证"], prefix="/auth")

# @router.post("/register", response_model=UserInDB)
# def register_user(user: UserCreate, db: Session = Depends(get_db)):
#     """用户注册"""
#     db_user = get_user_by_username(db, username=user.username)
#     if db_user:
#         raise HTTPException(status_code=400, detail="用户名已被注册")
#     return create_user(db=db, user=user)

@router.post("/token", response_model=Token)
def login_for_access_token(form_data: LoginRequest, db: Session = Depends(get_db)):
    """获取JWT访问令牌"""
    logger.info(f"尝试登录用户: {form_data.username}")
    try:
        # 记录请求体
        logger.info(f"请求体: {form_data}")
        
        # 记录数据库连接信息
        logger.info(f"数据库连接 URL: {settings.DATABASE_URL}")
        
        # 尝试获取用户
        logger.info(f"尝试从数据库获取用户: {form_data.username}")
        user = get_user_by_username(db, username=form_data.username)
        
        if not user:
            logger.warning(f"登录失败: 用户不存在 - {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 记录用户信息
        logger.info(f"用户存在: {user.username}, ID: {user.id}")
        
        # 验证密码
        logger.info(f"尝试验证密码...")
        if not verify_password(form_data.password, str(user.hashed_password)):
            logger.warning(f"登录失败: 密码错误 - {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 生成访问令牌
        logger.info(f"密码验证成功，生成访问令牌...")
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username},
            expires_delta=access_token_expires
        )
        logger.info(f"用户登录成功: {form_data.username}")
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        logger.error(f"登录过程中发生异常: {str(e)}")
        logger.exception("详细异常信息")
        raise

# 安全依赖：获取当前用户
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=str(username))
    except JWTError: # 捕获 JWTError
        raise credentials_exception
    # 确保username不为None
    username = token_data.username
    if username is None:
        raise credentials_exception
        
    user = get_user_by_username(db, username=username)
    if user is None:
        raise credentials_exception
    return user

@router.get("/users/me", response_model=UserInDB)
def read_users_me(current_user: Annotated[UserInDB, Depends(get_current_user)]):
    """获取当前用户信息 (需要认证) """
    return current_user 