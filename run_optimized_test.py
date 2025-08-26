#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VTOX 优化集成测试启动脚本

优化特性：
1. 改进Redis连接配置
2. 增加WebSocket连接超时控制
3. 优化性能基准调整
4. 更详细的错误诊断

使用方法：
python run_optimized_test.py
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
        print("正在自动安装...")
        for package in missing_packages:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
        print("✅ 依赖包安装完成")
    
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
                return False
        except Exception as e:
            print(f"❌ 检查{service_name}时出错: {e}")
            return False
        finally:
            sock.close()
    
    return True

async def run_optimized_tests():
    """运行优化的测试"""
    print("🚀 开始运行优化集成测试...")
    
    # 导入优化的测试器
    sys.path.append(str(Path(__file__).parent))
    
    from tests.test_cluster_backend_integration import ClusterBackendTester
    
    # 创建优化配置的测试器
    tester = ClusterBackendTester()
    
    # 优化Redis连接配置
    tester.redis_url = "redis://localhost:6379/0?socket_timeout=5&socket_connect_timeout=5"
    
    try:
        await tester.run_all_tests()
        print("\n🎯 优化建议:")
        
        # 基于测试结果提供具体建议
        failed_tests = [r for r in tester.test_results if not r.get("success", False)]
        
        if any("WebSocket" in r["test"] for r in failed_tests):
            print("📡 WebSocket问题解决方案:")
            print("   1. 检查后端WebSocket服务是否正确启动")
            print("   2. 确认防火墙没有阻止WebSocket连接")
            print("   3. 尝试重启后端服务")
        
        if any("Redis" in r["test"] for r in failed_tests):
            print("🔴 Redis性能优化建议:")
            print("   1. 检查Redis配置文件中的timeout设置")
            print("   2. 考虑使用Redis连接池")
            print("   3. 检查Redis服务器负载")
        
        if any("阻塞" in r["test"] for r in failed_tests):
            print("⚡ 性能优化建议:")
            print("   1. 检查系统CPU和内存使用率")
            print("   2. 优化后端异步处理逻辑")
            print("   3. 考虑增加Redis连接池大小")
    
    finally:
        await tester.cleanup()

async def main():
    """主函数"""
    print("🔍 VTOX 优化集群-后端集成测试")
    print("="*60)
    
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
        print("3. 确保服务在正确端口运行")
        return
    
    # 运行测试
    await run_optimized_tests()

if __name__ == "__main__":
    asyncio.run(main())