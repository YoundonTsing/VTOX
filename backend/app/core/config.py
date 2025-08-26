"""
系统配置模块
集中管理应用程序配置参数
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 数据目录
DATA_DIR = os.path.join(BASE_DIR, "data")
SAMPLES_DIR = os.path.join(DATA_DIR, "samples")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")

# 确保目录存在
os.makedirs(SAMPLES_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

# 日志目录
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "app.log")

# 诊断阈值配置
DIAGNOSIS_THRESHOLDS = {
    "warning": 0.3,
    "fault": 0.7,
    "I2_avg": 0.05,            # 负序电流平均值阈值
    "I2_I1_ratio": 0.02,       # 负序/正序比值阈值
    "unbalance_avg": 5.0,      # 电流不平衡度阈值(%)
    "kurtosis_delta_iq": 3.0,  # ΔI_q峭度阈值
    "delta_eta_avg": -0.03     # 效率残差平均值阈值
}

# API配置
API_CONFIG = {
    "title": "匝间短路故障诊断系统API",
    "description": "电机匝间短路故障诊断系统后端API",
    "version": "1.0.0",
    "docs_url": "/docs",
    "redoc_url": "/redoc"
}

# CORS配置
CORS_CONFIG = {
    "allow_origins": ["*"],  # 在生产环境中应该指定允许的源
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
    "expose_headers": ["Content-Disposition"]  # 允许前端访问Content-Disposition头，用于文件下载
}

# 默认值配置
DEFAULT_VALUES = {
    "eta_ref": 0.93,  # 默认效率参考值
}

class Settings(BaseSettings):
    # 数据库配置
    DATABASE_URL: str = "mysql+pymysql://root:123456@localhost:3306/vtox_db" # 使用正确的数据库连接信息
    
    # JWT 认证配置
    SECRET_KEY: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7" # 使用一个安全的密钥
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30 # 访问令牌过期时间（分钟）

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

# 创建 .env 文件示例 (如果不存在)
env_file_path = BASE_DIR / ".env"
if not os.path.exists(env_file_path):
    with open(env_file_path, "w") as f:
        f.write("# 数据库配置\n")
        f.write("DATABASE_URL=\"mysql+pymysql://root:123456@localhost:3306/vtox_db\"\n\n")
        f.write("# JWT 认证配置\n")
        f.write("SECRET_KEY=\"09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7\"\n")
        f.write("ALGORITHM=\"HS256\"\n")
        f.write("ACCESS_TOKEN_EXPIRE_MINUTES=30\n")
    print(f"创建了示例 .env 文件: {env_file_path}，请根据实际情况修改其中的配置。") 