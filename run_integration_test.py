#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VTOX 集成测试启动脚本

使用方法：
python run_integration_test.py

前提条件：
1. 后端服务运行在 http://localhost:8000
2. Redis服务运行在 localhost:6379
3. 已安装必要的依赖包
"""

import sys
import subprocess
import asyncio
from pathlib import Path

def check_dependencies():
    """检查依赖包"""
    required_packages = [
        'aiohttp',
        'websockets', 
        'redis'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ 缺少依赖包: {', '.join(missing_packages)}")
        print("请安装依赖包:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True

def check_services():
    """检查服务状态"""
    import socket
    
    services = [
        ("后端服务", "localhost", 8000),
        ("Redis服务", "localhost", 6379)
    ]
    
    for service_name, host, port in services:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        
        try:
            result = sock.connect_ex((host, port))
            if result == 0:
                print(f"✅ {service_name} ({host}:{port}) 可访问")
            else:
                print(f"❌ {service_name} ({host}:{port}) 不可访问")
                print(f"   请确保{service_name}正在运行")
                return False
        except Exception as e:
            print(f"❌ 检查{service_name}时出错: {e}")
            return False
        finally:
            sock.close()
    
    return True

async def main():
    """主函数"""
    print("🔍 VTOX 集群-后端集成测试")
    print("="*50)
    
    # 检查依赖
    print("📦 检查依赖包...")
    if not check_dependencies():
        return
    
    # 检查服务
    print("\n🌐 检查服务状态...")
    if not check_services():
        print("\n💡 启动建议:")
        print("1. 启动后端服务: cd backend && python run.py")
        print("2. 启动Redis服务: redis-server")
        return
    
    print("\n🚀 开始运行集成测试...")
    
    # 导入并运行测试
    try:
        sys.path.append(str(Path(__file__).parent))
        from tests.test_cluster_backend_integration import ClusterBackendTester
        
        tester = ClusterBackendTester()
        await tester.run_all_tests()
        
    except ImportError as e:
        print(f"❌ 导入测试模块失败: {e}")
    except Exception as e:
        print(f"❌ 测试执行失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())