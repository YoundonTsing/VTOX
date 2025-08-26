#!/usr/bin/env python3
"""
数据流量分析脚本
检查50台车并发数据的实际流量和计算公式问题
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
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False

async def analyze_actual_data_flow():
    """分析实际数据流量"""
    print("🚗 50台车数据流量分析")
    print("=" * 60)
    
    try:
        redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
        await redis_client.ping()
        
        current_time = int(time.time() * 1000)
        
        # 分析不同时间窗口的数据量
        time_windows = [
            (60000, "1分钟"),      # 1分钟
            (300000, "5分钟"),     # 5分钟  
            (600000, "10分钟"),    # 10分钟
            (3600000, "1小时")     # 1小时
        ]
        
        print("📊 motor_raw_data 实际流量分析:")
        
        for window_ms, window_name in time_windows:
            window_start = current_time - window_ms
            
            try:
                messages = await redis_client.xrange(
                    "motor_raw_data",
                    min=f"{window_start}-0",
                    max="+"
                )
                
                message_count = len(messages)
                
                # 计算真实吞吐量
                throughput_per_minute = message_count / (window_ms / 60000)
                throughput_per_second = throughput_per_minute / 60
                
                print(f"  {window_name}: {message_count}条消息")
                print(f"    平均: {throughput_per_minute:.1f} msg/min = {throughput_per_second:.1f} msg/s")
                
                # 50台车的预期计算
                if message_count > 0:
                    per_vehicle_rate = throughput_per_second / 50
                    print(f"    每台车: {per_vehicle_rate:.3f} msg/s")
                    
                    # 采样分析前10条消息
                    if window_name == "5分钟" and message_count > 0:
                        print(f"    🔍 最近消息采样分析:")
                        sample_messages = messages[-10:] if len(messages) >= 10 else messages
                        
                        vehicle_ids = set()
                        for msg_id, fields in sample_messages:
                            vehicle_id = fields.get('vehicle_id', 'unknown')
                            vehicle_ids.add(vehicle_id)
                            timestamp_ms = int(msg_id.split('-')[0])
                            age_minutes = (current_time - timestamp_ms) / 60000
                            
                        print(f"      采样10条消息涉及 {len(vehicle_ids)} 台车")
                        print(f"      车辆ID样本: {list(vehicle_ids)[:5]}...")
                        
            except Exception as e:
                print(f"  {window_name}: 分析失败 - {e}")
        
        await redis_client.aclose()
        
    except Exception as e:
        print(f"❌ 数据流量分析失败: {e}")

async def analyze_performance_metrics_formula():
    """分析performance_metrics计算公式问题"""
    print(f"\n🧮 Performance Metrics 计算公式分析")
    print("=" * 60)
    
    if not CONFIG_AVAILABLE:
        print("❌ 配置不可用，无法分析")
        return
    
    try:
        redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
        await redis_client.ping()
        
        config = get_config()
        
        print("📊 配置参数:")
        print(f"  base_throughput_multiplier: {config.base_throughput_multiplier}")
        print(f"  freshness_weight: {config.freshness_weight}")
        print(f"  activity_weight: {config.activity_weight}")
        print(f"  freshness_window_minutes: {config.freshness_window_minutes}")
        
        # 获取performance_metrics数据
        recent_metrics = await redis_client.xrevrange("performance_metrics", count=20)
        print(f"\n📈 Performance Metrics 数据分析:")
        print(f"  最近获取: {len(recent_metrics)}条记录")
        
        if recent_metrics:
            current_time_ms = int(time.time() * 1000)
            
            print(f"\n  最近记录详情:")
            for i, (msg_id, fields) in enumerate(recent_metrics[:5]):
                timestamp_ms = int(msg_id.split('-')[0])
                age_minutes = (current_time_ms - timestamp_ms) / 60000
                processing_time = fields.get("processing_time", "未知")
                throughput = fields.get("throughput", "未知")
                
                print(f"    {i+1}. {age_minutes:.1f}分钟前: throughput={throughput}, processing_time={processing_time}ms")
            
            # 分析公式问题
            print(f"\n🚨 公式问题分析:")
            
            latest_age = (current_time_ms - int(recent_metrics[0][0].split('-')[0])) / 60000
            
            # 当前计算方式
            base_throughput = len(recent_metrics) * config.base_throughput_multiplier  # 这里有问题！
            print(f"  当前计算: base_throughput = {len(recent_metrics)} * {config.base_throughput_multiplier} = {base_throughput}")
            print(f"  🚨 问题1: 基础吞吐量只基于记录数量，不是实际数据流量！")
            
            freshness_factor = config.calculate_freshness_factor(latest_age)
            activity_factor = min(1.5, len(recent_metrics) / 8.0)
            
            print(f"  新鲜度因子: {freshness_factor:.4f}")
            print(f"  活跃度因子: {activity_factor:.4f}")
            
            print(f"\n💡 正确的计算方式应该是:")
            print(f"  1. 基础吞吐量应该基于实际motor_raw_data流量")
            print(f"  2. performance_metrics只是性能统计，不是流量来源")
            print(f"  3. 50台车并发应该产生更高的基础吞吐量")
        
        await redis_client.aclose()
        
    except Exception as e:
        print(f"❌ 公式分析失败: {e}")

async def suggest_formula_fix():
    """建议公式修复方案"""
    print(f"\n🛠️ 公式修复建议")
    print("=" * 60)
    
    print("🚨 发现的关键问题:")
    print("1. base_throughput = 记录数 * multiplier 是错误的")
    print("   - 应该基于实际数据流量，不是performance_metrics记录数")
    print("   - 50台车并发数据应该产生更高的基础值")
    
    print(f"\n💡 建议修复方案:")
    print("方案1: 基于实际流量计算")
    print("  - 获取最近5分钟motor_raw_data的实际消息数")
    print("  - base_throughput = 实际消息数 / 5分钟")
    
    print(f"\n方案2: 基于车辆数量估算")
    print("  - 检测当前活跃车辆数量")
    print("  - base_throughput = 车辆数 * 每车平均频率")
    
    print(f"\n方案3: 混合计算")
    print("  - 结合实际流量和performance_metrics质量")
    print("  - 动态调整multiplier基于车辆规模")
    
    print(f"\n🎯 立即行动:")
    print("1. 修改throughput_config.py中的计算逻辑")
    print("2. 让base_throughput基于实际数据流量")
    print("3. 考虑50台车的并发规模")

async def main():
    await analyze_actual_data_flow()
    await analyze_performance_metrics_formula()
    await suggest_formula_fix()
    
    print(f"\n" + "="*60)
    print("🎯 结论: 计算公式确实有问题！")
    print("base_throughput不应该基于performance_metrics记录数，")
    print("而应该基于motor_raw_data的实际流量。")
    print("50台车并发数据被严重低估了！")

if __name__ == "__main__":
    asyncio.run(main())