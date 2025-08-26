#!/usr/bin/env python3
"""
独立RAG服务启动脚本
专门用于启动AI聊天功能的RAG服务，使用外部虚拟环境
"""

import os
import sys
import subprocess
from pathlib import Path

def start_isolated_rag_service():
    """启动独立的RAG服务"""
    print("🚀 启动独立RAG服务...")
    
    # 设置环境变量
    os.environ["ISOLATED_RAG_ENV"] = "true"
    os.environ["USE_EXTERNAL_RAG"] = "true"
    
    # 激活外部虚拟环境
    rag_env_path = Path("C:/Projects/RAG_Anything/rag_env")
    rag_anything_path = Path("C:/Projects/RAG_Anything")
    
    if not rag_env_path.exists():
        print(f"❌ 外部虚拟环境不存在: {rag_env_path}")
        return False
    
    if not rag_anything_path.exists():
        print(f"❌ RAG-Anything项目不存在: {rag_anything_path}")
        return False
    
    # 添加路径到PYTHONPATH
    current_pythonpath = os.environ.get("PYTHONPATH", "")
    new_paths = [str(rag_anything_path)]
    
    if current_pythonpath:
        new_paths.append(current_pythonpath)
    
    os.environ["PYTHONPATH"] = os.pathsep.join(new_paths)
    print(f"✅ 设置PYTHONPATH: {os.environ['PYTHONPATH']}")
    
    # 启动FastAPI应用（仅AI聊天相关路由）
    try:
        # 进入backend目录
        backend_path = Path(__file__).parent / "backend"
        os.chdir(backend_path)
        print(f"📁 工作目录: {os.getcwd()}")
        
        # 启动服务
        print("🌐 启动RAG服务...")
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "app.routers.ai_chat:router", 
            "--host", "127.0.0.1", 
            "--port", "8001",
            "--reload"
        ])
        
        return True
        
    except Exception as e:
        print(f"❌ 启动RAG服务失败: {e}")
        return False

def start_main_app_with_rag():
    """启动主应用并集成RAG功能"""
    print("🚀 启动主应用并集成RAG功能...")
    
    # 设置环境变量
    os.environ["USE_EXTERNAL_RAG"] = "true"
    os.environ["ISOLATED_RAG_ENV"] = "true"
    
    # 添加RAG-Anything路径
    rag_anything_path = Path("C:/Projects/RAG_Anything")
    if rag_anything_path.exists():
        current_pythonpath = os.environ.get("PYTHONPATH", "")
        new_paths = [str(rag_anything_path)]
        
        if current_pythonpath:
            new_paths.append(current_pythonpath)
        
        os.environ["PYTHONPATH"] = os.pathsep.join(new_paths)
        print(f"✅ 设置PYTHONPATH: {os.environ['PYTHONPATH']}")
    
    # 启动主应用
    try:
        # 进入backend目录
        backend_path = Path(__file__).parent / "backend"
        os.chdir(backend_path)
        print(f"📁 工作目录: {os.getcwd()}")
        
        # 启动主服务
        print("🌐 启动主应用服务...")
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "app.main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000",
            "--reload"
        ])
        
        return True
        
    except Exception as e:
        print(f"❌ 启动主应用失败: {e}")
        return False

def main():
    """主函数"""
    print("🔧 vtox独立RAG服务启动器")
    print("=" * 40)
    print("选择启动模式:")
    print("1. 独立RAG服务 (端口8001)")
    print("2. 主应用+RAG集成 (端口8000)")
    print("3. 退出")
    
    choice = input("\n请输入选择 (1-3): ").strip()
    
    if choice == "1":
        start_isolated_rag_service()
    elif choice == "2":
        start_main_app_with_rag()
    elif choice == "3":
        print("👋 再见!")
        sys.exit(0)
    else:
        print("❌ 无效选择")
        sys.exit(1)

if __name__ == "__main__":
    main()