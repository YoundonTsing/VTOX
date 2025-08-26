"""
RAG配置管理模块
基于RAGAnything的配置系统，适配vtox项目需求
"""

from dataclasses import dataclass, field
from typing import List, Optional
import os
from pathlib import Path

@dataclass
class VtoxRAGConfig:
    """vtox项目的RAG配置类"""
    
    # 外部虚拟环境配置
    external_rag_env: str = field(default="C:\\Projects\\RAG_Anything\\rag_env")
    """外部RAG虚拟环境路径"""
    
    use_external_env: bool = field(default=True)
    """是否使用外部虚拟环境"""
    
    isolated_rag_env: bool = field(default=True)
    """是否使用独立的RAG环境"""
    
    # 工作目录配置
    working_dir: str = field(default="./backend/rag_storage")
    """RAG存储目录"""
    
    # RAG-Anything配置路径
    rag_anything_path: str = field(default="C:\\Projects\\RAG_Anything")
    """RAG-Anything项目路径"""
    
    # 知识库配置
    knowledge_base_dir: str = field(default="./backend/knowledge_base")
    """MCSA知识库目录"""
    
    # 向量数据库配置
    vector_db_type: str = field(default="chroma")
    """向量数据库类型: chroma, faiss, qdrant"""
    
    vector_db_path: str = field(default="./backend/rag_storage/vector_db")
    """向量数据库存储路径"""
    
    # 嵌入模型配置
    embedding_model: str = field(default="text-embedding-3-small")
    """嵌入模型名称"""
    
    embedding_dimension: int = field(default=1536)
    """嵌入向量维度"""
    
    # 检索配置
    top_k: int = field(default=5)
    """检索时返回的最相关文档数量"""
    
    similarity_threshold: float = field(default=0.7)
    """相似度阈值"""
    
    # 文档处理配置
    chunk_size: int = field(default=500)
    """文档分块大小"""
    
    chunk_overlap: int = field(default=50)
    """文档分块重叠"""
    
    # 缓存配置
    enable_cache: bool = field(default=True)
    """是否启用缓存"""
    
    cache_ttl: int = field(default=3600)
    """缓存过期时间(秒)"""
    
    # MCSA专业配置
    mcsa_knowledge_types: List[str] = field(default_factory=lambda: [
        "轴承故障", "偏心故障", "断条故障", "匝间短路", "频谱分析", "维护指南"
    ])
    """MCSA知识类型"""
    
    def __post_init__(self):
        """初始化后的设置"""
        # 确保目录存在
        Path(self.working_dir).mkdir(parents=True, exist_ok=True)
        Path(self.knowledge_base_dir).mkdir(parents=True, exist_ok=True)
        Path(self.vector_db_path).mkdir(parents=True, exist_ok=True)