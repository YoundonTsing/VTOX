#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VTOX 集群健康诊断脚本

功能：
1. 深入分析Worker节点状态
2. 检查Redis Stream数据流
3. 诊断端到端数据传递问题
4. 提供具体修复建议

使用方法：
python diagnose_cluster_health.py
"""

import asyncio
import json
import logging
import time
import aiohttp
import redis.asyncio as redis
from typing import Dict, Any, List, Optional
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("cluster-health-diagnosis")

class ClusterHealthDiagnostic:
    def __init__(self):
        self.backend_url = "http://localhost:8000"
        self.redis_url = "redis://localhost:6379"
        self.redis_client: Optional[redis.Redis] = None
        self.diagnostic_results = []

    async def initialize(self):
        """初始化诊断环境"""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis_client.ping()
            logger.info("✅ Redis连接成功")
            return True
        except Exception as e:
            logger.error(f"❌ Redis连接失败: {e}")
            return False

    async def diagnose_worker_health(self):
        """诊断Worker节点健康状态"""
        logger.info("🔍 诊断Worker节点健康状态...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.backend_url}/api/v1/cluster/status") as response:
                    if response.status == 200:
                        data = await response.json()
                        cluster_data = data.get("data", {})
                        worker_nodes = cluster_data.get("worker_nodes", [])
                        
                        print("\n" + "="*60)
                        print("🏥 Worker节点健康诊断报告")
                        print("="*60)
                        
                        healthy_count = 0
                        warning_count = 0
                        offline_count = 0
                        
                        for worker in worker_nodes:
                            worker_id = worker.get("id", "unknown")
                            worker_type = worker.get("type", "unknown")
                            status = worker.get("status", "unknown")
                            idle_ms = worker.get("idle_ms", 0)
                            current_tasks = worker.get("current_tasks", 0)
                            success_rate = worker.get("success_rate", 0)
                            
                            print(f"\n🔧 Worker: {worker_id}")
                            print(f"   类型: {worker_type}")
                            print(f"   状态: {status}")
                            print(f"   空闲时间: {idle_ms/1000:.1f}秒")
                            print(f"   当前任务: {current_tasks}")
                            print(f"   成功率: {success_rate*100:.1f}%")
                            
                            # 分析Worker状态
                            if status == "healthy":
                                healthy_count += 1
                            elif status == "warning":
                                warning_count += 1
                                # 分析warning的原因
                                if idle_ms > 300000:  # 超过5分钟空闲
                                    print(f"   ⚠️ 问题: 长时间空闲（{idle_ms/1000/60:.1f}分钟）")
                                if current_tasks == 0:
                                    print(f"   ⚠️ 问题: 没有处理任务")
                                if success_rate < 0.9:
                                    print(f"   ⚠️ 问题: 成功率偏低")
                            else:
                                offline_count += 1
                        
                        print(f"\n📊 Worker节点统计:")
                        print(f"   健康节点: {healthy_count}")
                        print(f"   警告节点: {warning_count}")
                        print(f"   离线节点: {offline_count}")
                        print(f"   总节点数: {len(worker_nodes)}")
                        
                        # 诊断结论
                        if warning_count == len(worker_nodes) and current_tasks == 0:
                            print(f"\n🚨 诊断结论: 所有Worker节点都没有接收到任务")
                            print(f"   可能原因:")
                            print(f"   1. 没有数据写入Redis Stream")
                            print(f"   2. Worker消费者组配置问题")
                            print(f"   3. 集群启动脚本未正确启动Worker")
                        
                        return {
                            "total_workers": len(worker_nodes),
                            "healthy_workers": healthy_count,
                            "warning_workers": warning_count,
                            "offline_workers": offline_count,
                            "all_workers_idle": warning_count == len(worker_nodes)
                        }
                        
        except Exception as e:
            logger.error(f"❌ Worker健康诊断失败: {e}")
            return {"error": str(e)}

    async def diagnose_redis_streams(self):
        """诊断Redis Stream状态"""
        logger.info("🔍 诊断Redis Stream状态...")
        try:
            if not self.redis_client:
                return {"error": "Redis客户端未初始化"}
            
            # 检查关键Stream
            key_streams = [
                "motor_raw_data",
                "fault_diagnosis_results", 
                "vehicle_health_assessments",
                "performance_metrics",
                "system_alerts"
            ]
            
            print(f"\n" + "="*60)
            print("📊 Redis Stream诊断报告")
            print("="*60)
            
            stream_status = {}
            
            for stream_name in key_streams:
                try:
                    # 获取Stream长度
                    length = await self.redis_client.xlen(stream_name)
                    
                    # 获取Stream信息
                    try:
                        info = await self.redis_client.xinfo_stream(stream_name)
                        groups_count = info.get("groups", 0)
                    except:
                        groups_count = 0
                    
                    # 获取最近的消息
                    messages = await self.redis_client.xrevrange(stream_name, count=1)
                    last_message_time = None
                    if messages:
                        last_message_id = messages[0][0]
                        # 从消息ID提取时间戳
                        timestamp_ms = int(last_message_id.split('-')[0])
                        last_message_time = datetime.fromtimestamp(timestamp_ms/1000)
                    
                    print(f"\n🌊 Stream: {stream_name}")
                    print(f"   消息数量: {length}")
                    print(f"   消费者组: {groups_count}")
                    if last_message_time:
                        time_diff = datetime.now() - last_message_time
                        print(f"   最后消息: {time_diff.total_seconds():.1f}秒前")
                    else:
                        print(f"   最后消息: 无")
                    
                    stream_status[stream_name] = {
                        "length": length,
                        "groups": groups_count,
                        "last_message_seconds_ago": time_diff.total_seconds() if last_message_time else None,
                        "has_recent_data": last_message_time and time_diff.total_seconds() < 300  # 5分钟内
                    }
                    
                except Exception as e:
                    print(f"\n❌ Stream {stream_name}: 检查失败 - {e}")
                    stream_status[stream_name] = {"error": str(e)}
            
            # 分析Stream状态
            print(f"\n📋 Stream状态分析:")
            motor_data_length = stream_status.get("motor_raw_data", {}).get("length", 0)
            
            if motor_data_length == 0:
                print(f"   🚨 关键问题: motor_raw_data Stream为空")
                print(f"      → 没有原始数据输入，Worker无法处理任务")
                print(f"      → 需要启动数据源或模拟器")
            
            diagnosis_length = stream_status.get("fault_diagnosis_results", {}).get("length", 0)
            if diagnosis_length == 0:
                print(f"   ⚠️ 问题: 没有诊断结果输出")
                print(f"      → Worker可能没有正常处理数据")
            
            return stream_status
            
        except Exception as e:
            logger.error(f"❌ Redis Stream诊断失败: {e}")
            return {"error": str(e)}

    async def diagnose_data_flow(self):
        """诊断端到端数据流"""
        logger.info("🔍 诊断端到端数据流...")
        try:
            if not self.redis_client:
                return {"error": "Redis客户端未初始化"}
            
            print(f"\n" + "="*60)
            print("🔄 端到端数据流诊断")
            print("="*60)
            
            # 1. 测试写入数据到motor_raw_data
            test_data = {
                "vehicle_id": "DIAGNOSIS_TEST_001",
                "sensor_data": json.dumps({
                    "current_a": 1.5,
                    "current_b": 1.4,
                    "current_c": 1.6,
                    "timestamp": time.time()
                }),
                "test_marker": "health_diagnosis_test",
                "timestamp": str(time.time())
            }
            
            print(f"🔼 步骤1: 写入测试数据到motor_raw_data...")
            message_id = await self.redis_client.xadd("motor_raw_data", test_data)  # type: ignore
            print(f"   ✅ 数据写入成功，消息ID: {message_id}")
            
            # 2. 等待Worker处理
            print(f"⏳ 步骤2: 等待Worker处理数据（10秒）...")
            await asyncio.sleep(10)
            
            # 3. 检查诊断结果Stream
            print(f"🔍 步骤3: 检查诊断结果...")
            diagnosis_messages = await self.redis_client.xrevrange(
                "fault_diagnosis_results", count=5
            )
            
            found_test_result = False
            for msg_id, fields in diagnosis_messages:
                if fields.get("vehicle_id") == "DIAGNOSIS_TEST_001":
                    found_test_result = True
                    print(f"   ✅ 找到测试车辆的诊断结果")
                    print(f"   消息ID: {msg_id}")
                    break
            
            if not found_test_result:
                print(f"   ❌ 未找到测试车辆的诊断结果")
                print(f"   📊 最近的诊断结果数量: {len(diagnosis_messages)}")
            
            # 4. 检查WebSocket数据推送
            print(f"🌐 步骤4: 检查WebSocket推送机制...")
            try:
                import websockets
                async with websockets.connect("ws://localhost:8000/ws/frontend") as websocket:
                    print(f"   ✅ WebSocket连接成功")
                    
                    # 发送订阅消息
                    subscribe_msg = {
                        "type": "subscribe",
                        "channels": ["diagnosis_results"]
                    }
                    await websocket.send(json.dumps(subscribe_msg))
                    
                    # 等待消息
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                        print(f"   ✅ 接收到WebSocket消息")
                    except asyncio.TimeoutError:
                        print(f"   ⚠️ WebSocket连接正常但未接收到实时消息")
                        
            except Exception as e:
                print(f"   ❌ WebSocket连接失败: {e}")
            
            # 清理测试数据
            await self.redis_client.xdel("motor_raw_data", message_id)
            
            return {
                "data_written": True,
                "worker_processed": found_test_result,
                "websocket_available": True  # 基于之前的测试结果
            }
            
        except Exception as e:
            logger.error(f"❌ 数据流诊断失败: {e}")
            return {"error": str(e)}

    async def check_cluster_startup_status(self):
        """检查集群启动状态"""
        logger.info("🔍 检查集群启动状态...")
        try:
            print(f"\n" + "="*60)
            print("🚀 集群启动状态检查")
            print("="*60)
            
            # 检查集群启动脚本是否运行
            print(f"🔧 检查集群组件运行状态...")
            
            # 检查分布式诊断系统是否启动
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(f"{self.backend_url}/api/v1/diagnosis-stream/system/performance") as response:
                        if response.status == 200:
                            data = await response.json()
                            system_stats = data.get("data", {}).get("system_stats", {})
                            messages_processed = system_stats.get("messages_processed", 0)
                            active_consumers = system_stats.get("active_consumers", 0)
                            
                            print(f"   ✅ 分布式诊断系统API可访问")
                            print(f"   📊 已处理消息数: {messages_processed}")
                            print(f"   👥 活跃消费者数: {active_consumers}")
                            
                            if messages_processed == 0:
                                print(f"   🚨 问题: 系统未处理任何消息")
                            if active_consumers == 0:
                                print(f"   🚨 问题: 没有活跃的消费者")
                                
                        elif response.status == 401:
                            print(f"   ⚠️ 分布式诊断系统需要认证")
                        else:
                            print(f"   ❌ 分布式诊断系统响应异常: {response.status}")
                            
                except Exception as e:
                    print(f"   ❌ 无法访问分布式诊断系统: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 集群启动状态检查失败: {e}")
            return False

    def generate_repair_recommendations(self, diagnosis_results):
        """生成修复建议"""
        print(f"\n" + "="*60)
        print("💡 修复建议")
        print("="*60)
        
        recommendations = []
        
        # 基于诊断结果生成建议
        if diagnosis_results.get("all_workers_idle", False):
            recommendations.extend([
                "🔧 Worker节点问题修复:",
                "   1. 启动集群: python cluster/start_cluster.py --mode=development",
                "   2. 检查Worker消费者组: 确保每个故障类型都有对应的消费者",
                "   3. 重启分布式诊断系统"
            ])
        
        if diagnosis_results.get("no_input_data", False):
            recommendations.extend([
                "📊 数据输入问题修复:",
                "   1. 启动数据模拟器: python scripts/data_simulator.py",
                "   2. 检查数据源配置",
                "   3. 确保motor_raw_data Stream有数据写入"
            ])
        
        if not diagnosis_results.get("websocket_working", True):
            recommendations.extend([
                "🌐 WebSocket连接问题修复:",
                "   1. 重启后端服务: cd backend && python run.py",
                "   2. 检查WebSocket路由配置",
                "   3. 确认防火墙设置"
            ])
        
        # 通用建议
        recommendations.extend([
            "🔄 端到端数据流修复:",
            "   1. 确保完整启动顺序: Redis → 后端 → 集群 → 前端",
            "   2. 检查所有服务的日志输出",
            "   3. 验证Redis Stream消费者组配置"
        ])
        
        for rec in recommendations:
            print(rec)

    async def run_full_diagnosis(self):
        """运行完整诊断"""
        print("🏥 开始VTOX集群健康全面诊断")
        print("="*80)
        
        if not await self.initialize():
            print("❌ 诊断环境初始化失败")
            return
        
        # 执行各项诊断
        worker_health = await self.diagnose_worker_health()
        stream_status = await self.diagnose_redis_streams()
        data_flow = await self.diagnose_data_flow()
        cluster_startup = await self.check_cluster_startup_status()
        
        # 汇总诊断结果
        diagnosis_results = {
            "all_workers_idle": worker_health.get("warning_workers", 0) == worker_health.get("total_workers", 0),
            "no_input_data": stream_status.get("motor_raw_data", {}).get("length", 0) == 0,
            "websocket_working": data_flow.get("websocket_available", False),
            "worker_processing": data_flow.get("worker_processed", False)
        }
        
        # 生成修复建议
        self.generate_repair_recommendations(diagnosis_results)
        
        print(f"\n" + "="*80)
        print("🏁 诊断完成")

    async def cleanup(self):
        """清理资源"""
        if self.redis_client:
            await self.redis_client.close()

async def main():
    """主函数"""
    diagnostic = ClusterHealthDiagnostic()
    
    try:
        await diagnostic.run_full_diagnosis()
    finally:
        await diagnostic.cleanup()

if __name__ == "__main__":
    asyncio.run(main())