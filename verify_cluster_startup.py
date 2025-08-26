#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VTOX 集群启动验证工具
验证 main.py 是否正确以集群模式启动
"""

import asyncio
import aiohttp
import json
import time
import psutil
from typing import Dict, Any

class ClusterStartupVerifier:
    """集群启动验证器"""
    
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url
        self.expected_ports = [8000, 8001, 8002, 8003, 8004]  # 主服务 + 协调器 + 3个Worker
        
    def check_port_usage(self) -> Dict[int, bool]:
        """检查端口占用情况"""
        port_status = {}
        
        for port in self.expected_ports:
            try:
                for conn in psutil.net_connections():
                    if conn.laddr.port == port and conn.status == 'LISTEN':
                        port_status[port] = True
                        break
                else:
                    port_status[port] = False
            except Exception:
                port_status[port] = False
                
        return port_status
    
    async def check_api_health(self) -> Dict[str, Any]:
        """检查 API 健康状态"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_base_url}/") as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "status": "healthy",
                            "response": data
                        }
                    else:
                        return {
                            "status": "unhealthy",
                            "status_code": response.status
                        }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def check_cluster_status(self) -> Dict[str, Any]:
        """检查集群状态 API"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_base_url}/api/v1/cluster/status") as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "status": "healthy",
                            "cluster_data": data
                        }
                    else:
                        return {
                            "status": "unhealthy", 
                            "status_code": response.status
                        }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def verify_startup(self) -> bool:
        """完整的启动验证"""
        print("🔍 VTOX 集群启动验证")
        print("=" * 60)
        
        # 1. 检查端口占用
        print("\n📊 1. 检查端口占用情况:")
        port_status = self.check_port_usage()
        
        expected_running = 0
        for port, is_used in port_status.items():
            status_icon = "✅" if is_used else "❌"
            if port == 8000:
                print(f"   {status_icon} 端口 {port}: FastAPI 主服务")
                if is_used:
                    expected_running += 1
            elif port == 8001:
                print(f"   {status_icon} 端口 {port}: 诊断协调器")
                if is_used:
                    expected_running += 1
            else:
                worker_num = port - 8001
                print(f"   {status_icon} 端口 {port}: Worker节点{worker_num}")
                if is_used:
                    expected_running += 1
        
        # 2. 检查 API 健康状态
        print(f"\n🌐 2. 检查 API 健康状态:")
        print("   ⏳ 正在连接 API...")
        
        api_health = await self.check_api_health()
        
        if api_health["status"] == "healthy":
            print("   ✅ API 服务正常响应")
            
            response_data = api_health["response"]
            cluster_info = response_data.get("cluster_info", {})
            
            print(f"   📋 服务信息:")
            print(f"      - 架构: {response_data.get('architecture', 'unknown')}")
            print(f"      - 版本: {response_data.get('version', 'unknown')}")
            print(f"      - 队列类型: {response_data.get('queue_type', 'unknown')}")
            
            print(f"   🏗️ 集群信息:")
            print(f"      - 集群启用: {cluster_info.get('cluster_enabled', False)}")
            print(f"      - 集群状态: {cluster_info.get('cluster_status', 'unknown')}")
            print(f"      - Worker数量: {cluster_info.get('worker_count', 0)}")
            print(f"      - 部署模式: {cluster_info.get('deployment_mode', 'unknown')}")
            print(f"      - 服务类型: {cluster_info.get('service_type', 'unknown')}")
            
        elif api_health["status"] == "unhealthy":
            print(f"   ❌ API 服务响应异常: HTTP {api_health['status_code']}")
        else:
            print(f"   ❌ API 服务连接失败: {api_health['error']}")
        
        # 3. 检查集群状态 API
        print(f"\n📈 3. 检查集群状态 API:")
        cluster_status = await self.check_cluster_status()
        
        if cluster_status["status"] == "healthy":
            print("   ✅ 集群状态 API 正常")
            
            cluster_data = cluster_status["cluster_data"]
            print(f"   📊 集群详细信息:")
            print(f"      - 系统吞吐量: {cluster_data.get('throughput', 'N/A')} msg/s")
            print(f"      - 平均延迟: {cluster_data.get('average_latency', 'N/A')} ms")
            print(f"      - 集群健康度: {cluster_data.get('cluster_health', 'N/A')}%")
            
            workers = cluster_data.get("workers", [])
            if workers:
                print(f"      - 活跃 Worker: {len(workers)} 个")
                for worker in workers[:3]:  # 只显示前3个
                    print(f"        * {worker.get('id', 'unknown')}: {worker.get('status', 'unknown')}")
            
        else:
            print(f"   ⚠️ 集群状态 API 不可用: {cluster_status.get('error', 'unknown')}")
        
        # 4. 生成验证结果
        print(f"\n🎯 4. 验证结果总结:")
        
        success_criteria = [
            (port_status.get(8000, False), "FastAPI 主服务运行"),
            (api_health["status"] == "healthy", "API 服务健康"),
            (expected_running >= 2, f"至少2个服务运行 (实际: {expected_running})")
        ]
        
        all_success = True
        for criterion, description in success_criteria:
            status_icon = "✅" if criterion else "❌"
            print(f"   {status_icon} {description}")
            if not criterion:
                all_success = False
        
        # 5. 给出建议
        print(f"\n💡 建议:")
        if all_success:
            if expected_running >= 4:
                print("   🎉 集群模式启动完美！所有服务正常运行")
                print("   🚀 您可以开始启动前端和数据源了")
            else:
                print("   ✅ 基础服务正常，集群可能仍在启动中")
                print("   ⏳ 等待几秒后 Worker 节点应该会完全启动")
        else:
            print("   ⚠️ 发现问题，请检查:")
            print("      1. Redis 服务是否启动")
            print("      2. 端口是否被其他进程占用")
            print("      3. 系统资源是否充足")
            print("      4. 查看终端中的错误日志")
        
        return all_success

async def main():
    """主函数"""
    verifier = ClusterStartupVerifier()
    
    print("等待3秒让服务完全启动...")
    await asyncio.sleep(3)
    
    success = await verifier.verify_startup()
    
    if success:
        print(f"\n🎉 验证通过！集群启动成功")
        return 0
    else:
        print(f"\n❌ 验证失败！请检查启动日志")
        return 1

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        exit(result)
    except KeyboardInterrupt:
        print("\n❌ 用户中断验证")
        exit(1)
    except Exception as e:
        print(f"\n❌ 验证异常: {e}")
        exit(1)