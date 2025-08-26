#!/usr/bin/env python3
"""
快速诊断消费者周期性闲置问题
"""
import asyncio
import redis.asyncio as redis
import time
from datetime import datetime

async def quick_diagnosis():
    """快速诊断当前状态"""
    print("🚨 消费者周期性闲置快速诊断")
    print("=" * 60)
    
    try:
        redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
        await redis_client.ping()
        
        current_time = int(time.time() * 1000)
        
        # 1. 检查数据生产状态
        print("📊 数据生产状态检查:")
        try:
            stream_info = await redis_client.xinfo_stream("motor_raw_data")
            length = stream_info.get('length', 0)
            
            if length > 0:
                # 检查最新几条消息的时间
                latest_messages = await redis_client.xrevrange("motor_raw_data", count=3)
                print(f"  总消息数: {length}")
                
                for i, (msg_id, fields) in enumerate(latest_messages):
                    timestamp_ms = int(msg_id.split('-')[0])
                    age_minutes = (current_time - timestamp_ms) / 60000
                    print(f"  最新消息{i+1}: {age_minutes:.1f}分钟前")
                
                # 检查最近5分钟的新消息
                five_min_ago = current_time - 300000
                recent_messages = await redis_client.xrange(
                    "motor_raw_data", 
                    min=f"{five_min_ago}-0", 
                    max="+"
                )
                print(f"  最近5分钟新消息: {len(recent_messages)}条")
                
                if len(recent_messages) == 0:
                    print("  🚨 关键问题: 最近5分钟没有新数据！")
                    print("  原因: 数据生产者已停止工作")
                else:
                    print(f"  ✅ 数据生产正常: 每分钟约{len(recent_messages)/5:.1f}条")
                    
        except Exception as e:
            print(f"  ❌ 检查失败: {e}")
        
        # 2. 检查消费者处理状态
        print(f"\n👥 消费者处理状态:")
        try:
            groups = await redis_client.xinfo_groups("motor_raw_data")
            
            total_pending = 0
            active_consumers = 0
            
            for group in groups:
                group_name = group['name']
                pending = group['pending']
                total_pending += pending
                
                if pending > 0:
                    print(f"  📦 {group_name}: {pending}条待处理")
                
                consumers = await redis_client.xinfo_consumers("motor_raw_data", group_name)
                for consumer in consumers:
                    idle_ms = consumer['idle']
                    idle_minutes = idle_ms / 60000
                    
                    if idle_minutes < 5:
                        active_consumers += 1
                        status = "✅ 活跃"
                    else:
                        status = "❌ 闲置"
                    
                    print(f"    {status} {consumer['name']}: {idle_minutes:.1f}分钟")
            
            print(f"\n📈 处理统计:")
            print(f"  总待处理: {total_pending}条")
            print(f"  活跃消费者: {active_consumers}个")
            
            if total_pending > 0 and active_consumers == 0:
                print("  🚨 严重问题: 有待处理消息但没有活跃消费者!")
                
        except Exception as e:
            print(f"  ❌ 检查失败: {e}")
        
        # 3. 检查下游处理情况
        print(f"\n⬇️ 下游处理状态:")
        downstream_streams = [
            ("fault_diagnosis_results", "故障诊断结果"),
            ("vehicle_health_assessments", "健康评估结果")
        ]
        
        for stream_name, description in downstream_streams:
            try:
                stream_info = await redis_client.xinfo_stream(stream_name)
                length = stream_info.get('length', 0)
                
                if length > 0:
                    latest = await redis_client.xrevrange(stream_name, count=1)
                    if latest:
                        latest_id = latest[0][0]
                        timestamp_ms = int(latest_id.split('-')[0])
                        age_minutes = (current_time - timestamp_ms) / 60000
                        
                        status_icon = "✅" if age_minutes < 3 else "⚠️" if age_minutes < 10 else "❌"
                        print(f"  {status_icon} {description}: {length}条, 最新{age_minutes:.1f}分钟前")
                    else:
                        print(f"  ❌ {description}: {length}条, 无法获取时间")
                else:
                    print(f"  ❌ {description}: 无数据")
                    
            except Exception as e:
                print(f"  ❌ {description}检查失败: {e}")
        
        await redis_client.aclose()
        
    except Exception as e:
        print(f"❌ 诊断失败: {e}")

async def suggest_immediate_fixes():
    """建议立即修复方案"""
    print(f"\n🛠️ 立即修复建议:")
    print("=" * 60)
    
    print("1. 🔄 重启数据生产者:")
    print("   - 检查数据模拟器是否还在运行")
    print("   - 重启车辆数据模拟器脚本")
    print("   - 确认数据生产频率设置")
    
    print("\n2. 🚀 重启微服务集群:")
    print("   - 停止当前集群: Ctrl+C")
    print("   - 重新启动: python cluster/start_cluster.py --mode=development")
    print("   - 等待所有服务完全启动")
    
    print("\n3. 📊 调整吞吐量计算:")
    print("   - 降低活跃度判断阈值（从5分钟改为2分钟）")
    print("   - 增加数据刷新频率")
    print("   - 启用自动数据生成")
    
    print("\n4. 🔍 持续监控:")
    print("   - 监控消费者闲置时间变化")
    print("   - 观察吞吐量计算恢复")
    print("   - 检查数据流连续性")

async def main():
    await quick_diagnosis()
    await suggest_immediate_fixes()
    
    print("\n" + "="*60)
    print("🎯 下一步:")
    print("1. 立即检查数据模拟器状态")
    print("2. 如果数据生产停止，重启数据模拟器")
    print("3. 如果数据正常，重启微服务集群")
    print("4. 观察5分钟后的状态变化")

if __name__ == "__main__":
    asyncio.run(main())