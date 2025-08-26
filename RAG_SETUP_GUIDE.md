# vtox RAG环境设置指南

## 概述

vtox项目现已完全集成RAG（检索增强生成）功能，支持使用外部RAG-Anything虚拟环境。本指南将帮助您正确配置和使用RAG功能。

## 环境模式

vtox支持两种RAG环境模式：

1. **集成模式**：主应用和RAG功能使用同一个环境
2. **独立模式**：RAG功能使用外部虚拟环境，主应用使用基础环境

推荐使用**独立模式**，可以避免依赖冲突并提高系统稳定性。

## 前置条件

- 外部RAG环境：`C:\Projects\RAG_Anything\rag_env`
- RAG-Anything项目：`C:\Projects\RAG_Anything`
- Python 3.10+
- 已配置的通义千问API Key（可选）

## 快速启动

### 方法一：自动化设置（推荐）

1. **运行环境检测脚本**
```bash
cd C:\Projects\vtox
python setup_rag_env.py
```

2. **使用外部环境启动**
```bash
start_with_rag_env.bat
```

### 方法二：独立环境模式

1. **选择独立RAG服务模式**
```bash
start_with_rag_env.bat
# 选择"2. 独立RAG服务"
```

2. **或者直接运行独立服务**
```bash
cd C:\Projects\vtox
python start_rag_service.py
# 选择"1. 独立RAG服务"
```

### 方法三：手动设置

1. **设置环境变量**
```bash
set USE_EXTERNAL_RAG=true
set ISOLATED_RAG_ENV=true
set PYTHONPATH=C:\Projects\RAG_Anything;%PYTHONPATH%
```

2. **启动服务**
```bash
# 启动主应用
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 在另一个终端启动RAG服务
cd ..
python start_rag_service.py
# 选择"1. 独立RAG服务"
```

## 功能验证

### 1. 检查RAG状态
```bash
# 集成模式
curl http://localhost:8000/ai/rag/status

# 独立模式
curl http://localhost:8001/ai/rag/status
```

预期响应：
```json
{
  "status": "active",
  "knowledge_count": 6,
  "config": {
    "working_dir": "./backend/rag_storage",
    "external_rag_env": "C:/Projects/RAG_Anything/rag_env",
    "use_external_env": true
  },
  "knowledge_categories": ["故障诊断", "分析方法", "维护指南"]
}
```

### 2. 测试RAG知识检索
```bash
# 集成模式
curl -X POST http://localhost:8000/ai/rag/query \
  -H "Content-Type: application/json" \
  -d '{"message": "轴承外圈故障诊断方法"}'

# 独立模式
curl -X POST http://localhost:8001/ai/rag/query \
  -H "Content-Type: application/json" \
  -d '{"message": "轴承外圈故障诊断方法"}'
```

### 3. 测试RAG增强的AI对话
```bash
curl -X POST http://localhost:8000/ai/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "电机振动异常，怀疑是轴承问题，该如何诊断？",
    "model_provider": "qwen"
  }'
```

### 4. 测试流式RAG对话
```bash
curl -X POST http://localhost:8000/ai/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "MCSA频谱分析的关键要点", "model_provider": "qwen"}'
```

## 配置选项

### RAG配置文件
位置：`backend/app/services/rag/config.py`

关键配置项：
- `external_rag_env`: 外部虚拟环境路径
- `rag_anything_path`: RAG-Anything项目路径
- `use_external_env`: 是否使用外部环境
- `working_dir`: RAG存储目录
- `top_k`: 检索返回的文档数量

### 环境变量
- `QWEN_API_KEY`: 通义千问API密钥
- `USE_EXTERNAL_RAG`: 是否使用外部RAG环境
- `PYTHONPATH`: Python模块搜索路径

## RAG功能架构

### 三级降级策略
1. **RAG-Anything模式**：使用完整的RAG-Anything功能
2. **简化RAG模式**：使用内置的向量检索
3. **本地知识库模式**：使用预定义的MCSA知识

### 知识库内容
- 轴承故障诊断
- 偏心故障分析
- 转子断条故障
- 匝间短路故障
- 频谱分析方法
- 维护建议

### API端点
- `/ai/chat`: RAG增强的AI对话
- `/ai/chat/stream`: 流式RAG对话
- `/ai/rag/query`: 纯RAG知识检索
- `/ai/rag/status`: RAG系统状态
- `/ai/models`: 可用模型列表
- `/ai/health`: AI服务健康检查

## 故障排除

### 常见问题

**1. RAG环境检测失败**
- 检查外部环境路径是否正确
- 确保RAG-Anything项目存在
- 验证Python可执行文件路径

**2. 模块导入失败**
- 检查PYTHONPATH设置
- 确保sys.path包含RAG-Anything路径
- 验证依赖包是否安装

**3. API Key配置问题**
- 检查QWEN_API_KEY环境变量
- 验证API Key格式（sk-开头）
- 测试API Key有效性

**4. 向量数据库问题**
- 检查ChromaDB是否安装
- 确保存储目录权限正确
- 验证向量数据库初始化

### 日志分析

启动时查看关键日志：
```
✅ 外部虚拟环境激活成功
✅ RAG-Anything模块导入成功
✅ RAG引擎初始化成功
```

或者降级日志：
```
⚠️  RAG功能不可用，降级到标准API调用
✅ 使用简化模式初始化RAG引擎
```

## 性能优化

### 建议配置
- `top_k`: 3-5个文档（平衡相关性和响应速度）
- `chunk_size`: 500字符（适合中文文本）
- `similarity_threshold`: 0.7（过滤低相关性结果）

### 缓存策略
- 启用查询结果缓存
- 设置合适的缓存TTL（3600秒）
- 定期清理过期缓存

## 开发扩展

### 添加新知识
在`VtoxRAGEngine._load_mcsa_knowledge()`中添加新的知识条目：

```python
"新故障类型": {
    "content": "故障描述和诊断方法...",
    "keywords": ["关键词1", "关键词2"],
    "category": "故障类别"
}
```

### 自定义检索逻辑
继承`VtoxRAGEngine`类并重写`query()`方法：

```python
class CustomRAGEngine(VtoxRAGEngine):
    async def query(self, query: str, top_k: Optional[int] = None):
        # 自定义检索逻辑
        pass
```

### 集成新的向量数据库
实现新的向量数据库适配器：

```python
class CustomVectorDB:
    def add(self, documents, embeddings, metadatas, ids):
        # 实现添加逻辑
        pass
    
    def query(self, query_embedding, n_results=5):
        # 实现查询逻辑
        pass
```

## 总结

vtox的RAG功能为电机故障诊断提供了强大的知识检索和智能问答能力。通过使用外部RAG-Anything环境，系统可以充分利用现有的RAG基础设施，同时保持轻量级和高性能的特点。

如需更多帮助，请查看相关文档或联系开发团队。