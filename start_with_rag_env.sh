#!/bin/bash
# vtox项目使用外部RAG环境启动脚本 (Linux/Mac)

echo "🚀 使用外部RAG环境启动vtox项目"
echo "====================================="

# 设置环境变量
export EXTERNAL_RAG_ENV="/Projects/RAG_Anything/rag_env"
export RAG_ANYTHING_PATH="/Projects/RAG_Anything"
export USE_EXTERNAL_RAG="true"

# 检查外部环境是否存在
if [ ! -d "$EXTERNAL_RAG_ENV" ]; then
    echo "❌ 外部RAG环境不存在: $EXTERNAL_RAG_ENV"
    echo "请确保RAG-Anything项目已正确安装"
    exit 1
fi

# 检查RAG-Anything项目是否存在
if [ ! -d "$RAG_ANYTHING_PATH" ]; then
    echo "❌ RAG-Anything项目不存在: $RAG_ANYTHING_PATH"
    exit 1
fi

echo "✅ 外部RAG环境: $EXTERNAL_RAG_ENV"
echo "✅ RAG-Anything项目: $RAG_ANYTHING_PATH"

# 激活外部虚拟环境
echo ""
echo "🔄 激活外部RAG环境..."
source "$EXTERNAL_RAG_ENV/bin/activate"

# 设置Python路径
export PYTHONPATH="$RAG_ANYTHING_PATH:$PYTHONPATH"

# 进入项目目录
cd "$(dirname "$0")/backend"

# 启动FastAPI服务器
echo "🌐 启动FastAPI服务器..."
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000