#!/usr/bin/env python3
"""
分析Redis Stream数据流，找出消费者闲置的原因
"""
import asyncio
import redis.asyncio as redis
import time
from datetime import datetime

async def analyze_stream_data_flow():
    """分析Stream数据流"""
    print("🔍 分析Redis Stream数据流...")
    print("=" * 60)
    
    try:
        redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
        await redis_client.ping()
        print("✅ Redis连接成功")
        
        # 检查所有相关的Stream
        streams = [
            "motor_raw_data",
            "fault_diagnosis_results", 
            "vehicle_health_assessments",
            "performance_metrics",
            "system_alerts"
        ]
        
        current_time = int(time.time() * 1000)
        
        for stream_name in streams:
            print(f"\n📊 分析Stream: {stream_name}")
            print("-" * 40)
            
            try:
                # 获取Stream基本信息
                stream_info = await redis_client.xinfo_stream(stream_name)
                length = stream_info.get('length', 0)
                print(f"  消息总数: {length}")
                
                if length > 0:
                    # 获取最新消息
                    latest_messages = await redis_client.xrevrange(stream_name, count=3)
                    if latest_messages:
                        print(f"  最新3条消息:")
                        for i, (msg_id, fields) in enumerate(latest_messages):
                            timestamp_ms = int(msg_id.split('-')[0])
                            age_minutes = (current_time - timestamp_ms) / 60000
                            print(f"    {i+1}. ID: {msg_id}")
                            print(f"       时间: {age_minutes:.1f}分钟前")
                            print(f"       字段: {dict(fields) if fields else '无'}")
                    
                    # 检查最近1小时的消息数量
                    one_hour_ago = current_time - 3600000  # 1小时前
                    recent_messages = await redis_client.xrange(
                        stream_name, 
                        min=f"{one_hour_ago}-0", 
                        max="+"
                    )
                    print(f"  最近1小时新消息: {len(recent_messages)}条")
                    
                    # 检查消费者组
                    try:
                        groups = await redis_client.xinfo_groups(stream_name)
                        print(f"  消费者组数量: {len(groups)}")
                        
                        for group in groups:
                            group_name = group['name']
                            pending = group['pending']
                            print(f"    组 {group_name}: 待处理 {pending}条")
                            
                            # 检查组内消费者
                            try:
                                consumers = await redis_client.xinfo_consumers(stream_name, group_name)
                                for consumer in consumers:
                                    consumer_name = consumer['name']
                                    idle_ms = consumer['idle']
                                    pending_count = consumer['pending']
                                    idle_minutes = idle_ms / 60000
                                    print(f"      消费者 {consumer_name}: 闲置 {idle_minutes:.1f}分钟, 待处理 {pending_count}条")
                            except Exception as e:
                                print(f"      获取消费者信息失败: {e}")
                                
                    except Exception as e:
                        print(f"  获取消费者组失败: {e}")
                else:
                    print(f"  ⚠️ Stream为空!")
                    
            except Exception as e:
                print(f"  ❌ 分析失败: {e}")
        
        # 总结分析
        print(f"\n🎯 数据流分析总结:")
        print("=" * 60)
        
        # 检查是否有数据生产者在工作
        motor_data_info = await redis_client.xinfo_stream("motor_raw_data")
        motor_data_length = motor_data_info.get('length', 0)
        
        if motor_data_length == 0:
            print("❌ 问题诊断: motor_raw_data Stream为空")
            print("   可能原因:")
            print("   1. 数据生产者（数据模拟器）未启动")
            print("   2. 数据上传程序未运行")
            print("   3. 数据源配置问题")
            print("\n💡 建议解决方案:")
            print("   - 检查是否启动了数据模拟器")
            print("   - 运行车辆数据模拟器脚本")
            print("   - 检查数据源配置")
        else:
            # 检查最新数据的时间
            latest_motor_data = await redis_client.xrevrange("motor_raw_data", count=1)
            if latest_motor_data:
                latest_id = latest_motor_data[0][0]
                timestamp_ms = int(latest_id.split('-')[0])
                age_minutes = (current_time - timestamp_ms) / 60000
                
                if age_minutes > 10:
                    print(f"⚠️ 问题诊断: 最新数据过旧({age_minutes:.1f}分钟前)")
                    print("   可能原因:")
                    print("   1. 数据生产者已停止")
                    print("   2. 数据生产频率过低")
                    print("\n💡 建议解决方案:")
                    print("   - 重启数据模拟器")
                    print("   - 增加数据生产频率")
                else:
                    print(f"✅ 数据流正常: 最新数据 {age_minutes:.1f}分钟前")
                    print("   消费者闲置可能是由于:")
                    print("   1. 消费速度过快，已处理完所有数据")
                    print("   2. 消费者组配置问题")
                    print("   3. 批处理间隔设置")
        
        await redis_client.close()
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")

async def suggest_solutions():
    """建议解决方案"""
    print(f"\n🚀 建议的解决方案:")
    print("=" * 60)
    
    print("1. 检查数据生产者状态:")
    print("   - 确认车辆数据模拟器是否在运行")
    print("   - 检查数据上传频率设置")
    print("   - 验证Redis连接配置")
    
    print("\n2. 重启相关服务:")
    print("   - 重启数据模拟器")
    print("   - 重启微服务集群")
    print("   - 清理Redis数据并重新开始")
    
    print("\n3. 调整系统参数:")
    print("   - 如果这是正常的批处理间隔，可以调整健康判断阈值")
    print("   - 增加数据生产频率")
    print("   - 优化消费者处理逻辑")
    
    print("\n4. 临时验证修复效果:")
    print("   - 手动添加一些测试数据到motor_raw_data")
    print("   - 观察消费者是否开始处理")
    print("   - 验证吞吐量计算是否正确响应")

async def main():
    await analyze_stream_data_flow()
    await suggest_solutions()

if __name__ == "__main__":
    asyncio.run(main())