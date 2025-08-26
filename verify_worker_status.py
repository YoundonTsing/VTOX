#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速验证Worker状态修复效果
"""

import asyncio
import aiohttp
import json

async def verify_worker_status():
    """验证Worker状态"""
    print("🔍 验证Worker状态修复效果...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/api/v1/cluster/status") as response:
                if response.status == 200:
                    data = await response.json()
                    cluster_data = data.get("data", {})
                    worker_nodes = cluster_data.get("worker_nodes", [])
                    
                    print(f"\n📊 Worker节点状态验证结果:")
                    print(f"=" * 50)
                    
                    healthy_count = 0
                    warning_count = 0
                    
                    for worker in worker_nodes:
                        worker_id = worker.get("id", "unknown")
                        status = worker.get("status", "unknown")
                        current_tasks = worker.get("current_tasks", 0)
                        idle_ms = worker.get("idle_ms", 0)
                        
                        status_icon = "✅" if status == "healthy" else "⚠️" if status == "warning" else "❌"
                        
                        print(f"{status_icon} {worker_id}: {status} (任务:{current_tasks}, 空闲:{idle_ms/1000:.1f}s)")
                        
                        if status == "healthy":
                            healthy_count += 1
                        elif status == "warning":
                            warning_count += 1
                    
                    print(f"\n📈 统计结果:")
                    print(f"   健康节点: {healthy_count}")
                    print(f"   警告节点: {warning_count}")
                    print(f"   总节点数: {len(worker_nodes)}")
                    
                    # 显示集群健康度
                    cluster_health = cluster_data.get("cluster_health", 0)
                    cluster_status = cluster_data.get("cluster_status", "未知")
                    
                    print(f"\n🏥 集群总体状态:")
                    print(f"   健康度: {cluster_health}%")
                    print(f"   状态: {cluster_status}")
                    
                    # 验证修复效果
                    if healthy_count > warning_count:
                        print(f"\n🎉 修复成功！大部分Worker节点现在状态为健康")
                    elif healthy_count > 0:
                        print(f"\n✅ 修复部分成功，有{healthy_count}个健康节点")
                    else:
                        print(f"\n⚠️ 仍需调整，所有Worker仍为警告状态")
                    
                else:
                    print(f"❌ API请求失败: HTTP {response.status}")
                    
    except Exception as e:
        print(f"❌ 验证失败: {e}")

async def main():
    await verify_worker_status()

if __name__ == "__main__":
    asyncio.run(main())