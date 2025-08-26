#!/usr/bin/env python3
"""
vtox RAG环境检测和配置脚本
检测并配置外部RAG-Anything虚拟环境
"""

import os
import sys
import subprocess
from pathlib import Path
import json

def check_external_rag_env():
    """检测外部RAG环境"""
    rag_env_path = Path("C:/Projects/RAG_Anything/rag_env")
    rag_project_path = Path("C:/Projects/RAG_Anything")
    
    print("🔍 检测外部RAG环境...")
    
    # 检查虚拟环境
    if not rag_env_path.exists():
        print(f"❌ 虚拟环境不存在: {rag_env_path}")
        return False
    
    # 检查Python可执行文件
    python_exe = rag_env_path / "Scripts" / "python.exe"  # Windows
    if not python_exe.exists():
        python_exe = rag_env_path / "bin" / "python"  # Linux/Mac
    
    if not python_exe.exists():
        print(f"❌ Python可执行文件不存在: {python_exe}")
        return False
    
    # 检查RAG-Anything项目
    if not rag_project_path.exists():
        print(f"❌ RAG-Anything项目不存在: {rag_project_path}")
        return False
    
    print(f"✅ 虚拟环境存在: {rag_env_path}")
    print(f"✅ Python可执行文件: {python_exe}")
    print(f"✅ RAG-Anything项目: {rag_project_path}")
    
    return True

def test_rag_imports():
    """测试RAG模块导入"""
    print("\n🧪 测试RAG模块导入...")
    
    try:
        # 添加路径到sys.path
        rag_anything_path = Path("C:/Projects/RAG_Anything")
        if str(rag_anything_path) not in sys.path:
            sys.path.insert(0, str(rag_anything_path))
        
        # 尝试导入
        import raganything
        from raganything import RAGAnything, RAGAnythingConfig
        
        print("✅ raganything模块导入成功")
        print(f"   版本: {getattr(raganything, '__version__', '未知')}")
        return True
        
    except ImportError as e:
        print(f"❌ raganything模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 导入时发生错误: {e}")
        return False

def check_dependencies():
    """检查依赖包"""
    print("\n📦 检查依赖包...")
    
    # vtox项目的必需依赖包
    required_packages = [
        "redis",           # Redis客户端
        "fastapi",         # FastAPI框架
        "uvicorn",         # ASGI服务器
        "pydantic",        # 数据校验
        "aiohttp",         # 异步HTTP客户端
        "websockets",      # WebSocket支持
        "sqlalchemy",      # ORM框架
        "pandas",          # 数据处理
        "numpy",           # 数值计算
        # RAG相关依赖
        "lightrag",        # RAG核心库
        "chromadb",        # 向量数据库
        "sentence-transformers",  # 嵌入模型
        "transformers",    # Transformer模型
        "torch"            # PyTorch
    ]
    
    missing_packages = []
    installed_packages = []
    
    for package in required_packages:
        try:
            # 特殊处理一些包名
            import_name = package
            if package == "sentence-transformers":
                import_name = "sentence_transformers"
            elif package == "lightrag":
                # lightrag可能不存在，跳过
                try:
                    __import__(import_name)
                    print(f"✅ {package}")
                    installed_packages.append(package)
                except ImportError:
                    print(f"❌ {package} (缺失 - 可选)")
                continue
            
            __import__(import_name)
            print(f"✅ {package}")
            installed_packages.append(package)
        except ImportError:
            print(f"❌ {package} (缺失)")
            missing_packages.append(package)
    
    print(f"\n✅ 已安装: {len(installed_packages)} 个")
    print(f"❌ 缺失: {len(missing_packages)} 个")
    
    return missing_packages

