#!/usr/bin/env python3
"""
🔄 重启多实例车辆模拟器
停止当前运行的实例并重新启动，解决实例数不足问题
"""

import os
import sys
import time
import psutil
import subprocess
import asyncio

def stop_all_instances():
    """停止所有实例"""
    print("🛑 停止所有车辆模拟器实例...")
    
    stopped_count = 0
    
    # 停止所有相关进程
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'python' in proc.info['name'].lower():
                cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                
                if 'realistic_vehicle_simulator_instance' in cmdline:
                    print(f"  停止实例 PID: {proc.info['pid']}")
                    proc.terminate()
                    stopped_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    
    # 等待进程结束
    time.sleep(5)
    
    # 强制终止未响应的进程
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'python' in proc.info['name'].lower():
                cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                
                if 'realistic_vehicle_simulator_instance' in cmdline:
                    print(f"  强制终止实例 PID: {proc.info['pid']}")
                    proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    
    print(f"✅ 已停止 {stopped_count} 个实例")

def cleanup_temp_files():
    """清理临时文件"""
    print("🧹 清理临时文件...")
    
    import glob
    
    # 清理实例脚本文件
    script_files = glob.glob('databases/realistic_vehicle_simulator_instance_*.py')
    for file in script_files:
        try:
            os.remove(file)
            print(f"  删除: {file}")
        except:
            pass
    
    # 清理日志文件（可选）
    choice = input("是否清理实例日志文件？(y/N): ").strip().lower()
    if choice == 'y':
        log_files = glob.glob('realistic_simulator_instance_*.log')
        for file in log_files:
            try:
                os.remove(file)
                print(f"  删除日志: {file}")
            except:
                pass

def check_system_resources():
    """检查系统资源"""
    print("💻 检查系统资源...")
    
    # CPU
    cpu_count = psutil.cpu_count()
    cpu_percent = psutil.cpu_percent(interval=1)
    
    # 内存
    memory = psutil.virtual_memory()
    available_gb = memory.available / 1024 / 1024 / 1024
    
    print(f"  CPU: {cpu_count} 核心, 使用率: {cpu_percent:.1f}%")
    print(f"  内存: 可用 {available_gb:.1f}GB")
    
    # 资源建议
    if cpu_count < 6:
        print("  ⚠️ CPU核心数较少，建议减少车辆数量到300辆")
    
    if available_gb < 4:
        print("  ⚠️ 可用内存不足，建议减少车辆数量")
        return False
    
    return True

def restart_with_optimized_settings():
    """使用优化设置重启"""
    print("🚀 使用优化设置重启...")
    
    # 检查系统资源并调整车辆数量
    if not check_system_resources():
        vehicles = 200  # 降低到200辆
        print(f"  📉 基于系统资源，调整为 {vehicles} 辆车")
    else:
        vehicles = 500  # 保持500辆
        print(f"  🎯 启动 {vehicles} 辆车")
    
    # 启动多实例管理器
    try:
        print("  ⏳ 启动多实例管理器...")
        
        # 使用Python子进程启动
        cmd = [sys.executable, "启动多实例车辆模拟器.py"]
        
        # 在后台启动
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        print(f"  ✅ 启动进程 PID: {process.pid}")
        print("  📋 请在新的终端窗口中选择车辆数量")
        print("  📊 使用 'python 检查多实例状态.py' 监控状态")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 启动失败: {e}")
        return False

def main():
    """主函数"""
    print("""
    🔄 多实例车辆模拟器重启工具
    
    功能:
    1. 停止所有运行中的实例
    2. 清理临时文件
    3. 检查系统资源
    4. 使用优化设置重启
    """)
    
    try:
        # 1. 停止所有实例
        stop_all_instances()
        
        # 2. 清理临时文件
        cleanup_temp_files()
        
        # 3. 等待系统稳定
        print("⏳ 等待系统稳定...")
        time.sleep(3)
        
        # 4. 重启
        if restart_with_optimized_settings():
            print("""
            ✅ 重启完成！
            
            下一步:
            1. 在新终端中选择车辆数量
            2. 运行 'python 检查多实例状态.py' 检查状态
            3. 前端界面应该很快显示正确的车辆数
            """)
        else:
            print("❌ 重启失败，请手动启动")
            
    except KeyboardInterrupt:
        print("\n👋 操作已取消")
    except Exception as e:
        print(f"❌ 操作失败: {e}")

if __name__ == "__main__":
    main() 