#!/usr/bin/env python3
"""
诊断方法1未被使用的问题
检查配置导入、Redis连接、数据获取等各个环节
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

import asyncio
import redis.asyncio as redis
import time
import requests

async def test_config_import():
    """测试配置导入"""
    print("🔧 测试配置导入...")
    try:
        # 直接导入测试
        from backend.app.config.throughput_config import get_config
        config = get_config()
        
        print(f"✅ 配置导入成功:")
        print(f"  - 时间窗口: {config.freshness_window_minutes}分钟")
        print(f"  - 最小新鲜度因子: {config.min_freshness_factor}")
        print(f"  - 递减曲线: {config.decay_curve_type}")
        print(f"  - 基础乘数: {config.base_throughput_multiplier}")
        return True
        
    except Exception as e:
        print(f"❌ 配置导入失败: {e}")
        return False

async def test_redis_data():
    """测试Redis数据"""
    print("\n📊 测试Redis数据...")
    try:
        redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
        await redis_client.ping()
        print("✅ Redis连接成功")
        
        # 检查performance_metrics流
        recent_metrics = await redis_client.xrevrange("performance_metrics", count=10)
        if recent_metrics:
            print(f"✅ performance_metrics流有数据: {len(recent_metrics)}条")
            
            # 检查最新数据的年龄
            latest_metric_id = recent_metrics[0][0]
            metric_timestamp = int(latest_metric_id.split('-')[0])
            current_time_ms = int(time.time() * 1000)
            age_minutes = (current_time_ms - metric_timestamp) / 60000
            
            print(f"  - 最新数据ID: {latest_metric_id}")
            print(f"  - 数据年龄: {age_minutes:.2f}分钟")
            print(f"  - 当前时间: {current_time_ms}")
            print(f"  - 数据时间: {metric_timestamp}")
            
            # 检查数据内容
            latest_data = recent_metrics[0][1]
            print(f"  - 数据内容: {latest_data}")
            
        else:
            print("❌ performance_metrics流无数据")
            return False
            
        await redis_client.aclose()
        return True
        
    except Exception as e:
        print(f"❌ Redis测试失败: {e}")
        return False

def test_api_directly():
    """直接测试API"""
    print("\n🌐 测试API...")
    try:
        response = requests.get('http://localhost:8000/api/v1/cluster/status', timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                metrics = data['data']['performance_metrics']
                print(f"✅ API调用成功:")
                print(f"  - 吞吐量: {metrics['throughput']} msg/s")
                print(f"  - 延迟: {metrics['latency']} ms")
                print(f"  - 队列长度: {metrics['queue_length']}")
                return metrics['throughput']
        
        print(f"❌ API调用失败: {response.status_code}")
        return None
        
    except Exception as e:
        print(f"❌ API测试失败: {e}")
        return None

async def simulate_method1_calculation():
    """模拟方法1计算过程"""
    print("\n🧮 模拟方法1计算...")
    try:
        # 导入配置
        from backend.app.config.throughput_config import get_config
        config = get_config()
        
        # 获取Redis数据
        redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
        recent_metrics = await redis_client.xrevrange("performance_metrics", count=10)
        
        if not recent_metrics:
            print("❌ 无performance_metrics数据")
            return None
        
        # 计算数据年龄
        latest_metric_id = recent_metrics[0][0]
        metric_timestamp = int(latest_metric_id.split('-')[0])
        current_time_ms = int(time.time() * 1000)
        age_minutes = (current_time_ms - metric_timestamp) / 60000
        
        print(f"📊 模拟计算过程:")
        print(f"  - 数据年龄: {age_minutes:.2f}分钟")
        print(f"  - 时间窗口: {config.freshness_window_minutes}分钟")
        print(f"  - 数据是否在窗口内: {age_minutes < config.freshness_window_minutes}")
        
        if age_minutes < config.freshness_window_minutes:
            # 计算吞吐量
            base_throughput = len(recent_metrics) * config.base_throughput_multiplier
            freshness_factor = config.calculate_freshness_factor(age_minutes)
            
            activity_factor = min(1.5, len(recent_metrics) / 8.0)
            final_factor = (freshness_factor * config.freshness_weight + 
                          activity_factor * config.activity_weight)
            
            throughput_per_minute = base_throughput * final_factor
            throughput_per_second = throughput_per_minute / 60.0
            
            print(f"  - 基础吞吐量: {base_throughput:.1f} msg/min")
            print(f"  - 新鲜度因子: {freshness_factor:.4f}")
            print(f"  - 活跃度因子: {activity_factor:.4f}")
            print(f"  - 最终因子: {final_factor:.4f}")
            print(f"  - 每分钟吞吐量: {throughput_per_minute:.1f} msg/min")
            print(f"  - 每秒吞吐量: {throughput_per_second:.1f} msg/s")
            
            return throughput_per_second
        else:
            print(f"  - 数据过旧，应该跳过方法1")
            return None
            
        await redis_client.aclose()
        
    except Exception as e:
        print(f"❌ 模拟计算失败: {e}")
        return None

async def check_auto_refresh_service():
    """检查自动刷新服务"""
    print("\n🔄 检查自动刷新服务...")
    try:
        from backend.app.services.auto_refresh_service import get_auto_refresh_service
        service = await get_auto_refresh_service()
        print("✅ 自动刷新服务导入成功")
        
        # 测试手动刷新
        result = await service.manual_refresh("诊断测试")
        if result:
            print("✅ 手动刷新测试成功")
        else:
            print("❌ 手动刷新测试失败")
        
        return True
        
    except Exception as e:
        print(f"❌ 自动刷新服务检查失败: {e}")
        return False

async def main():
    print("🔍 诊断方法1未被使用的问题")
    print("=" * 50)
    
    # 测试1: 配置导入
    config_ok = await test_config_import()
    
    # 测试2: Redis数据
    redis_ok = await test_redis_data()
    
    # 测试3: API调用
    api_result = test_api_directly()
    
    # 测试4: 模拟方法1计算
    simulated_result = await simulate_method1_calculation()
    
    # 测试5: 自动刷新服务
    refresh_ok = await check_auto_refresh_service()
    
    # 结果分析
    print("\n📋 诊断总结:")
    print(f"  - 配置导入: {'✅' if config_ok else '❌'}")
    print(f"  - Redis数据: {'✅' if redis_ok else '❌'}")
    print(f"  - API调用: {'✅' if api_result else '❌'}")
    print(f"  - 方法1模拟: {'✅' if simulated_result else '❌'}")
    print(f"  - 自动刷新: {'✅' if refresh_ok else '❌'}")
    
    if api_result and simulated_result:
        print(f"\n🔍 结果对比:")
        print(f"  - API返回: {api_result:.1f} msg/s")
        print(f"  - 方法1模拟: {simulated_result:.1f} msg/s")
        
        if abs(api_result - simulated_result) < 0.1:
            print("✅ 结果一致，方法1正在使用")
        else:
            print("❌ 结果不一致，方法1可能未被使用")
            
            if api_result > 90:
                print("💡 API返回值很大(>90)，可能使用了方法3固定估算")
            
    print("\n💡 可能的问题:")
    print("  1. 配置模块导入失败")
    print("  2. performance_metrics数据过旧或无数据")
    print("  3. 方法1计算过程中出现异常")
    print("  4. 单位转换问题(msg/min vs msg/s)")
    print("  5. 自动刷新服务未正常工作")

if __name__ == "__main__":
    asyncio.run(main())