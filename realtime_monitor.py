#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VTOX 实时系统监控面板
显示分布式系统关键性能指标
"""

import asyncio
import aiohttp
import redis.asyncio as redis
import time
import os
from datetime import datetime, timedelta
from typing import Dict, Any

class RealTimeMonitor:
    """实时监控面板"""
    
    def __init__(self):
        self.backend_url = "http://localhost:8000"
        self.redis_url = "redis://localhost:6379"
        self.redis_client = None
        self.running = False
    
    async def initialize(self):
        """初始化连接"""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis_client.ping()
            return True
        except Exception as e:
            print(f"❌ Redis连接失败: {e}")
            return False
    
    def clear_screen(self):
        """清屏"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    async def get_cluster_status(self):
        """获取集群状态"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.backend_url}/api/v1/cluster/status") as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("data", {})
                    else:
                        return {}
        except Exception:
            return {}
    
    async def get_stream_stats(self):
        """获取Stream统计"""
        try:
            streams = [
                "motor_raw_data",
                "fault_diagnosis_results", 
                "vehicle_health_assessments",
                "performance_metrics",
                "system_alerts"
            ]
            
            stats = {}
            for stream_name in streams:
                length = await self.redis_client.xlen(stream_name)
                
                # 获取最近消息时间
                recent_messages = await self.redis_client.xrevrange(stream_name, count=1)
                last_message_time = None
                if recent_messages:
                    message_id = recent_messages[0][0]
                    timestamp_ms = int(message_id.split('-')[0])
                    last_message_time = datetime.fromtimestamp(timestamp_ms/1000)
                
                # 获取消费者组数量
                try:
                    groups = await self.redis_client.xinfo_groups(stream_name)
                    groups_count = len(groups)
                except:
                    groups_count = 0
                
                stats[stream_name] = {
                    "length": length,
                    "groups": groups_count,
                    "last_message": last_message_time
                }
            
            return stats
        except Exception as e:
            print(f"获取Stream统计失败: {e}")
            return {}
    
    async def calculate_throughput(self, stream_stats, previous_stats):
        """计算吞吐量"""
        throughput = {}
        
        if not previous_stats:
            return throughput
        
        time_diff = 5  # 5秒间隔
        
        for stream_name in stream_stats:
            current_length = stream_stats[stream_name]["length"]
            previous_length = previous_stats.get(stream_name, {}).get("length", 0)
            
            messages_per_second = (current_length - previous_length) / time_diff
            throughput[stream_name] = max(0, messages_per_second)
        
        return throughput
    
    def format_time_ago(self, dt):
        """格式化时间差"""
        if not dt:
            return "无"
        
        diff = datetime.now() - dt
        seconds = diff.total_seconds()
        
        if seconds < 60:
            return f"{seconds:.1f}秒前"
        elif seconds < 3600:
            return f"{seconds/60:.1f}分钟前"
        else:
            return f"{seconds/3600:.1f}小时前"
    
    def display_dashboard(self, cluster_status, stream_stats, throughput, previous_throughput):
        """显示监控面板"""
        self.clear_screen()
        
        print("🔥 VTOX 实时系统监控面板")
        print("=" * 80)
        print(f"⏰ 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 集群状态
        print("🏗️ 集群状态")
        print("-" * 40)
        cluster_health = cluster_status.get("cluster_health", 0)
        cluster_status_text = cluster_status.get("cluster_status", "未知")
        worker_nodes = cluster_status.get("worker_nodes", [])
        
        health_color = "🟢" if cluster_health >= 90 else "🟡" if cluster_health >= 70 else "🔴"
        print(f"健康度: {health_color} {cluster_health}% ({cluster_status_text})")
        print(f"Worker节点: {len(worker_nodes)}个")
        
        # Worker状态统计
        healthy_workers = sum(1 for w in worker_nodes if w.get("status") == "healthy")
        warning_workers = sum(1 for w in worker_nodes if w.get("status") == "warning")
        active_tasks = sum(w.get("current_tasks", 0) for w in worker_nodes)
        
        print(f"  ✅ 健康: {healthy_workers}")
        print(f"  ⚠️ 警告: {warning_workers}")
        print(f"  🔥 活跃任务: {active_tasks}")
        print()
        
        # 性能指标
        perf_metrics = cluster_status.get("performance_metrics", {})
        print("📊 性能指标")
        print("-" * 40)
        print(f"吞吐量: {perf_metrics.get('throughput', 0):.1f} msg/s")
        print(f"延迟: {perf_metrics.get('latency', 0):.1f} ms")
        print(f"队列积压: {perf_metrics.get('queue_length', 0)}")
        print()
        
        # Stream状态
        print("🌊 Redis Stream状态")
        print("-" * 40)
        print(f"{'Stream名称':<25} {'消息数':<8} {'组数':<4} {'吞吐量':<10} {'最后消息'}")
        print("-" * 70)
        
        for stream_name, stats in stream_stats.items():
            length = stats["length"]
            groups = stats["groups"]
            last_msg = self.format_time_ago(stats["last_message"])
            current_tp = throughput.get(stream_name, 0)
            
            # 显示吞吐量趋势
            if previous_throughput:
                prev_tp = previous_throughput.get(stream_name, 0)
                if current_tp > prev_tp:
                    trend = "📈"
                elif current_tp < prev_tp:
                    trend = "📉"
                else:
                    trend = "➡️"
            else:
                trend = "➡️"
            
            display_name = stream_name.replace("_", " ").title()[:24]
            print(f"{display_name:<25} {length:<8} {groups:<4} {current_tp:>6.1f}/s {trend} {last_msg}")
        
        print()
        
        # 系统资源（如果可用）
        service_registry = cluster_status.get("service_registry", {})
        if service_registry:
            print("🔧 服务注册")
            print("-" * 40)
            print(f"总服务: {service_registry.get('total_services', 0)}")
            print(f"健康服务: {service_registry.get('healthy_services', 0)}")
            print(f"故障服务: {service_registry.get('faulty_services', 0)}")
            print()
        
        # 负载均衡器
        load_balancer = cluster_status.get("load_balancer", {})
        if load_balancer:
            print("⚖️ 负载均衡")
            print("-" * 40)
            print(f"总请求: {load_balancer.get('total_requests', 0)}")
            print(f"成功率: {load_balancer.get('success_rate', 0):.1f}%")
            print(f"平均响应: {load_balancer.get('avg_response_time', 0):.1f}ms")
        
        print()
        print("💡 按 Ctrl+C 退出监控")
    
    async def run_monitor(self):
        """运行监控循环"""
        print("🚀 启动实时监控面板...")
        print("⏳ 正在初始化...")
        
        if not await self.initialize():
            print("❌ 初始化失败")
            return
        
        previous_stream_stats = None
        previous_throughput = None
        
        self.running = True
        
        try:
            while self.running:
                # 获取数据
                cluster_status = await self.get_cluster_status()
                stream_stats = await self.get_stream_stats()
                throughput = await self.calculate_throughput(stream_stats, previous_stream_stats)
                
                # 显示面板
                self.display_dashboard(cluster_status, stream_stats, throughput, previous_throughput)
                
                # 保存上次数据
                previous_stream_stats = stream_stats.copy()
                previous_throughput = throughput.copy()
                
                # 等待下次更新
                await asyncio.sleep(5)
                
        except KeyboardInterrupt:
            print("\n\n👋 监控已停止")
        except Exception as e:
            print(f"\n❌ 监控错误: {e}")
        finally:
            if self.redis_client:
                await self.redis_client.close()

async def main():
    """主函数"""
    monitor = RealTimeMonitor()
    await monitor.run_monitor()

if __name__ == "__main__":
    asyncio.run(main())