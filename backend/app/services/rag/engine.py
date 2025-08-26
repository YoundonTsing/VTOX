# pyright: reportMissingImports=false
"""
vtox RAG引擎
基于RAGAnything架构，专门为MCSA故障诊断优化
"""

import asyncio
import json
import os
import sys
import subprocess
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import logging

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    chromadb = None

from .config import VtoxRAGConfig

logger = logging.getLogger(__name__)

class VtoxRAGEngine:
    """vtox项目的RAG引擎"""
    
    def __init__(self, config: Optional[VtoxRAGConfig] = None):
        self.config = config or VtoxRAGConfig()
        self.vector_db = None
        self.collection = None
        self.knowledge_cache = {}
        self.initialized = False
        self.external_env_activated = False
        
    def _setup_external_environment(self):
        """设置外部虚拟环境"""
        if not self.config.use_external_env:
            return True
            
        try:
            # 检查外部虚拟环境是否存在
            env_path = Path(self.config.external_rag_env)
            if not env_path.exists():
                logger.warning(f"外部虚拟环境不存在: {env_path}")
                return False
            
            # 如果使用独立环境，只添加必要的路径
            if self.config.isolated_rag_env:
                # 只添加RAG-Anything路径到sys.path
                rag_anything_path = Path(self.config.rag_anything_path)
                if rag_anything_path.exists() and str(rag_anything_path) not in sys.path:
                    sys.path.insert(0, str(rag_anything_path))
                    logger.info(f"添加RAG-Anything路径: {rag_anything_path}")
                
                # 不添加虚拟环境的site-packages，让系统使用当前环境
                logger.info("使用独立RAG环境模式 - 仅添加RAG-Anything路径")
                self.external_env_activated = True
                return True
            
            # 非独立环境模式，添加虚拟环境路径
            # 检查Python可执行文件
            python_exe = env_path / "Scripts" / "python.exe"  # Windows
            if not python_exe.exists():
                python_exe = env_path / "bin" / "python"  # Linux/Mac
                
            if not python_exe.exists():
                logger.warning(f"Python可执行文件不存在: {python_exe}")
                return False
            
            # 添加RAG-Anything路径到sys.path
            rag_anything_path = Path(self.config.rag_anything_path)
            if rag_anything_path.exists() and str(rag_anything_path) not in sys.path:
                sys.path.insert(0, str(rag_anything_path))
                logger.info(f"添加RAG-Anything路径: {rag_anything_path}")
            
            # 添加虚拟环境的site-packages到sys.path
            site_packages = env_path / "Lib" / "site-packages"  # Windows
            if not site_packages.exists():
                site_packages = env_path / "lib" / "python3.11" / "site-packages"  # Linux
                
            if site_packages.exists() and str(site_packages) not in sys.path:
                sys.path.insert(0, str(site_packages))
                logger.info(f"添加虚拟环境site-packages: {site_packages}")
            
            self.external_env_activated = True
            logger.info("外部虚拟环境激活成功")
            return True
            
        except Exception as e:
            logger.error(f"设置外部虚拟环境失败: {e}")
            return False
    
    def _try_import_rag_anything(self):
        """尝试导入RAG-Anything模块"""
        try:
            # 尝试导入raganything
            global raganything
            import raganything
            from raganything import RAGAnything, RAGAnythingConfig
            
            logger.info("RAG-Anything模块导入成功")
            return True, RAGAnything, RAGAnythingConfig
            
        except ImportError as e:
            logger.warning(f"RAG-Anything模块导入失败: {e}")
            return False, None, None
        except Exception as e:
            logger.error(f"导入RAG-Anything时发生错误: {e}")
            return False, None, None
        
    async def initialize(self):
        """初始化RAG引擎"""
        try:
            # 设置外部虚拟环境
            env_setup_success = self._setup_external_environment()
            
            # 尝试导入RAG-Anything
            rag_available, RAGAnything, RAGAnythingConfig = self._try_import_rag_anything()
            
            if rag_available and env_setup_success:
                # 使用RAG-Anything初始化
                await self._init_with_rag_anything(RAGAnything, RAGAnythingConfig)
            else:
                # 使用简化版初始化
                logger.info("使用简化版RAG初始化")
                await self._init_simplified_rag()
            
            self.initialized = True
            logger.info("RAG引擎初始化成功")
            
        except Exception as e:
            logger.error(f"RAG引擎初始化失败: {e}")
            # 退回到简化模式
            await self._init_simplified_rag()
            self.initialized = True
            logger.info("使用简化模式初始化RAG引擎")
    
    async def _init_with_rag_anything(self, RAGAnything, RAGAnythingConfig):
        """使用RAG-Anything初始化"""
        try:
            # 配置 RAG-Anything
            rag_config = RAGAnythingConfig(
                working_dir=self.config.working_dir,
                enable_image_processing=False,  # 禁用图像处理以减少依赖
                enable_table_processing=True,
                enable_equation_processing=True,
                max_concurrent_files=1
            )
            
            # 创建 RAG-Anything 实例
            self.rag_anything = RAGAnything(config=rag_config)
            
            # 加载 MCSA 知识库
            await self._load_mcsa_knowledge()
            
            logger.info("RAG-Anything初始化成功")
            
        except Exception as e:
            logger.error(f"RAG-Anything初始化失败: {e}")
            raise
    
    async def _init_simplified_rag(self):
        """简化版RAG初始化"""
        try:
            # 初始化向量数据库
            await self._init_vector_db()
            
            # 加载 MCSA 知识库
            await self._load_mcsa_knowledge()
            
            # 构建索引
            await self._build_index()
            
            logger.info("简化版RAG初始化成功")
            
        except Exception as e:
            logger.error(f"简化版RAG初始化失败: {e}")
            raise
    
    async def _init_vector_db(self):
        """初始化向量数据库"""
        if chromadb is None:
            logger.warning("ChromaDB未安装，使用内存向量存储")
            self.vector_db = InMemoryVectorDB()
        else:
            # 使用ChromaDB
            self.vector_db = chromadb.PersistentClient(
                path=self.config.vector_db_path,
                settings=Settings(allow_reset=True)
            )
            
            # 获取或创建集合
            try:
                self.collection = self.vector_db.get_collection(
                    name="mcsa_knowledge",
                    embedding_function=None  # 使用自定义嵌入
                )
            except:
                self.collection = self.vector_db.create_collection(
                    name="mcsa_knowledge",
                    embedding_function=None
                )
    
    async def _load_mcsa_knowledge(self):
        """加载MCSA专业知识库"""
        # MCSA故障诊断知识库
        mcsa_knowledge = {
            "轴承故障诊断": {
                "content": """
                轴承故障是电机最常见的故障类型之一，可通过MCSA分析检测：
                
                1. 外圈故障特征频率：BPFO = (N/2) × (1 - d/D × cos φ) × fs
                2. 内圈故障特征频率：BPFI = (N/2) × (1 + d/D × cos φ) × fs  
                3. 滚动体故障特征频率：BSF = (D/2d) × (1 - (d/D × cos φ)²) × fs
                4. 保持架故障特征频率：FTF = (1/2) × (1 - d/D × cos φ) × fs
                
                其中：N为滚动体数量，d为滚动体直径，D为节径，φ为接触角，fs为转子频率
                """,
                "keywords": ["轴承", "bearing", "BPFO", "BPFI", "BSF", "FTF", "故障特征频率"],
                "category": "故障诊断"
            },
            
            "偏心故障分析": {
                "content": """
                偏心故障分为静偏心和动偏心两种类型：
                
                静偏心故障：
                - 特征：在电源频率处出现边频带
                - 频率成分：fs ± k×fr (k=1,2,3...)
                - 原因：定子与转子几何中心不重合
                
                动偏心故障：
                - 特征：在转子频率处出现调制
                - 频率成分：fr ± k×fs (k=1,2,3...)
                - 原因：转子重心与几何中心不重合
                """,
                "keywords": ["偏心", "eccentricity", "静偏心", "动偏心", "边频带"],
                "category": "故障诊断"
            },
            
            "转子断条故障": {
                "content": """
                转子断条故障诊断要点：
                
                特征频率：fb = f × (1 ± 2×s)
                其中：f为电源频率，s为转差率
                
                诊断方法：
                1. 观察电流频谱中是否出现fb频率成分
                2. 分析负载变化时频谱的演变
                3. 检查转子条断裂导致的不平衡
                4. 监测断条引起的转矩脉动
                """,
                "keywords": ["断条", "broken bar", "转子", "转差率", "频谱分析"],
                "category": "故障诊断"
            },
            
            "匝间短路故障": {
                "content": """
                匝间短路故障特征：
                
                1. 负序电流增大
                2. 出现特征频率分量
                3. 三相电流不平衡加剧
                
                检测方法：
                - 负序阻抗测试
                - 三相电流不平衡度计算
                - 频谱分析寻找短路特征频率
                - 绝缘电阻测试
                """,
                "keywords": ["匝间短路", "turn fault", "负序电流", "三相不平衡"],
                "category": "故障诊断"
            },
            
            "频谱分析方法": {
                "content": """
                MCSA频谱分析关键要点：
                
                1. 采样参数设置：
                   - 采样频率：至少为最高分析频率的2倍
                   - 频率分辨率：Δf = fs/N，N为采样点数
                   - 采样时间：确保足够的频率分辨率
                
                2. 窗函数选择：
                   - Hanning窗：减少频谱泄漏
                   - Blackman窗：更好的边瓣抑制
                   - Kaiser窗：可调节的时频特性
                
                3. 分析技巧：
                   - 观察基频、谐波和边频带
                   - 分析幅值变化趋势
                   - 结合时域信号特征
                """,
                "keywords": ["频谱", "FFT", "采样", "窗函数", "频率分辨率"],
                "category": "分析方法"
            },
            
            "维护建议": {
                "content": """
                基于MCSA诊断结果的维护策略：
                
                轻微异常（幅值增长<20%）：
                - 增加监测频次
                - 密切观察趋势变化
                - 制定预防性维护计划
                
                中等异常（幅值增长20-50%）：
                - 安排计划性维护
                - 准备备件和工具
                - 缩短维护周期
                
                严重异常（幅值增长>50%）：
                - 立即停机检修
                - 全面故障排查
                - 更换损坏部件
                """,
                "keywords": ["维护", "maintenance", "预防", "计划", "停机"],
                "category": "维护指南"
            }
        }
        
        # 将知识库存储到缓存
        self.knowledge_cache = mcsa_knowledge
        logger.info(f"加载了{len(mcsa_knowledge)}个MCSA知识条目")
    
    async def _build_index(self):
        """构建知识库索引"""
        if not self.knowledge_cache:
            return
        
        documents = []
        metadatas = []
        ids = []
        
        for idx, (title, knowledge) in enumerate(self.knowledge_cache.items()):
            content = knowledge["content"]
            keywords = knowledge.get("keywords", [])
            category = knowledge.get("category", "通用")
            
            # 创建文档
            documents.append(content)
            metadatas.append({
                "title": title,
                "category": category,
                "keywords": ",".join(keywords),
                "source": "mcsa_knowledge"
            })
            ids.append(f"mcsa_{idx}")
        
        # 添加到向量数据库
        if self.collection is not None and hasattr(self.collection, 'add'):
            # 这里需要实际的嵌入向量，暂时使用占位符
            embeddings = [[0.1] * self.config.embedding_dimension for _ in documents]
            
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
                embeddings=embeddings
            )
        
        logger.info(f"构建了{len(documents)}个文档的索引")
    
    async def query(self, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """查询知识库"""
        if not self.initialized:
            await self.initialize()
        
        top_k = top_k or self.config.top_k
        
        # 关键词匹配（简化版检索）
        results = []
        query_lower = query.lower()
        
        for title, knowledge in self.knowledge_cache.items():
            score = 0
            content = knowledge["content"].lower()
            keywords = [k.lower() for k in knowledge.get("keywords", [])]
            
            # 计算相关性得分
            if any(keyword in query_lower for keyword in keywords):
                score += 2
            
            if any(word in content for word in query_lower.split()):
                score += 1
            
            if score > 0:
                results.append({
                    "title": title,
                    "content": knowledge["content"],
                    "score": score,
                    "category": knowledge.get("category", ""),
                    "keywords": knowledge.get("keywords", [])
                })
        
        # 按得分排序并返回top_k结果
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
    
    async def generate_rag_response(self, query: str, llm_func) -> str:
        """生成RAG增强的回复"""
        # 检索相关知识
        relevant_docs = await self.query(query)
        
        if not relevant_docs:
            return "抱歉，未找到相关的MCSA诊断知识。请提供更具体的故障现象描述。"
        
        # 构建上下文
        context_parts = []
        for doc in relevant_docs:
            context_parts.append(f"### {doc['title']}\n{doc['content']}")
        
        context = "\n\n".join(context_parts)
        
        # 构建增强提示
        enhanced_prompt = f"""
基于以下MCSA专业知识回答用户问题：

<知识库内容>
{context}
</知识库内容>

用户问题：{query}

请基于上述专业知识，结合MCSA分析经验，为用户提供准确、详细的回答。回答应包括：
1. 直接回答用户问题
2. 相关的理论解释
3. 实际的诊断方法或建议
4. 如果适用，提供具体的公式或参数

回答要专业准确，但也要通俗易懂。
"""
        
        try:
            # 调用LLM生成回复
            response = await llm_func(enhanced_prompt)
            return response
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            # 降级到基础回复
            return f"基于知识库检索，找到以下相关信息：\n\n{context[:500]}..."


class InMemoryVectorDB:
    """简单的内存向量数据库实现"""
    
    def __init__(self):
        self.documents = []
        self.embeddings = []
        self.metadatas = []
        self.ids = []
    
    def add(self, documents, embeddings, metadatas, ids):
        self.documents.extend(documents)
        self.embeddings.extend(embeddings)
        self.metadatas.extend(metadatas)
        self.ids.extend(ids)
    
    def query(self, query_embedding, n_results=5):
        # 简化的查询实现
        return {
            "documents": [self.documents[:n_results]],
            "metadatas": [self.metadatas[:n_results]],
            "distances": [[0.1] * min(n_results, len(self.documents))]
        }