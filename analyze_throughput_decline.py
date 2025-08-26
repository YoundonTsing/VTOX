#!/usr/bin/env python3
"""
分析吞吐量逐步递减的原因
重点分析方法1中的新鲜度因子计算逻辑
"""
import asyncio
import redis.asyncio as redis
import time
import requests
import json

async def analyze_performance_metrics_freshness():
    """分析performance_metrics数据的新鲜度计算"""
    print("🔍 分析performance_metrics数据新鲜度...")
    
    try:
        redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
        await redis_client.ping()
        
        # 获取最近的performance_metrics数据
        recent_metrics = await redis_client.xrevrange("performance_metrics", count=10)
        
        if recent_metrics:
            current_time_ms = int(time.time() * 1000)
            
            print(f"📊 Performance Metrics分析:")
            print(f"  当前时间戳: {current_time_ms}")
            print(f"  数据条数: {len(recent_metrics)}")
            
            for i, (message_id, fields) in enumerate(recent_metrics[:3]):
                metric_timestamp = int(message_id.split('-')[0])
                age_minutes = (current_time_ms - metric_timestamp) / 60000
                
                print(f"  消息{i+1}: ID={message_id}")
                print(f"    时间戳: {metric_timestamp}")
                print(f"    年龄: {age_minutes:.2f}分钟前")
                
                # 计算新鲜度因子
                if age_minutes < 30:
                    freshness_factor = max(0.1, 1.0 - (age_minutes / 30))
                    base_throughput = len(recent_metrics) * 6.0
                    final_throughput = base_throughput * freshness_factor
                    
                    print(f"    新鲜度因子: {freshness_factor:.4f}")
                    print(f"    基础吞吐量: {base_throughput} msg/min")
                    print(f"    最终吞吐量: {final_throughput:.2f} msg/min")
                    break
                else:
                    print(f"    数据过旧，不使用")
        else:
            print("❌ 没有找到performance_metrics数据")
        
        await redis_client.aclose()
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")

def simulate_freshness_decline():
    """模拟新鲜度因子随时间的变化"""
    print("\n📈 模拟新鲜度因子随时间变化:")
    print("时间(分钟前) | 新鲜度因子 | 基础吞吐量 | 最终吞吐量")
    print("-" * 55)
    
    base_throughput = 60.0  # 10条记录 × 6.0
    
    for age_minutes in [0, 2, 5, 10, 15, 20, 25, 29, 30, 35]:
        if age_minutes < 30:
            freshness_factor = max(0.1, 1.0 - (age_minutes / 30))
            final_throughput = base_throughput * freshness_factor
            print(f"{age_minutes:11.1f} | {freshness_factor:10.4f} | {base_throughput:10.1f} | {final_throughput:10.2f}")
        else:
            print(f"{age_minutes:11.1f} | {'N/A':>10} | {'N/A':>10} | {'跳过方法1':>10}")

async def test_multiple_api_calls():
    """连续多次调用API，观察递减趋势"""
    print("\n🔄 连续API调用测试:")
    
    results = []
    
    for i in range(5):
        print(f"\n第{i+1}次调用:")
        
        try:
            response = requests.get(
                'http://localhost:8000/api/v1/cluster/status',
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    throughput = data['data']['performance_metrics']['throughput']
                    results.append(throughput)
                    print(f"  吞吐量: {throughput} msg/s")
                else:
                    print(f"  API错误: {data.get('message')}")
            else:
                print(f"  HTTP错误: {response.status_code}")
                
        except Exception as e:
            print(f"  请求失败: {e}")
        
        # 等待3秒再调用下一次
        if i < 4:
            await asyncio.sleep(3)
    
    print("\n📊 递减趋势分析:")
    if len(results) >= 2:
        for i in range(1, len(results)):
            change = results[i] - results[i-1]
            change_percent = (change / results[i-1]) * 100 if results[i-1] != 0 else 0
            print(f"  第{i}→{i+1}次: {results[i-1]:.1f} → {results[i]:.1f} (变化: {change:+.1f}, {change_percent:+.2f}%)")

def calculate_expected_decline():
    """计算预期的递减模式"""
    print("\n🧮 理论递减计算:")
    
    # 假设数据年龄在测试期间的变化
    initial_age = 25  # 假设数据已经25分钟前
    base_throughput = 60.0
    
    print("时间间隔 | 数据年龄 | 新鲜度因子 | 预期吞吐量")
    print("-" * 50)
    
    for interval in [0, 3, 6, 9, 12]:  # 每3秒增加
        current_age = initial_age + (interval / 60)  # 转换为分钟
        
        if current_age < 30:
            freshness_factor = max(0.1, 1.0 - (current_age / 30))
            expected_throughput = base_throughput * freshness_factor
            print(f"{interval:8}秒 | {current_age:7.2f}分 | {freshness_factor:10.4f} | {expected_throughput:10.2f}")
        else:
            print(f"{interval:8}秒 | {current_age:7.2f}分 | {'过期':>10} | {'跳过':>10}")

async def main():
    print("🔬 吞吐量递减原因分析")
    print("=" * 50)
    
    # 分析1: 检查performance_metrics数据新鲜度
    await analyze_performance_metrics_freshness()
    
    # 分析2: 模拟新鲜度因子变化
    simulate_freshness_decline()
    
    # 分析3: 理论递减计算
    calculate_expected_decline()
    
    # 分析4: 实际API测试
    await test_multiple_api_calls()
    
    print("\n🎯 结论分析:")
    print("1. 如果使用方法1(performance_metrics)，递减是由于新鲜度因子随时间降低")
    print("2. 新鲜度因子公式: max(0.1, 1.0 - (age_minutes / 30))")
    print("3. 数据越老，新鲜度因子越小，最终吞吐量越低")
    print("4. 当数据超过30分钟时，系统会跳过方法1，使用方法2或方法3")
    print("5. 如果看到平滑递减，说明方法1的新鲜度调整机制正在工作")

if __name__ == "__main__":
    asyncio.run(main())