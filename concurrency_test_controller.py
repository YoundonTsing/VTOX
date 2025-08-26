#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VTOX 分布式系统并发测试配置器
支持多级别负载测试和性能监控
"""

import asyncio
import aiohttp
import argparse
import json
import time
import subprocess
import sys
from datetime import datetime
from pathlib import Path

class ConcurrencyTestController:
    """并发测试控制器"""
    
    def __init__(self):
        self.backend_url = "http://localhost:8000"
        self.session = None
        self.auth_token = None
        
        # 测试配置预设
        self.test_presets = {
            "light": {
                "vehicles": 5,
                "consumers_per_fault": 2,
                "duration_minutes": 5,
                "description": "轻量测试 - 5辆车，基础负载"
            },
            "medium": {
                "vehicles": 20,
                "consumers_per_fault": 4,
                "duration_minutes": 10,
                "description": "中等测试 - 20辆车，中等负载"
            },
            "heavy": {
                "vehicles": 50,
                "consumers_per_fault": 6,
                "duration_minutes": 15,
                "description": "重载测试 - 50辆车，高负载"
            },
            "extreme": {
                "vehicles": 100,
                "consumers_per_fault": 10,
                "duration_minutes": 20,
                "description": "极限测试 - 100辆车，极限负载"
            }
        }
    
    async def initialize(self):
        """初始化测试环境"""
        self.session = aiohttp.ClientSession()
        return await self.login()
    
    async def login(self, username="user1", password="password123"):
        """登录获取认证"""
        try:
            async with self.session.post(
                f"{self.backend_url}/auth/token",
                json={"username": username, "password": password}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.auth_token = data.get("access_token")
                    print("✅ 认证成功")
                    return True
                else:
                    print(f"❌ 认证失败: HTTP {response.status}")
                    return False
        except Exception as e:
            print(f"❌ 认证异常: {e}")
            return False
    
    def get_auth_headers(self):
        """获取认证头"""
        if self.auth_token:
            return {"Authorization": f"Bearer {self.auth_token}"}
        return {}
    
    async def configure_system_for_test(self, test_config):
        """为测试配置系统"""
        print(f"🔧 配置系统用于测试: {test_config['description']}")
        
        # 1. 初始化分布式诊断系统
        print("   📡 初始化分布式诊断系统...")
        async with self.session.post(
            f"{self.backend_url}/api/v1/diagnosis-stream/initialize",
            headers=self.get_auth_headers()
        ) as response:
            if response.status == 200:
                print("   ✅ 系统初始化成功")
            else:
                print(f"   ⚠️ 初始化状态: {response.status}")
        
        # 2. 启动Consumer with 指定数量
        print(f"   🚀 启动{test_config['consumers_per_fault']}个Consumer/故障类型...")
        params = {
            "consumers_per_fault": test_config['consumers_per_fault'],
            "enable_aggregation": "true",
            "enable_monitoring": "true"
        }
        
        async with self.session.post(
            f"{self.backend_url}/api/v1/diagnosis-stream/start",
            params=params,
            headers=self.get_auth_headers()
        ) as response:
            if response.status == 200:
                print("   ✅ Consumer启动成功")
                return True
            else:
                error_text = await response.text()
                print(f"   ❌ Consumer启动失败: {response.status} - {error_text}")
                return False
    
    def start_vehicle_simulator(self, vehicle_count, duration_minutes):
        """启动车辆模拟器"""
        print(f"🚗 启动{vehicle_count}辆车模拟器，运行{duration_minutes}分钟...")
        
        simulator_cmd = [
            sys.executable,
            "databases/multi_vehicle_simulator.py",
            "--vehicles", str(vehicle_count),
            "--duration", str(duration_minutes * 60)
        ]
        
        process = subprocess.Popen(
            simulator_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        print(f"✅ 模拟器启动成功 (PID: {process.pid})")
        return process
    
    def start_monitoring(self):
        """启动监控进程"""
        print("📊 启动系统监控...")
        
        # 启动Redis Stream监控
        monitor_cmd = [sys.executable, "databases/redis_stream_monitor.py", "--interval", "5"]
        
        monitor_process = subprocess.Popen(
            monitor_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        print(f"✅ 监控启动成功 (PID: {monitor_process.pid})")
        return monitor_process
    
    async def get_system_status(self):
        """获取系统状态"""
        try:
            async with self.session.get(
                f"{self.backend_url}/api/v1/cluster/status"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", {})
                else:
                    return {}
        except Exception as e:
            print(f"⚠️ 获取系统状态失败: {e}")
            return {}
    
    async def run_test(self, test_name):
        """运行指定的测试"""
        if test_name not in self.test_presets:
            print(f"❌ 未知测试配置: {test_name}")
            return False
        
        test_config = self.test_presets[test_name]
        
        print(f"\n{'='*60}")
        print(f"🎯 开始并发测试: {test_config['description']}")
        print(f"{'='*60}")
        
        # 配置系统
        if not await self.configure_system_for_test(test_config):
            print("❌ 系统配置失败")
            return False
        
        # 等待系统稳定
        print("⏳ 等待系统稳定 (5秒)...")
        await asyncio.sleep(5)
        
        # 获取测试前状态
        initial_status = await self.get_system_status()
        initial_workers = len(initial_status.get("worker_nodes", []))
        
        print(f"📊 测试前状态:")
        print(f"   Worker节点数: {initial_workers}")
        print(f"   集群健康度: {initial_status.get('cluster_health', 0)}%")
        
        # 启动监控
        monitor_process = self.start_monitoring()
        
        # 启动车辆模拟器
        simulator_process = self.start_vehicle_simulator(
            test_config['vehicles'],
            test_config['duration_minutes']
        )
        
        # 显示测试信息
        print(f"\n🔥 测试进行中...")
        print(f"   车辆数量: {test_config['vehicles']}")
        print(f"   Consumer数: {test_config['consumers_per_fault']} × 5故障类型 = {test_config['consumers_per_fault'] * 5}")
        print(f"   预计运行: {test_config['duration_minutes']}分钟")
        print(f"   开始时间: {datetime.now().strftime('%H:%M:%S')}")
        
        # 定期检查状态
        test_start_time = time.time()
        check_interval = 30  # 30秒检查一次
        
        while simulator_process.poll() is None:
            await asyncio.sleep(check_interval)
            
            elapsed_minutes = (time.time() - test_start_time) / 60
            current_status = await self.get_system_status()
            
            print(f"\n📈 测试进度 ({elapsed_minutes:.1f}分钟):")
            print(f"   集群健康度: {current_status.get('cluster_health', 0)}%")
            print(f"   活跃Worker: {len(current_status.get('worker_nodes', []))}")
            print(f"   吞吐量: {current_status.get('performance_metrics', {}).get('throughput', 0)} msg/s")
            
            # 检查是否超时
            if elapsed_minutes > test_config['duration_minutes'] + 2:
                print("⚠️ 测试超时，终止模拟器")
                simulator_process.terminate()
                break
        
        # 测试完成
        print(f"\n✅ 测试完成!")
        
        # 获取最终状态
        final_status = await self.get_system_status()
        
        print(f"\n📊 测试结果:")
        print(f"   最终健康度: {final_status.get('cluster_health', 0)}%")
        print(f"   最终Worker数: {len(final_status.get('worker_nodes', []))}")
        print(f"   最终吞吐量: {final_status.get('performance_metrics', {}).get('throughput', 0)} msg/s")
        
        # 清理
        if monitor_process.poll() is None:
            monitor_process.terminate()
        
        return True
    
    async def cleanup(self):
        """清理资源"""
        if self.session:
            await self.session.close()

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="VTOX 并发测试控制器")
    parser.add_argument("--test", choices=["light", "medium", "heavy", "extreme"], 
                       default="light", help="测试级别")
    parser.add_argument("--list", action="store_true", help="列出所有测试配置")
    
    args = parser.parse_args()
    
    controller = ConcurrencyTestController()
    
    if args.list:
        print("📋 可用测试配置:")
        for name, config in controller.test_presets.items():
            print(f"  {name}: {config['description']}")
        return
    
    try:
        if await controller.initialize():
            await controller.run_test(args.test)
        else:
            print("❌ 初始化失败")
    finally:
        await controller.cleanup()

if __name__ == "__main__":
    asyncio.run(main())