#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis Stream缓存优化方案简单测试演示
解决编码问题并提供基本测试功能
"""

import asyncio
import aiohttp
import time
import json
import random
from datetime import datetime

async def demo_test():
    """演示测试程序"""
    print("Redis Stream缓存优化方案测试演示")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    
    async with aiohttp.ClientSession() as session:
        try:
            # 1. 测试连通性
            print("\n1. 测试后端连通性...")
            async with session.get(f"{base_url}/health") as response:
                if response.status == 200:
                    print("   连接成功")
                else:
                    print(f"   连接失败: {response.status}")
                    return
        
        except Exception as e:
            print(f"   连接异常: {str(e)}")
            print("   请确保后端服务正在运行")
            return
        
        # 2. 测试桥接器状态
        print("\n2. 获取桥接器状态...")
        try:
            url = f"{base_url}/api/v1/diagnosis-stream/bridge/status"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"   状态获取成功: {data.get('status')}")
                else:
                    print(f"   状态获取失败: {response.status}")
        except Exception as e:
            print(f"   状态获取异常: {str(e)}")
        
        # 3. 启用缓存优化
        print("\n3. 启用缓存优化...")
        try:
            url = f"{base_url}/api/v1/diagnosis-stream/bridge/optimization/enable"
            async with session.post(url) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"   启用成功: {data.get('message', 'OK')}")
                else:
                    print(f"   启用失败: {response.status}")
        except Exception as e:
            print(f"   启用异常: {str(e)}")
        
        # 4. 发送测试消息
        print("\n4. 发送测试消息...")
        success_count = 0
        for i in range(5):
            try:
                data = {
                    "vehicle_id": f"TEST_VEHICLE_{i:03d}",
                    "fault_type": "turn_fault",
                    "sensor_data": {
                        "current": [random.uniform(0, 10) for _ in range(10)],
                        "voltage": [random.uniform(220, 240) for _ in range(10)],
                        "frequency": 50.0,
                        "temperature": random.uniform(20, 80)
                    },
                    "timestamp": datetime.now().isoformat(),
                    "location": "测试地点"
                }
                
                url = f"{base_url}/api/v1/diagnosis-stream/vehicles/{data['vehicle_id']}/data"
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        success_count += 1
                        print(f"   消息 {i+1}/5 发送成功")
                    else:
                        print(f"   消息 {i+1}/5 发送失败: {response.status}")
                
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"   消息 {i+1}/5 异常: {str(e)}")
        
        print(f"   发送成功率: {success_count}/5 ({success_count*20}%)")
        
        # 5. 获取优化统计
        print("\n5. 获取优化统计...")
        try:
            url = f"{base_url}/api/v1/diagnosis-stream/bridge/optimization/stats"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "success":
                        stats = data.get("data", {})
                        print(f"   优化器运行: {stats.get('is_running', False)}")
                        print(f"   缓存命中率: {stats.get('cache_hit_rate', 0):.1%}")
                        print(f"   消息丢失率: {stats.get('loss_rate', 0):.1%}")
                        print(f"   活跃车辆: {stats.get('active_vehicles', 0)}")
                    else:
                        print(f"   统计获取失败: {data.get('message')}")
                else:
                    print(f"   统计获取失败: {response.status}")
        except Exception as e:
            print(f"   统计获取异常: {str(e)}")
        
        # 6. 禁用缓存优化
        print("\n6. 禁用缓存优化...")
        try:
            url = f"{base_url}/api/v1/diagnosis-stream/bridge/optimization/disable"
            async with session.post(url) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"   禁用成功: {data.get('message', 'OK')}")
                else:
                    print(f"   禁用失败: {response.status}")
        except Exception as e:
            print(f"   禁用异常: {str(e)}")
        
    print("\n测试演示完成!")
    print("\n主要功能验证:")
    print("  API接口连通性")
    print("  缓存优化启用/禁用")
    print("  消息发送处理")
    print("  统计信息获取")
    print("\n如需详细测试，请运行其他测试程序")

if __name__ == "__main__":
    asyncio.run(demo_test()) 