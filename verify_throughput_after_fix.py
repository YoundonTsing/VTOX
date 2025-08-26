#!/usr/bin/env python3
"""
验证消费者修复后的吞吐量计算状态
"""
import asyncio
import redis.asyncio as redis
import requests
import time
from datetime import datetime

async def check_consumer_activity():
    """检查消费者活跃状态"""
    print("🔍 检查消费者活跃状态...")
    print("=" * 50)
    
    try:
        redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
        await redis_client.ping()
        
        current_time = int(time.time() * 1000)
        
        # 检查motor_raw_data的消费者状态
        groups = await redis_client.xinfo_groups("motor_raw_data")
        
        active_consumers = 0
        total_consumers = 0
        
        print("📊 motor_raw_data消费者活跃度分析:")
        
        for group in groups:
            group_name = group['name']
            try:
                consumers = await redis_client.xinfo_consumers("motor_raw_data", group_name)
                for consumer in consumers:
                    total_consumers += 1
                    consumer_name = consumer['name']
                    idle_ms = consumer['idle']
                    idle_minutes = idle_ms / 60000
                    
                    # 使用吞吐量计算的标准：5分钟内为活跃
                    if idle_ms < 300000:  # 5分钟 = 300秒
                        active_consumers += 1
                        status = "✅ 活跃"
                    elif idle_ms < 600000:  # 10分钟
                        status = "⚠️ 正常"
                    else:
                        status = "❌ 闲置"
                    
                    print(f"  {consumer_name}: {status} ({idle_minutes:.1f}分钟)")
            except Exception as e:
                print(f"  获取组 {group_name} 消费者失败: {e}")
        
        print(f"\n📈 活跃度统计:")
        print(f"  总消费者: {total_consumers}")
        print(f"  活跃消费者(5分钟内): {active_consumers}")
        print(f"  活跃比例: {(active_consumers/total_consumers*100):.1f}%" if total_consumers > 0 else "  活跃比例: 0%")
        
        await redis_client.aclose()
        return active_consumers, total_consumers
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return 0, 0

async def check_stream_activity():
    """检查Stream活跃度"""
    print("\n🌊 检查Stream活跃度...")
    print("=" * 50)
    
    try:
        redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
        await redis_client.ping()
        
        current_time = int(time.time() * 1000)
        
        streams = ["motor_raw_data", "fault_diagnosis_results", "vehicle_health_assessments"]
        
        for stream_name in streams:
            try:
                stream_info = await redis_client.xinfo_stream(stream_name)
                length = stream_info.get('length', 0)
                
                if length > 0:
                    # 获取最新消息
                    latest = await redis_client.xrevrange(stream_name, count=1)
                    if latest:
                        latest_id = latest[0][0]
                        timestamp_ms = int(latest_id.split('-')[0])
                        age_minutes = (current_time - timestamp_ms) / 60000
                        
                        print(f"📊 {stream_name}:")
                        print(f"  总消息: {length}条")
                        print(f"  最新消息: {age_minutes:.1f}分钟前")
                        
                        # 检查最近10分钟的消息数量
                        ten_min_ago = current_time - 600000
                        recent_messages = await redis_client.xrange(
                            stream_name, 
                            min=f"{ten_min_ago}-0", 
                            max="+"
                        )
                        print(f"  最近10分钟: {len(recent_messages)}条新消息")
                        
            except Exception as e:
                print(f"  检查 {stream_name} 失败: {e}")
        
        await redis_client.aclose()
        
    except Exception as e:
        print(f"❌ Stream检查失败: {e}")

def test_api_throughput():
    """测试API吞吐量计算"""
    print("\n🧪 测试API吞吐量计算...")
    print("=" * 50)
    
    try:
        response = requests.get(
            'http://localhost:8000/api/v1/cluster/status',
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                cluster_data = data['data']
                perf = cluster_data.get('performance_metrics', {})
                debug = cluster_data.get('debug_info', {})
                
                print("📊 当前API返回结果:")
                print(f"  吞吐量: {perf.get('throughput')} msg/s")
                print(f"  延迟: {perf.get('latency')}ms")
                print(f"  队列长度: {perf.get('queue_length')}")
                print(f"  总消费者: {debug.get('total_consumers')}")
                print(f"  健康消费者: {debug.get('healthy_workers')}")
                
                # 分析可能的问题
                throughput = perf.get('throughput', 0)
                healthy_workers = debug.get('healthy_workers', 0)
                
                print(f"\n🩺 问题分析:")
                if throughput <= 3:
                    print("  ⚠️ 吞吐量过低，可能原因:")
                    print("    1. 方法1: performance_metrics数据过期")
                    print("    2. 方法2: Stream活动检测窗口太短")
                    print("    3. 方法3: 消费者活跃度判断逻辑需要时间更新")
                    
                if healthy_workers == 0:
                    print("  ❌ 没有健康消费者，需要检查阈值设置")
                elif healthy_workers > 0:
                    print(f"  ✅ 有{healthy_workers}个健康消费者")
                
                return throughput
            else:
                print(f"❌ API返回错误: {data.get('message')}")
                return None
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ API测试失败: {e}")
        return None

async def suggest_solutions(active_consumers, total_consumers, current_throughput):
    """建议解决方案"""
    print("\n💡 建议解决方案:")
    print("=" * 50)
    
    if active_consumers > 0 and current_throughput and current_throughput <= 3:
        print("🔧 吞吐量计算可能需要优化:")
        print("1. 等待一段时间（2-3分钟）让算法检测到消费者活跃状态")
        print("2. 手动刷新performance_metrics数据")
        print("3. 检查吞吐量配置是否启用自动刷新")
        print("4. 调整消费者活跃度判断阈值")
        
        print("\n🚀 立即尝试的解决方案:")
        print("1. 刷新前端页面，等待新数据")
        print("2. 检查自动刷新服务是否正常运行")
        print("3. 手动触发吞吐量配置刷新")
    
    elif active_consumers == 0:
        print("❌ 消费者活跃度问题:")
        print("1. 检查消费者是否真的在处理数据")
        print("2. 调整活跃度判断阈值（从5分钟改为2分钟）")
        print("3. 重新检查消费者闲置时间")
    
    else:
        print("✅ 系统状态正常，吞吐量应该会逐渐恢复")

async def main():
    print("🛠️ 消费者修复后吞吐量验证")
    print("=" * 50)
    print("目标: 验证修复效果并分析吞吐量问题")
    print()
    
    # 1. 检查消费者活跃状态
    active_consumers, total_consumers = await check_consumer_activity()
    
    # 2. 检查Stream活跃度
    await check_stream_activity()
    
    # 3. 测试API吞吐量
    current_throughput = test_api_throughput()
    
    # 4. 建议解决方案
    await suggest_solutions(active_consumers, total_consumers, current_throughput)
    
    print("\n" + "="*50)
    print("🎯 总结:")
    if active_consumers > 0:
        print(f"✅ 消费者修复成功：{active_consumers}/{total_consumers}个消费者活跃")
        if current_throughput and current_throughput <= 3:
            print("⚠️ 吞吐量计算需要时间更新，建议等待2-3分钟后重新检查")
        else:
            print("✅ 系统完全恢复正常")
    else:
        print("❌ 需要进一步检查消费者状态")

if __name__ == "__main__":
    asyncio.run(main())