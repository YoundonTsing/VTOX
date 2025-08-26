#!/usr/bin/env python3
"""
快速测试吞吐量计算改进效果
"""
import requests
import asyncio
import redis.asyncio as redis
import time
import json

async def add_fresh_data():
    """添加新的诊断数据"""
    print("📝 添加新的诊断数据...")
    
    try:
        redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
        await redis_client.ping()
        
        # 添加到诊断结果流
        streams = ["fault_diagnosis_results", "vehicle_health_assessments"]
        
        for i in range(3):
            for stream in streams:
                await redis_client.xadd(
                    stream,
                    {
                        "vehicle_id": f"test_vehicle_{i}",
                        "timestamp": int(time.time() * 1000),
                        "test_data": f"throughput_test_{i}",
                        "score": "0.2"
                    }
                )
            print(f"  ✅ 添加了第{i+1}批数据")
            await asyncio.sleep(0.5)
        
        await redis_client.aclose()
        print("✅ 新数据添加完成")
        
    except Exception as e:
        print(f"❌ 添加数据失败: {e}")

def test_api():
    """测试API"""
    print("🔍 测试集群状态API...")
    
    try:
        response = requests.get(
            'http://localhost:8000/api/v1/cluster/status',
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                perf = data['data'].get('performance_metrics', {})
                print(f"📊 当前性能指标:")
                print(f"  吞吐量: {perf.get('throughput', 'N/A')} msg/s")
                print(f"  延迟: {perf.get('latency', 'N/A')}ms")
                print(f"  队列长度: {perf.get('queue_length', 'N/A')}")
                
                debug_info = data['data'].get('debug_info', {})
                print(f"  消费者: {debug_info.get('total_consumers', 'N/A')}")
                print(f"  健康: {debug_info.get('healthy_workers', 'N/A')}")
                print(f"  警告: {debug_info.get('warning_workers', 'N/A')}")
                return True
            else:
                print(f"❌ API错误: {data.get('message')}")
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")
    
    return False

async def main():
    print("🧪 快速吞吐量测试")
    print("=" * 40)
    
    # 测试初始状态
    print("\n1️⃣ 测试初始状态:")
    test_api()
    
    # 添加新数据
    print("\n2️⃣ 添加新数据:")
    await add_fresh_data()
    
    # 等待一下再测试
    print("\n3️⃣ 等待2秒后重新测试:")
    await asyncio.sleep(2)
    test_api()
    
    print("\n✅ 测试完成")
    print("\n💡 提示: 如果吞吐量仍然是60，请检查后端日志中的详细调试信息")

if __name__ == "__main__":
    asyncio.run(main())