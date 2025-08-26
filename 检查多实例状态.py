#!/usr/bin/env python3
"""
🔍 多实例状态检查工具
检查当前运行的车辆模拟器实例状态
"""

import subprocess
import psutil
import json
import time
from datetime import datetime

def check_running_instances():
    """检查运行中的实例"""
    print("🔍 检查运行中的车辆模拟器实例...")
    print("=" * 60)
    
    running_instances = []
    
    # 检查所有Python进程
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time', 'memory_info', 'cpu_percent']):
        try:
            if 'python' in proc.info['name'].lower():
                cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                
                if 'realistic_vehicle_simulator_instance' in cmdline:
                    # 提取实例号
                    instance_id = "unknown"
                    for part in cmdline.split():
                        if 'instance_' in part:
                            instance_id = part.split('instance_')[1].split('.')[0]
                            break
                    
                    running_time = time.time() - proc.info['create_time']
                    memory_mb = proc.info['memory_info'].rss / 1024 / 1024
                    
                    instance_info = {
                        'instance_id': instance_id,
                        'pid': proc.info['pid'],
                        'running_time_seconds': running_time,
                        'memory_mb': memory_mb,
                        'cpu_percent': proc.info['cpu_percent'],
                        'status': 'running'
                    }
                    
                    running_instances.append(instance_info)
                    
                    print(f"实例 {instance_id}:")
                    print(f"  PID: {proc.info['pid']}")
                    print(f"  运行时间: {running_time/60:.1f} 分钟")
                    print(f"  内存使用: {memory_mb:.1f} MB")
                    print(f"  CPU: {proc.info['cpu_percent']:.1f}%")
                    print()
                    
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    
    print(f"📊 总计运行实例: {len(running_instances)} 个")
    return running_instances

def check_system_resources():
    """检查系统资源"""
    print("\n💻 系统资源使用情况:")
    print("=" * 60)
    
    # CPU
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_count = psutil.cpu_count()
    print(f"CPU: {cpu_percent:.1f}% (核心数: {cpu_count})")
    
    # 内存
    memory = psutil.virtual_memory()
    print(f"内存: {memory.percent:.1f}% ({memory.used/1024/1024/1024:.1f}GB / {memory.total/1024/1024/1024:.1f}GB)")
    
    # 网络连接到API
    connections = 0
    for conn in psutil.net_connections():
        if conn.laddr and conn.laddr.port == 8000:
            connections += 1
    print(f"API连接数: {connections}")
    
    return {
        'cpu_percent': cpu_percent,
        'memory_percent': memory.percent,
        'memory_used_gb': memory.used/1024/1024/1024,
        'api_connections': connections
    }

def check_log_files():
    """检查日志文件"""
    print("\n📋 检查日志文件:")
    print("=" * 60)
    
    import os
    import glob
    
    # 主日志
    if os.path.exists('multi_instance_simulator.log'):
        size = os.path.getsize('multi_instance_simulator.log') / 1024
        print(f"主日志: multi_instance_simulator.log ({size:.1f} KB)")
    
    # 实例日志
    instance_logs = glob.glob('realistic_simulator_instance_*.log')
    print(f"实例日志文件数: {len(instance_logs)}")
    
    for log_file in instance_logs[:5]:  # 只显示前5个
        size = os.path.getsize(log_file) / 1024
        print(f"  {log_file} ({size:.1f} KB)")
    
    if len(instance_logs) > 5:
        print(f"  ... 还有 {len(instance_logs) - 5} 个日志文件")

def analyze_issues(instances, resources):
    """分析问题"""
    print("\n🔍 问题分析:")
    print("=" * 60)
    
    issues = []
    
    # 检查实例数量
    expected_instances = 10  # 500辆车 / 50辆每实例 = 10个实例
    actual_instances = len(instances)
    
    if actual_instances < expected_instances:
        issues.append(f"实例数不足: 期望{expected_instances}个，实际{actual_instances}个")
    
    # 检查资源使用
    if resources['memory_percent'] > 90:
        issues.append("内存使用率过高 (>90%)")
    
    if resources['cpu_percent'] > 90:
        issues.append("CPU使用率过高 (>90%)")
    
    # 检查单个实例资源
    for instance in instances:
        if instance['memory_mb'] > 1000:  # 超过1GB
            issues.append(f"实例{instance['instance_id']}内存使用异常: {instance['memory_mb']:.1f}MB")
    
    if issues:
        print("发现的问题:")
        for issue in issues:
            print(f"  ⚠️ {issue}")
    else:
        print("✅ 未发现明显问题")
    
    return issues

def main():
    """主函数"""
    print("""
    🔍 多实例车辆模拟器状态检查工具
    
    检查项目:
    ✓ 运行中的实例数量和状态
    ✓ 系统资源使用情况  
    ✓ 日志文件状态
    ✓ 潜在问题分析
    """)
    
    # 检查实例
    instances = check_running_instances()
    
    # 检查系统资源
    resources = check_system_resources()
    
    # 检查日志
    check_log_files()
    
    # 分析问题
    issues = analyze_issues(instances, resources)
    
    # 生成建议
    print("\n💡 建议:")
    print("=" * 60)
    
    if len(instances) == 0:
        print("  1. 检查是否正确启动了多实例模拟器")
        print("  2. 查看 multi_instance_simulator.log 了解启动失败原因")
    elif len(instances) < 10:
        print("  1. 部分实例启动失败，检查系统资源是否充足")
        print("  2. 增加实例启动间隔时间")
        print("  3. 检查API服务是否正常运行")
    
    if resources['memory_percent'] > 80:
        print("  4. 考虑增加系统内存或减少车辆数量")
    
    if resources['cpu_percent'] > 80:
        print("  5. 考虑增加CPU核心或优化实例配置")
    
    print(f"\n📈 预期车辆数: {len(instances) * 50} 辆 (基于 {len(instances)} 个实例)")

if __name__ == "__main__":
    main() 