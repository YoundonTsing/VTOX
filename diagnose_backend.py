#!/usr/bin/env python3
"""
后端服务快速诊断脚本
检查服务状态和可能的阻塞问题
"""
import socket
import subprocess
import time
import sys

def check_port_status(host='localhost', port=8000):
    """检查端口是否被占用"""
    print(f"🔍 检查端口 {host}:{port} 状态...")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print(f"  ✅ 端口 {port} 已被占用（服务可能正在运行）")
            return True
        else:
            print(f"  ❌ 端口 {port} 未被占用（服务未启动）")
            return False
    except Exception as e:
        print(f"  ❌ 检查端口失败: {e}")
        return False

def check_running_processes():
    """检查Python相关进程"""
    print(f"\n🔍 检查正在运行的Python进程...")
    
    try:
        # Windows系统
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV"],
            capture_output=True,
            text=True,
            shell=True
        )
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:  # 有标题行
                print(f"  发现 {len(lines)-1} 个Python进程:")
                for line in lines[1:]:  # 跳过标题行
                    parts = line.replace('"', '').split(',')
                    if len(parts) >= 2:
                        print(f"    - {parts[0]} (PID: {parts[1]})")
                return True
            else:
                print(f"  ❌ 没有发现Python进程")
                return False
        else:
            print(f"  ❌ 无法检查进程: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"  ❌ 检查进程失败: {e}")
        return False

def check_redis_status():
    """检查Redis服务状态"""
    print(f"\n🔍 检查Redis服务状态...")
    
    try:
        result = subprocess.run(
            ["redis-cli", "ping"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and "PONG" in result.stdout:
            print(f"  ✅ Redis服务正常运行")
            return True
        else:
            print(f"  ❌ Redis服务未响应")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"  ❌ Redis服务响应超时")
        return False
    except FileNotFoundError:
        print(f"  ❌ redis-cli未找到，Redis可能未安装")
        return False
    except Exception as e:
        print(f"  ❌ 检查Redis失败: {e}")
        return False

def show_startup_suggestions():
    """显示启动建议"""
    print(f"\n💡 启动建议:")
    print(f"=" * 50)
    
    print(f"1. 🚀 启动后端服务:")
    print(f"   cd backend")
    print(f"   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
    
    print(f"\n2. 🔍 如果启动卡住，检查：")
    print(f"   - Redis服务是否正常运行")
    print(f"   - 端口8000是否被其他程序占用")
    print(f"   - 分布式集群是否被意外启用")
    
    print(f"\n3. 🛠️ 故障排除步骤:")
    print(f"   - 重启Redis服务")
    print(f"   - 杀死所有Python进程后重新启动")
    print(f"   - 检查backend目录下的启动日志")

def check_backend_directory():
    """检查backend目录结构"""
    print(f"\n🔍 检查backend目录结构...")
    
    import os
    backend_path = "backend"
    
    if not os.path.exists(backend_path):
        print(f"  ❌ backend目录不存在")
        return False
    
    required_files = [
        "app/main.py",
        "app/__init__.py",
        "app/routers/auth.py",
        "app/core/config.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        full_path = os.path.join(backend_path, file_path)
        if os.path.exists(full_path):
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} 缺失")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"  ⚠️ 发现 {len(missing_files)} 个缺失文件，可能影响启动")
        return False
    else:
        print(f"  ✅ 核心文件完整")
        return True

def main():
    print("🚨 VTOX后端服务诊断工具")
    print("=" * 50)
    print("目标: 诊断后端服务无法响应的原因")
    print()
    
    # 检查1: 端口状态
    port_occupied = check_port_status()
    
    # 检查2: Python进程
    python_running = check_running_processes()
    
    # 检查3: Redis状态
    redis_ok = check_redis_status()
    
    # 检查4: 目录结构
    backend_ok = check_backend_directory()
    
    # 分析结果
    print(f"\n" + "="*50)
    print("🎯 诊断结果分析:")
    
    if port_occupied and python_running:
        print("🔄 服务可能正在运行但响应缓慢")
        print("   可能原因:")
        print("   - 分布式集群启动过程阻塞")
        print("   - Redis连接问题")
        print("   - 消费者循环启动问题")
        print("\n🛠️ 建议操作:")
        print("   1. Ctrl+C 强制停止当前后端进程")
        print("   2. 确认分布式集群已禁用")
        print("   3. 重新启动后端服务")
        
    elif not port_occupied and not python_running:
        print("🚫 后端服务未启动")
        print("\n🛠️ 建议操作:")
        if redis_ok and backend_ok:
            print("   环境检查正常，可以直接启动服务")
        else:
            if not redis_ok:
                print("   1. 首先启动Redis服务")
            if not backend_ok:
                print("   2. 检查backend目录完整性")
            print("   3. 然后启动后端服务")
    
    elif port_occupied and not python_running:
        print("⚠️ 端口被非Python进程占用")
        print("   检查哪个程序占用了8000端口")
        
    else:
        print("❓ 状态异常，建议手动检查")
    
    # 显示启动建议
    show_startup_suggestions()
    
    print(f"\n🎯 快速修复命令:")
    print(f"   # 停止所有Python进程（Windows）")
    print(f"   taskkill /F /IM python.exe")
    print(f"   ")
    print(f"   # 重新启动后端")
    print(f"   cd backend")
    print(f"   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")

if __name__ == "__main__":
    main()