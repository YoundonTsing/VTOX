"""
Kafka配置模块（已禁用）
现在使用Redis队列替代Kafka
"""
import logging
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

class DisabledKafkaSettings(BaseSettings):
    """已禁用的Kafka配置设置"""
    
    # 为了兼容性保留这些设置，但不再使用
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TOPIC_FAULT_DATA: str = "fault_data"
    KAFKA_TOPIC_ANALYSIS_RESULTS: str = "analysis_results"
    KAFKA_CONSUMER_GROUP: str = "fault_analysis_group"
    KAFKA_AUTO_OFFSET_RESET: str = "latest"
    KAFKA_ACKS: int = 1
    KAFKA_MAX_RETRIES: int = 3
    KAFKA_RETRY_BACKOFF_MS: int = 500

# 创建禁用的配置实例（仅用于兼容性）
kafka_settings = DisabledKafkaSettings()

# 记录信息
logger.info("⚠️  Kafka配置已禁用，现在使用Redis队列替代") 