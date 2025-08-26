#!/usr/bin/env python3
"""
深度诊断吞吐量计算方法1和方法2失效原因
"""
import asyncio
import redis.asyncio as redis
import time
import sys
import os
from datetime import datetime

# 添加backend路径
backend_path = os.path.join(os.path.dirname(__file__), "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

try:
    from app.config.throughput_config import get_config
    from app.services.auto_refresh_service import get_auto_refresh_service
    CONFIG_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ 配置模块导入失败: {e}")
    CONFIG_AVAILABLE = False

async def diagnose_method1():
    """详细诊断方法1失效原因"""
    print("🔍 方法1详细诊断：Performance Metrics流")
    print("=" * 70)
    
    try:
        redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
        await redis_client.ping()
        
        current_time_ms = int(time.time() * 1000)
        
        # 1. 检查配置是否可用
        print("📊 配置检查:")
        if CONFIG_AVAILABLE:
            try:
                config = get_config()
                print(f"  ✅ 配置获取成功")
                print(f"  - 时间窗口: {config.freshness_window_minutes}分钟")
                print(f"  - 最小新鲜度因子: {config.min_freshness_factor}")
                print(f"  - 递减曲线: {config.decay_curve_type}")
                print(f"  - 基础吞吐量乘数: {config.base_throughput_multiplier}")
                print(f"  - 新鲜度权重: {config.freshness_weight}")
                print(f"  - 活跃度权重: {config.activity_weight}")
            except Exception as config_error:
                print(f"  ❌ 配置获取失败: {config_error}")
                return False
        else:
            print(f"  ❌ 配置模块不可用，方法1无法工作")
            return False
        
        # 2. 检查performance_metrics流状态
        print(f"\n📊 Performance Metrics流检查:")
        try:
            stream_info = await redis_client.xinfo_stream("performance_metrics")
            length = stream_info.get('length', 0)
            print(f"  - 总消息数: {length}")
            
            if length == 0:
                print(f"  ❌ 关键问题: performance_metrics流为空!")
                print(f"  原因: 没有性能数据写入或数据已过期清理")
                return False
                
            # 检查最新数据
            recent_metrics = await redis_client.xrevrange("performance_metrics", count=10)
            print(f"  - 获取到最新记录: {len(recent_metrics)}条")
            
            if recent_metrics:
                # 分析最新10条记录
                print(f"\n  📈 最新10条记录分析:")
                for i, (message_id, fields) in enumerate(recent_metrics):
                    timestamp_ms = int(message_id.split('-')[0])
                    age_minutes = (current_time_ms - timestamp_ms) / 60000
                    processing_time = fields.get("processing_time", "未知")
                    
                    status_icon = "✅" if age_minutes < 5 else "⚠️" if age_minutes < 30 else "❌"
                    print(f"    {i+1}. {status_icon} ID: {message_id}")
                    print(f"       时间: {age_minutes:.1f}分钟前")
                    print(f"       处理时间: {processing_time}ms")
                    
                    if i == 0:  # 最新记录
                        latest_age = age_minutes
                
                # 检查数据新鲜度
                print(f"\n  🕒 数据新鲜度检查:")
                print(f"  - 最新数据年龄: {latest_age:.1f}分钟")
                print(f"  - 配置时间窗口: {config.freshness_window_minutes}分钟")
                
                if latest_age < config.freshness_window_minutes:
                    print(f"  ✅ 数据新鲜，满足方法1使用条件")
                    
                    # 模拟方法1计算
                    print(f"\n  🧮 模拟方法1计算:")
                    base_throughput = len(recent_metrics) * config.base_throughput_multiplier
                    freshness_factor = config.calculate_freshness_factor(latest_age)
                    activity_factor = min(1.5, len(recent_metrics) / 8.0)
                    final_factor = (freshness_factor * config.freshness_weight + 
                                  activity_factor * config.activity_weight)
                    throughput_per_minute = base_throughput * final_factor
                    throughput = throughput_per_minute / 60.0
                    
                    print(f"    - 基础吞吐量: {base_throughput:.1f} msg/min")
                    print(f"    - 新鲜度因子: {freshness_factor:.4f}")
                    print(f"    - 活跃度因子: {activity_factor:.4f}")
                    print(f"    - 最终因子: {final_factor:.4f}")
                    print(f"    - 每分钟吞吐量: {throughput_per_minute:.1f} msg/min")
                    print(f"    - 最终吞吐量: {throughput:.1f} msg/s")
                    print(f"  ✅ 方法1应该工作并返回 {throughput:.1f} msg/s")
                    
                    return True
                else:
                    print(f"  ❌ 数据过旧({latest_age:.1f} > {config.freshness_window_minutes}分钟)")
                    print(f"  原因: 自动刷新服务可能未运行或写入频率过低")
                    return False
            else:
                print(f"  ❌ 无法获取最新记录")
                return False
                
        except Exception as e:
            print(f"  ❌ 检查performance_metrics失败: {e}")
            return False
        
        await redis_client.aclose()
        
    except Exception as e:
        print(f"❌ 方法1诊断失败: {e}")
        return False

async def diagnose_method2():
    """详细诊断方法2失效原因"""
    print("\n🔍 方法2详细诊断：Stream活跃度计算")
    print("=" * 70)
    
    try:
        redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
        await redis_client.ping()
        
        current_time_ms = int(time.time() * 1000)
        ten_minutes_ago_ms = current_time_ms - 600000  # 10分钟前
        
        diagnosis_streams = ["fault_diagnosis_results", "vehicle_health_assessments"]
        total_recent_activity = 0
        
        for stream_name in diagnosis_streams:
            print(f"\n📊 检查 {stream_name}:")
            
            try:
                # 检查流基本信息
                stream_info = await redis_client.xinfo_stream(stream_name)
                length = stream_info.get('length', 0)
                print(f"  - 总消息数: {length}")
                
                if length == 0:
                    print(f"  ❌ 流为空，没有诊断结果数据")
                    continue
                
                # 检查最新消息
                latest_messages = await redis_client.xrevrange(stream_name, count=5)
                if latest_messages:
                    print(f"  📈 最新5条消息:")
                    for i, (msg_id, fields) in enumerate(latest_messages):
                        timestamp_ms = int(msg_id.split('-')[0])
                        age_minutes = (current_time_ms - timestamp_ms) / 60000
                        status_icon = "✅" if age_minutes < 5 else "⚠️" if age_minutes < 15 else "❌"
                        print(f"    {i+1}. {status_icon} ID: {msg_id}")
                        print(f"       时间: {age_minutes:.1f}分钟前")
                        print(f"       字段: {dict(fields)}")
                
                # 检查最近10分钟的活动
                recent_messages = await redis_client.xrange(
                    stream_name, 
                    min=f"{ten_minutes_ago_ms}-0", 
                    max="+"
                )
                
                stream_recent_count = len(recent_messages)
                total_recent_activity += stream_recent_count
                
                print(f"  📊 最近10分钟活动: {stream_recent_count}条消息")
                
                if stream_recent_count == 0:
                    print(f"  ❌ 最近10分钟无新消息")
                    print(f"  可能原因:")
                    print(f"    - 故障诊断消费者未处理新数据")
                    print(f"    - 数据处理速度跟不上生产速度")
                    print(f"    - 消费者处理逻辑阻塞")
                else:
                    print(f"  ✅ 有最近活动，方法2数据可用")
                    
            except Exception as e:
                print(f"  ❌ 检查 {stream_name} 失败: {e}")
        
        # 总结方法2状态
        print(f"\n📊 方法2总结:")
        print(f"  - 总活动量: {total_recent_activity}条/10分钟")
        
        if total_recent_activity > 0:
            throughput_per_minute = total_recent_activity / 10.0
            throughput = throughput_per_minute / 60.0
            print(f"  - 计算结果: {throughput_per_minute:.1f} msg/min = {throughput:.1f} msg/s")
            print(f"  ✅ 方法2应该工作并返回 {throughput:.1f} msg/s")
            return True
        else:
            print(f"  ❌ 方法2失效: 最近10分钟无下游活动")
            print(f"  根本原因: 故障诊断消费者没有产生输出")
            return False
        
        await redis_client.aclose()
        
    except Exception as e:
        print(f"❌ 方法2诊断失败: {e}")
        return False

async def diagnose_data_flow():
    """诊断数据流问题"""
    print("\n🔍 数据流问题诊断")
    print("=" * 70)
    
    try:
        redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
        await redis_client.ping()
        
        current_time = int(time.time() * 1000)
        
        # 检查上游数据生产
        print("📊 上游数据生产检查:")
        motor_info = await redis_client.xinfo_stream("motor_raw_data")
        motor_length = motor_info.get('length', 0)
        
        latest_motor = await redis_client.xrevrange("motor_raw_data", count=1)
        if latest_motor:
            latest_id = latest_motor[0][0]
            timestamp_ms = int(latest_id.split('-')[0])
            age_minutes = (current_time - timestamp_ms) / 60000
            print(f"  ✅ motor_raw_data: {motor_length}条消息，最新{age_minutes:.1f}分钟前")
        
        # 检查消费者处理状态
        print(f"\n👥 消费者处理状态:")
        groups = await redis_client.xinfo_groups("motor_raw_data")
        
        total_pending = 0
        processing_consumers = 0
        
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
                    pending_count = consumer['pending']
                    
                    if idle_minutes < 5:
                        processing_consumers += 1
                        status = "✅ 处理中"
                    else:
                        status = "❌ 闲置"
                    
                    print(f"    {status} {consumer['name']}: {idle_minutes:.1f}分钟, {pending_count}条")
        
        print(f"\n🎯 问题根源分析:")
        if motor_length > 0 and age_minutes < 2:
            print(f"  ✅ 数据生产正常")
        else:
            print(f"  ❌ 数据生产异常")
            
        if total_pending > 0:
            print(f"  ⚠️ 有{total_pending}条消息积压")
        else:
            print(f"  ✅ 无消息积压")
            
        if processing_consumers > 0:
            print(f"  ✅ 有{processing_consumers}个消费者在处理")
        else:
            print(f"  ❌ 没有消费者在处理数据")
        
        # 给出具体建议
        print(f"\n💡 建议修复措施:")
        if total_pending > 50:
            print(f"  1. 消费者处理能力不足，考虑增加消费者")
        if processing_consumers == 0:
            print(f"  2. 重启微服务集群恢复消费者处理")
        if motor_length > 0 and total_pending == 0:
            print(f"  3. 检查消费者组配置和读取模式")
        
        await redis_client.aclose()
        
    except Exception as e:
        print(f"❌ 数据流诊断失败: {e}")

async def main():
    print("🔍 吞吐量计算方法1和方法2失效深度诊断")
    print("=" * 70)
    print("目标: 找出为什么系统正常运行但吞吐量计算失效")
    print()
    
    # 诊断方法1
    method1_working = await diagnose_method1()
    
    # 诊断方法2  
    method2_working = await diagnose_method2()
    
    # 诊断数据流
    await diagnose_data_flow()
    
    # 总结
    print("\n" + "="*70)
    print("🎯 诊断总结:")
    print(f"  方法1状态: {'✅ 应该工作' if method1_working else '❌ 失效'}")
    print(f"  方法2状态: {'✅ 应该工作' if method2_working else '❌ 失效'}")
    
    if not method1_working and not method2_working:
        print(f"\n🚨 双重失效原因:")
        print(f"  - 方法1: performance_metrics数据不新鲜或配置问题")
        print(f"  - 方法2: 故障诊断消费者未产生新的下游数据")
        print(f"  - 系统降级到方法3固定估算")
        
        print(f"\n🛠️ 修复建议:")
        print(f"  1. 启动自动刷新服务更新performance_metrics")
        print(f"  2. 检查故障诊断消费者是否正常处理数据")
        print(f"  3. 重启微服务集群确保所有组件正常工作")

if __name__ == "__main__":
    asyncio.run(main())