from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .config import settings

# 数据库连接字符串从配置中获取
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# 创建数据库引擎
# connect_args用于SQLite，对于MySQL可以移除或根据需要调整
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True, # 启用连接池的预ping，检查连接是否可用
    connect_args={"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {} # 仅适用于SQLite
)

# 创建SessionLocal类，每个SessionLocal实例都是一个数据库会话
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建Base类，用于ORM模型声明
Base = declarative_base()

# 依赖项：获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 