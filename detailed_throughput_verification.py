#!/usr/bin/env python3
"""
验证吞吐量多层次计算逻辑
测试方法1、方法2、方法3的工作情况
"""
import requests
import asyncio
import redis.asyncio as redis
import time
import json

async def check_backend_logs():
    """检查后端日志中的详细计算信息"""
    print("📋 提示: 请检查后端日志中的以下信息:")
    print("   📊 [方法1] performance_metrics数据检查:")
    print("   🔍 [方法2] Stream活跃度计算:")
    print("   📊 [方法3] 动态估算或固定估算:")
    print("   📊 [API DEBUG] 最终统计数据:")

def analyze_results(data):
    """分析API返回结果"""
    if not data or data.get('status') != 'success':
        print("❌ API调用失败")
        return False
    
    perf = data['data'].get('performance_metrics', {})
    debug = data['data'].get('debug_info', {})
    
    throughput = perf.get('throughput', 0)
    latency = perf.get('latency', 0) 
    queue_length = perf.get('queue_length', 0)
    
    total_consumers = debug.get('total_consumers', 0)
    healthy_workers = debug.get('healthy_workers', 0)
    warning_workers = debug.get('warning_workers', 0)
    
    print(f"📊 详细分析:")
    print(f"  吞吐量: {throughput} msg/s")
    print(f"  延迟: {latency}ms") 
    print(f"  队列长度: {queue_length}")
    print(f"  消费者总数: {total_consumers}")
    print(f"  健康消费者: {healthy_workers}")
    print(f"  警告消费者: {warning_workers}")
    
    # 分析使用的计算方法
    if throughput == total_consumers * 7.1:
        print(f"🔍 计算方法: 可能是方法3固定估算 ({total_consumers} × 7.1)")
    elif throughput == 60.0:
        print(f"🔍 计算方法: 可能是方法1的老逻辑 (10 × 6.0)")
    elif 0 < throughput < total_consumers * 12:
        print(f"🔍 计算方法: 可能是方法1新鲜度调整或方法2活跃度计算")
    else:
        print(f"🔍 计算方法: 未知逻辑")
    
    # 健康状态分析
    health_ratio = healthy_workers / total_consumers if total_consumers > 0 else 0
    if health_ratio == 1.0:
        print(f"✅ 系统健康: 所有消费者都是健康状态")
    elif health_ratio > 0.8:
        print(f"🟡 系统良好: {health_ratio:.1%}的消费者健康")
    else:
        print(f"🔴 系统警告: 只有{health_ratio:.1%}的消费者健康")
    
    return True

async def add_burst_data():
    """添加一批数据来测试响应"""
    print("🚀 添加大量数据测试...")
    
    try:
        redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
        await redis_client.ping()
        
        # 添加更多数据到多个流
        streams = ["fault_diagnosis_results", "vehicle_health_assessments"]
        
        for batch in range(5):
            for stream in streams:
                for i in range(3):
                    await redis_client.xadd(
                        stream,
                        {
                            "vehicle_id": f"batch_{batch}_vehicle_{i}",
                            "timestamp": int(time.time() * 1000),
                            "test_batch": f"burst_test_{batch}",
                            "score": f"0.{batch}",
                            "batch_id": batch
                        }
                    )
            print(f"  ✅ 添加了批次{batch+1}/5")
            await asyncio.sleep(0.2)
        
        await redis_client.aclose()
        print("✅ 大量数据添加完成")
        
    except Exception as e:
        print(f"❌ 添加数据失败: {e}")

def test_api_detailed():
    """详细测试API"""
    try:
        response = requests.get(
            'http://localhost:8000/api/v1/cluster/status',
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            return analyze_results(data)
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False

async def main():
    print("🧪 吞吐量多层次计算验证")
    print("=" * 50)
    
    # 测试1: 基准状态
    print("\n1️⃣ 基准状态测试:")
    test_api_detailed()
    
    await check_backend_logs()
    
    # 测试2: 添加少量数据
    print("\n2️⃣ 添加少量数据测试:")
    redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
    try:
        for i in range(2):
            await redis_client.xadd(
                "fault_diagnosis_results",
                {
                    "vehicle_id": f"light_test_{i}",
                    "timestamp": int(time.time() * 1000),
                    "score": "0.15"
                }
            )
        await redis_client.aclose()
        print("✅ 添加了2条轻量数据")
    except Exception as e:
        print(f"❌ 添加数据失败: {e}")
    
    await asyncio.sleep(1)
    test_api_detailed()
    
    # 测试3: 添加大量数据
    print("\n3️⃣ 大量数据测试:")
    await add_burst_data()
    
    await asyncio.sleep(2)
    test_api_detailed()
    
    # 测试4: 等待一段时间后再测试
    print("\n4️⃣ 延迟测试 (等待5秒):")
    await asyncio.sleep(5)
    test_api_detailed()
    
    print("\n🎯 总结:")
    print("1. 如果吞吐量有变化，说明多层次计算逻辑工作正常")
    print("2. 如果数值在合理范围内，说明新鲜度检查有效")
    print("3. 如果系统健康状态良好，说明消费者状态检测正确")
    print("4. 请查看后端日志了解具体使用了哪种计算方法")

if __name__ == "__main__":
    asyncio.run(main())