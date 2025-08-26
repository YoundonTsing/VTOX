#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VTOX 集群-后端数据传递一致性测试程序

功能：
1. 测试集群启动脚本与后端8000端口的数据类型一致性
2. 检测数据传递是否阻塞
3. 验证WebSocket和API数据结构完整性

使用方法：
python tests/test_cluster_backend_integration.py
"""

import asyncio
import json
import logging
import time
import websockets
import aiohttp
import redis.asyncio as redis
from typing import Dict, Any, List, Optional
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("integration-test")

class ClusterBackendTester:
    def __init__(self):
        self.backend_url = "http://localhost:8000"
        self.websocket_url = "ws://localhost:8000/ws/frontend"
        self.redis_url = "redis://localhost:6379"
        self.redis_client: Optional[redis.Redis] = None
        self.test_results: List[Dict[str, Any]] = []

    async def initialize(self):
        """初始化测试环境"""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis_client.ping()
            logger.info("✅ Redis连接成功")
            return True
        except Exception as e:
            logger.error(f"❌ Redis连接失败: {e}")
            return False

    async def test_api_connectivity(self):
        """测试API连通性和数据结构"""
        logger.info("🔍 测试API连通性...")
        try:
            async with aiohttp.ClientSession() as session:
                # 测试根端点
                async with session.get(f"{self.backend_url}/") as response:
                    if response.status == 200:
                        data = await response.json()
                        expected_fields = ["message", "status", "version"]
                        missing = [f for f in expected_fields if f not in data]
                        
                        result = {
                            "test": "API根端点",
                            "success": len(missing) == 0,
                            "status_code": response.status,
                            "data_structure": data,
                            "missing_fields": missing
                        }
                        self.test_results.append(result)
                        
                        if result["success"]:
                            logger.info("✅ API根端点测试通过")
                        else:
                            logger.error(f"❌ API根端点缺少字段: {missing}")
                        
                        return result
                    else:
                        logger.error(f"❌ API返回状态码: {response.status}")
                        return {"test": "API根端点", "success": False, "error": f"状态码{response.status}"}
                        
        except Exception as e:
            logger.error(f"❌ API连接失败: {e}")
            return {"test": "API根端点", "success": False, "error": str(e)}

    async def test_websocket_connection(self):
        """测试WebSocket连接和数据传递"""
        logger.info("🔍 测试WebSocket连接...")
        try:
            start_time = time.time()
            
            async with websockets.connect(self.websocket_url) as websocket:
                connection_time = time.time() - start_time
                
                # 发送测试消息
                test_message = {
                    "type": "test",
                    "timestamp": time.time(),
                    "data": "integration_test"
                }
                
                await websocket.send(json.dumps(test_message))
                
                # 尝试接收响应
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response_data = json.loads(response) if response else None
                    
                    result = {
                        "test": "WebSocket连接",
                        "success": True,
                        "connection_time": connection_time,
                        "response_received": response_data is not None,
                        "response_data": response_data
                    }
                    
                except asyncio.TimeoutError:
                    result = {
                        "test": "WebSocket连接",
                        "success": True,  # 连接成功，即使没有立即响应
                        "connection_time": connection_time,
                        "response_received": False,
                        "note": "连接成功但无立即响应"
                    }
                
                self.test_results.append(result)
                logger.info(f"✅ WebSocket连接成功 (耗时: {connection_time:.2f}s)")
                return result
                
        except Exception as e:
            logger.error(f"❌ WebSocket连接失败: {e}")
            result = {"test": "WebSocket连接", "success": False, "error": str(e)}
            self.test_results.append(result)
            return result

    async def test_redis_data_flow(self):
        """测试Redis数据流"""
        logger.info("🔍 测试Redis数据流...")
        try:
            if not self.redis_client:
                result = {"test": "Redis数据流", "success": False, "error": "Redis客户端未初始化"}
                self.test_results.append(result)
                return result
                
            test_stream = "test_integration_stream"
            test_data = {
                "vehicle_id": "TEST_001",
                "timestamp": str(time.time()),
                "sensor_data": json.dumps({"current_a": 1.5, "current_b": 1.4, "current_c": 1.6})
            }
            
            # 写入数据
            start_time = time.time()
            message_id = await self.redis_client.xadd(test_stream, test_data)  # type: ignore
            write_time = time.time() - start_time
            
            # 读取数据
            start_time = time.time()
            messages = await self.redis_client.xrange(test_stream, count=1)
            read_time = time.time() - start_time
            
            # 验证数据一致性
            data_consistent = False
            if messages:
                retrieved_data = messages[0][1]
                data_consistent = (
                    retrieved_data.get("vehicle_id") == test_data["vehicle_id"] and
                    retrieved_data.get("timestamp") == test_data["timestamp"]
                )
            
            # 清理
            await self.redis_client.delete(test_stream)
            
            result = {
                "test": "Redis数据流",
                "success": data_consistent,
                "write_time": write_time,
                "read_time": read_time,
                "data_consistent": data_consistent,
                "messages_count": len(messages)
            }
            
            self.test_results.append(result)
            
            if result["success"]:
                logger.info("✅ Redis数据流测试通过")
            else:
                logger.error("❌ Redis数据一致性检查失败")
                
            return result
            
        except Exception as e:
            logger.error(f"❌ Redis数据流测试失败: {e}")
            result = {"test": "Redis数据流", "success": False, "error": str(e)}
            self.test_results.append(result)
            return result

    async def test_data_blocking(self):
        """检测数据阻塞"""
        logger.info("🔍 检测数据阻塞...")
        try:
            blocking_issues = []
            
            # 1. 测试并发API请求
            concurrent_requests = 10
            start_time = time.time()
            
            async def single_request():
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"{self.backend_url}/") as response:
                            return response.status == 200
                except:
                    return False
            
            tasks = [single_request() for _ in range(concurrent_requests)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            concurrent_time = time.time() - start_time
            
            success_count = sum(1 for r in results if r is True)
            success_rate = success_count / concurrent_requests
            
            if success_rate < 0.8:
                blocking_issues.append(f"并发API请求成功率低: {success_rate:.2f}")
            
            if concurrent_time > 5:
                blocking_issues.append(f"并发请求耗时过长: {concurrent_time:.2f}s")
            
            # 2. 测试Redis响应时间
            if not self.redis_client:
                blocking_issues.append("Redis客户端未初始化")
                avg_redis_time = 0
            else:
                redis_times = []
                for _ in range(5):
                    start_time = time.time()
                    await self.redis_client.ping()
                    redis_times.append(time.time() - start_time)
                
                avg_redis_time = sum(redis_times) / len(redis_times)
                if avg_redis_time > 0.1:
                    blocking_issues.append(f"Redis响应时间过长: {avg_redis_time:.3f}s")
            
            result = {
                "test": "数据阻塞检测",
                "success": len(blocking_issues) == 0,
                "blocking_issues": blocking_issues,
                "concurrent_success_rate": success_rate,
                "concurrent_time": concurrent_time,
                "average_redis_time": avg_redis_time
            }
            
            self.test_results.append(result)
            
            if result["success"]:
                logger.info("✅ 未检测到数据阻塞")
            else:
                logger.warning(f"⚠️ 检测到潜在阻塞: {blocking_issues}")
                
            return result
            
        except Exception as e:
            logger.error(f"❌ 数据阻塞检测失败: {e}")
            result = {"test": "数据阻塞检测", "success": False, "error": str(e)}
            self.test_results.append(result)
            return result

    async def test_end_to_end_flow(self):
        """端到端数据流测试"""
        logger.info("🔍 端到端数据流测试...")
        try:
            if not self.redis_client:
                result = {"test": "端到端数据流", "success": False, "error": "Redis客户端未初始化"}
                self.test_results.append(result)
                return result
                
            # 模拟完整数据流：Redis写入 -> 后端处理 -> WebSocket输出
            test_vehicle_id = "E2E_TEST_001"
            test_data = {
                "vehicle_id": test_vehicle_id,
                "sensor_data": json.dumps({
                    "current_a": 1.5,
                    "current_b": 1.4, 
                    "current_c": 1.6,
                    "timestamp": time.time()
                }),
                "test_marker": "e2e_integration_test"
            }
            
            received_data = None
            
            # 同时建立WebSocket连接并写入Redis数据
            async with websockets.connect(self.websocket_url) as websocket:
                # 订阅相关数据流
                subscribe_msg = {
                    "type": "subscribe",
                    "channels": ["diagnosis_results", "system_stats"]
                }
                await websocket.send(json.dumps(subscribe_msg))
                
                # 写入Redis测试数据
                stream_name = "motor_raw_data"
                message_id = await self.redis_client.xadd(stream_name, test_data)  # type: ignore
                
                # 等待处理结果
                for _ in range(3):
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                        data = json.loads(message)
                        
                        if data.get("vehicle_id") == test_vehicle_id:
                            received_data = data
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                
                # 清理测试数据
                await self.redis_client.xdel(stream_name, message_id)
            
            result = {
                "test": "端到端数据流",
                "success": received_data is not None,
                "data_written": True,
                "data_received": received_data is not None,
                "received_data": received_data,
                "vehicle_id_match": received_data.get("vehicle_id") == test_vehicle_id if received_data else False
            }
            
            self.test_results.append(result)
            
            if result["success"]:
                logger.info("✅ 端到端数据流测试通过")
            else:
                logger.warning("⚠️ 端到端数据流未完全验证")
                
            return result
            
        except Exception as e:
            logger.error(f"❌ 端到端测试失败: {e}")
            result = {"test": "端到端数据流", "success": False, "error": str(e)}
            self.test_results.append(result)
            return result

    async def run_all_tests(self):
        """运行所有测试"""
        logger.info("🚀 开始集群-后端集成测试")
        
        if not await self.initialize():
            return {"error": "初始化失败"}
        
        # 运行测试套件
        tests = [
            self.test_api_connectivity(),
            self.test_websocket_connection(),
            self.test_redis_data_flow(),
            self.test_data_blocking(),
            self.test_end_to_end_flow()
        ]
        
        for test in tests:
            await test
            await asyncio.sleep(1)  # 测试间隔
        
        return self.generate_report()

    def generate_report(self):
        """生成测试报告"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.get("success", False))
        
        print("\n" + "="*60)
        print("🏁 VTOX 集群-后端数据传递一致性测试报告")
        print("="*60)
        print(f"📊 总测试数: {total_tests}")
        print(f"✅ 通过: {passed_tests}")
        print(f"❌ 失败: {total_tests - passed_tests}")
        print(f"📈 成功率: {passed_tests/total_tests*100:.1f}%")
        
        print("\n📋 详细结果:")
        for result in self.test_results:
            status = "✅" if result.get("success") else "❌"
            print(f"{status} {result['test']}")
            if not result.get("success") and "error" in result:
                print(f"   错误: {result['error']}")
        
        # 生成建议
        print("\n💡 建议:")
        failed_tests = [r for r in self.test_results if not r.get("success")]
        
        if not failed_tests:
            print("✅ 所有测试通过，系统运行正常")
        else:
            if any("API" in r["test"] for r in failed_tests):
                print("- 检查后端服务是否在8000端口正常运行")
            if any("WebSocket" in r["test"] for r in failed_tests):
                print("- 检查WebSocket服务配置")
            if any("Redis" in r["test"] for r in failed_tests):
                print("- 检查Redis服务状态")
            if any("阻塞" in r["test"] for r in failed_tests):
                print("- 优化系统性能，检查资源使用情况")
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "success_rate": passed_tests/total_tests,
            "results": self.test_results
        }

    async def cleanup(self):
        """清理资源"""
        if self.redis_client:
            await self.redis_client.close()

async def main():
    """主函数"""
    tester = ClusterBackendTester()
    
    try:
        await tester.run_all_tests()
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())