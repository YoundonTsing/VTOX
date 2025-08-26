from sqlalchemy import Column, Integer, String, DateTime, Enum
import enum

from ..core.database import Base

class UserRole(enum.Enum):
    admin = "admin"
    operator = "operator"
    guest = "guest"

class UserStatus(enum.Enum):
    active = "active"
    disabled = "disabled"

class User(Base):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True} # 解决重复定义表的问题，尤其在开发热重载时

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.operator, nullable=False)
    status = Column(Enum(UserStatus), default=UserStatus.active, nullable=False)
    last_login = Column(DateTime, nullable=True) 