def install_missing_packages(missing_packages):
    """安装缺失的包"""
    if not missing_packages:
        print("✅ 所有依赖包均已安装")
        return True
    
    print(f"\n📥 安装缺失的包: {', '.join(missing_packages)}")
    
    # 使用外部环境的pip
    rag_env_path = Path("C:/Projects/RAG_Anything/rag_env")
    pip_exe = rag_env_path / "Scripts" / "pip.exe"  # Windows
    if not pip_exe.exists():
        pip_exe = rag_env_path / "bin" / "pip"  # Linux/Mac
    
    if not pip_exe.exists():
        print(f"❌ pip不存在: {pip_exe}")
        return False
    
    # 优先安装核心依赖
    core_packages = ["redis", "fastapi", "uvicorn", "pydantic", "aiohttp"]
    priority_packages = [pkg for pkg in missing_packages if pkg in core_packages]
    other_packages = [pkg for pkg in missing_packages if pkg not in core_packages]
    
    all_success = True
    
    # 先安装核心依赖
    if priority_packages:
        print(f"🚀 优先安装核心依赖: {', '.join(priority_packages)}")
        try:
            subprocess.run([str(pip_exe), "install"] + priority_packages, 
                         check=True, capture_output=True, text=True)
            for pkg in priority_packages:
                print(f"✅ {pkg} 安装成功")
        except subprocess.CalledProcessError as e:
            print(f"❌ 核心依赖安装失败: {e}")
            print(f"stderr: {e.stderr}")
            all_success = False
    
    # 再安装其他依赖
    for package in other_packages:
        try:
            print(f"📦 安装 {package}...")
            result = subprocess.run([str(pip_exe), "install", package], 
                                  check=True, capture_output=True, text=True,
                                  timeout=300)  # 5分钟超时
            print(f"✅ {package} 安装成功")
        except subprocess.TimeoutExpired:
            print(f"⚠️ {package} 安装超时，跳过")
            all_success = False
        except subprocess.CalledProcessError as e:
            print(f"❌ {package} 安装失败: {e}")
            if e.stderr:
                print(f"   错误信息: {e.stderr.strip()}")
            all_success = False
    
    return all_success

def create_env_config():
    """创建环境配置文件"""
    print("\n⚙️ 创建环境配置文件...")
    
    config = {
        "external_rag_env": "C:/Projects/RAG_Anything/rag_env",
        "rag_anything_path": "C:/Projects/RAG_Anything",
        "use_external_env": True,
        "isolated_rag_env": True,  # 使用独立环境
        "working_dir": "./backend/rag_storage",
        "vector_db_path": "./backend/rag_storage/vector_db"
    }
    
    config_path = Path("backend/rag_config.json")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 配置文件已创建: {config_path}")

def test_vtox_rag():
    """测试vtox RAG功能"""
    print("\n🚀 测试vtox RAG功能...")
    
    try:
        # 导入vtox RAG模块
        sys.path.insert(0, "backend")
        from app.services.rag import VtoxRAGEngine, VtoxRAGConfig
        
        # 创建配置
        config = VtoxRAGConfig(
            external_rag_env="C:/Projects/RAG_Anything/rag_env",
            rag_anything_path="C:/Projects/RAG_Anything",
            use_external_env=True
        )
        
        # 创建引擎
        engine = VtoxRAGEngine(config)
        
        print("✅ vtox RAG模块导入成功")
        print("✅ RAG引擎创建成功")
        
        return True
        
    except Exception as e:
        print(f"❌ vtox RAG测试失败: {e}")
        return False

def main():
    """主函数"""
    print("🔧 vtox RAG环境配置工具")
    print("=" * 50)
    
    # 1. 检测外部环境
    if not check_external_rag_env():
        print("\n❌ 外部RAG环境检测失败，请确保：")
        print("   1. C:/Projects/RAG_Anything/rag_env 存在")
        print("   2. C:/Projects/RAG_Anything 项目存在")
        return
    
    # 2. 测试模块导入
    if not test_rag_imports():
        print("\n❌ RAG模块导入失败，请检查环境配置")
        return
    
    # 3. 检查依赖
    missing_packages = check_dependencies()
    
    if missing_packages:
        install_choice = input(f"\n是否安装缺失的包? (y/n): ").lower()
        if install_choice == 'y':
            if install_missing_packages(missing_packages):
                print("\n✅ 依赖包安装完成，重新检查依赖...")
                # 重新检查依赖
                check_dependencies()
            else:
                print("\n⚠️  部分依赖包安装失败，请手动安装")
    
    # 4. 创建配置文件
    create_env_config()
    
    # 5. 测试vtox RAG
    if test_vtox_rag():
        print("\n🎉 vtox RAG环境配置完成！")
        print("\n使用方法:")
        print("1. 启动vtox后端: cd backend && python -m uvicorn app.main:app --reload")
        print("2. 访问RAG状态: http://localhost:8000/ai/rag/status")
        print("3. 测试RAG查询: http://localhost:8000/ai/rag/query")
    else:
        print("\n❌ vtox RAG配置失败")

if __name__ == "__main__":
    main()