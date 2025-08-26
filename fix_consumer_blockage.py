#!/usr/bin/env python3
"""
修复消费者阻塞问题的脚本
重启服务并检查状态
"""
import asyncio
import redis.asyncio as redis
import subprocess
import time
import os
from datetime import datetime

async def check_services_status():
    """检查微服务集群状态"""
    print("🔍 检查微服务集群状态...")
    print("=" * 50)
    
    # 检查可能的微服务进程
    services_to_check = [
        "python",
        "java",
        "node",
        "microservice",
        "diagnosis"
    ]
    
    try:
        # 使用tasklist检查Windows进程
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq python.exe"],
            capture_output=True,
            text=True,
            shell=True
        )
        
        if result.returncode == 0:
            python_processes = result.stdout
            if "python.exe" in python_processes:
                print("✅ 发现Python进程正在运行")
                print(f"进程信息:\n{python_processes}")
            else:
                print("❌ 没有发现Python微服务进程")
        else:
            print(f"❌ 检查进程失败: {result.stderr}")
            
    except Exception as e:
        print(f"❌ 检查服务状态失败: {e}")

async def reset_consumer_groups():
    """重置消费者组状态"""
    print("\n🔄 重置消费者组状态...")
    print("=" * 50)
    
    try:
        redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
        await redis_client.ping()
        
        # 需要重置的消费者组
        problematic_groups = [
            ("motor_raw_data", "bearing_diagnosis_group"),
            ("motor_raw_data", "broken_bar_diagnosis_group"), 
            ("motor_raw_data", "eccentricity_diagnosis_group"),
            ("motor_raw_data", "insulation_diagnosis_group"),
            ("motor_raw_data", "turn_fault_diagnosis_group"),
            ("fault_diagnosis_results", "fault_results_group"),
            ("fault_diagnosis_results", "result_aggregation_group"),
            ("vehicle_health_assessments", "health_group")
        ]
        
        for stream_name, group_name in problematic_groups:
            try:
                # 检查消费者组是否存在
                groups = await redis_client.xinfo_groups(stream_name)
                group_exists = any(g['name'] == group_name for g in groups)
                
                if group_exists:
                    print(f"🔧 重置 {stream_name} -> {group_name}")
                    
                    # 获取消费者列表
                    consumers = await redis_client.xinfo_consumers(stream_name, group_name)
                    
                    # 删除所有消费者
                    for consumer in consumers:
                        consumer_name = consumer['name']
                        try:
                            await redis_client.xgroup_delconsumer(stream_name, group_name, consumer_name)
                            print(f"  ✅ 删除消费者: {consumer_name}")
                        except Exception as e:
                            print(f"  ⚠️ 删除消费者失败: {consumer_name} - {e}")
                    
                    # 可选：重置消费者组到最新位置
                    # await redis_client.xgroup_setid(stream_name, group_name, '$')
                    # print(f"  ✅ 重置组位置到最新")
                    
                else:
                    print(f"⚠️ 消费者组不存在: {stream_name} -> {group_name}")
                    
            except Exception as e:
                print(f"❌ 重置 {stream_name} -> {group_name} 失败: {e}")
        
        await redis_client.aclose()
        print("\n✅ 消费者组重置完成")
        
    except Exception as e:
        print(f"❌ 重置消费者组失败: {e}")

async def restart_microservices():
    """重启微服务建议"""
    print("\n🚀 微服务重启指南...")
    print("=" * 50)
    
    print("请按以下步骤重启微服务集群:")
    print()
    print("1. 停止现有服务:")
    print("   - 按 Ctrl+C 停止所有正在运行的微服务")
    print("   - 检查任务管理器，结束相关python.exe进程")
    print()
    print("2. 检查启动脚本:")
    print("   - 确认 start_cluster.py 或类似脚本存在")
    print("   - 检查微服务配置文件")
    print()
    print("3. 重新启动:")
    print("   - 运行: python start_cluster.py")
    print("   - 或分别启动各个微服务")
    print()
    print("4. 验证启动:")
    print("   - 检查控制台输出无错误")
    print("   - 等待所有服务完全启动（约30-60秒）")

async def verify_fix():
    """验证修复效果"""
    print("\n✅ 验证修复效果...")
    print("=" * 50)
    
    try:
        redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
        await redis_client.ping()
        
        # 等待一段时间让服务启动
        print("⏳ 等待30秒让服务完全启动...")
        await asyncio.sleep(30)
        
        # 检查新的消费者是否注册
        try:
            groups = await redis_client.xinfo_groups("motor_raw_data")
            print(f"\n📊 motor_raw_data消费者组状态:")
            
            for group in groups:
                group_name = group['name']
                pending = group['pending']
                
                consumers = await redis_client.xinfo_consumers("motor_raw_data", group_name)
                print(f"  组 {group_name}: {len(consumers)}个消费者, {pending}条待处理")
                
                for consumer in consumers:
                    consumer_name = consumer['name']
                    idle_ms = consumer['idle']
                    idle_minutes = idle_ms / 60000
                    
                    if idle_minutes < 2:
                        print(f"    ✅ {consumer_name}: 活跃 ({idle_minutes:.1f}分钟)")
                    else:
                        print(f"    ⚠️ {consumer_name}: 闲置 ({idle_minutes:.1f}分钟)")
                        
        except Exception as e:
            print(f"❌ 检查消费者状态失败: {e}")
        
        await redis_client.aclose()
        
    except Exception as e:
        print(f"❌ 验证失败: {e}")

async def main():
    print("🛠️ 消费者阻塞问题修复工具")
    print("=" * 50)
    print("目标: 修复24分钟前崩溃的故障诊断消费者")
    print()
    
    # 1. 检查服务状态
    await check_services_status()
    
    # 2. 重置消费者组
    await reset_consumer_groups()
    
    # 3. 重启指南
    await restart_microservices()
    
    print("\n" + "="*50)
    print("🎯 下一步操作:")
    print("1. 手动重启微服务集群")
    print("2. 等待服务完全启动")
    print("3. 运行验证脚本检查修复效果")
    print("4. 重新测试吞吐量计算")
    print()
    print("验证命令:")
    print("python fix_consumer_blockage.py --verify")

if __name__ == "__main__":
    import sys
    if "--verify" in sys.argv:
        asyncio.run(verify_fix())
    else:
        asyncio.run(main())