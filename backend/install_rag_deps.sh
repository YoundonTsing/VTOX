#!/bin/bash

# RAG功能依赖安装脚本

echo "开始安装vtox RAG功能依赖..."

# 安装向量数据库
echo "安装ChromaDB..."
pip install chromadb

# 安装文本处理库
echo "安装文本处理库..."
pip install sentence-transformers
pip install transformers
pip install torch

# 安装其他依赖
echo "安装其他依赖..."
pip install faiss-cpu  # CPU版本的FAISS
pip install numpy
pip install scikit-learn

# 可选：安装GPU版本（如果有GPU）
# pip install faiss-gpu

echo "RAG依赖安装完成！"
echo ""
echo "使用方法："
echo "1. 启动后端服务"
echo "2. 访问 http://localhost:8000/ai/rag/status 检查RAG状态"
echo "3. 使用 /ai/rag/query 进行纯RAG检索"
echo "4. 使用 /ai/chat 进行RAG增强的AI对话"