import asyncio
import redis.asyncio as redis
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import math

# 导入各种故障分析器
from ..analyzer.turn_fault_analyzer import TurnFaultAnalyzer
from ..analyzer.insulation_analyzer import InsulationAnalyzer
from ..analyzer.bearing_analyzer import BearingAnalyzer
from ..analyzer.eccentricity_analyzer import EccentricityAnalyzer
from ..analyzer.broken_bar_analyzer import BrokenBarAnalyzer

logger = logging.getLogger("distributed-diagnosis-stream")

class FaultType(Enum):
    """故障类型枚举"""
    TURN_FAULT = "turn_fault"           # 匝间短路诊断
    INSULATION = "insulation"           # 绝缘失效检测
    BEARING = "bearing"                 # 轴承故障诊断
    ECCENTRICITY = "eccentricity"       # 偏心故障诊断
    BROKEN_BAR = "broken_bar"          # 断条故障诊断

@dataclass
class DiagnosisResult:
    """诊断结果数据类"""
    fault_type: str
    timestamp: str
    status: str
    score: float
    features: Dict[str, Any]
    charts: Dict[str, Any]
    consumer_id: str
    processing_time: float

class DistributedDiagnosisStream:
    """基于Redis Stream的分布式故障诊断系统"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client = None
        
        # 流名称定义
        self.streams = {
            "raw_data": "motor_raw_data",           # 原始电机数据流
            "fault_results": "fault_diagnosis_results", # 故障诊断结果流
            "performance_metrics": "performance_metrics", # 性能监控流
            "system_alerts": "system_alerts"        # 系统告警流
        }
        
        # 消费者组配置
        self.consumer_groups = {
            FaultType.TURN_FAULT.value: "turn_fault_diagnosis_group",
            FaultType.INSULATION.value: "insulation_diagnosis_group", 
            FaultType.BEARING.value: "bearing_diagnosis_group",
            FaultType.ECCENTRICITY.value: "eccentricity_diagnosis_group",
            FaultType.BROKEN_BAR.value: "broken_bar_diagnosis_group",
            "aggregator": "result_aggregation_group",
            "monitor": "performance_monitor_group"
        }
        
        # 故障分析器实例
        self.analyzers = {
            FaultType.TURN_FAULT.value: TurnFaultAnalyzer(),
            FaultType.INSULATION.value: InsulationAnalyzer(),
            FaultType.BEARING.value: BearingAnalyzer(),
            FaultType.ECCENTRICITY.value: EccentricityAnalyzer(),
            FaultType.BROKEN_BAR.value: BrokenBarAnalyzer()
        }
        
        # 运行状态
        self.is_running = False
        self.consumer_tasks = []
        
        # 性能统计
        self.stats = {
            "messages_processed": 0,
            "processing_times": {},
            "error_count": 0,
            "start_time": None
        }
        
    async def connect(self):
        """连接Redis并初始化流和消费者组"""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                retry_on_timeout=True,
                health_check_interval=30
            )
            await self.redis_client.ping()
            logger.info("✅ Redis连接成功")
            
            # 初始化流和消费者组
            await self._initialize_streams()
            return True
            
        except Exception as e:
            logger.error(f"❌ Redis连接失败: {e}")
            return False
    
    async def _initialize_streams(self):
        """初始化Redis Stream和消费者组"""
        try:
            # 创建消费者组（如果不存在）
            for fault_type, group_name in self.consumer_groups.items():
                try:
                    await self.redis_client.xgroup_create(
                        self.streams["raw_data"], 
                        group_name, 
                        id="0", 
                        mkstream=True
                    )
                    logger.info(f"✅ 创建消费者组: {group_name}")
                except redis.ResponseError as e:
                    if "BUSYGROUP" in str(e):
                        logger.debug(f"消费者组已存在: {group_name}")
                    else:
                        logger.error(f"创建消费者组失败: {e}")
            
            # 为结果聚合创建消费者组
            try:
                await self.redis_client.xgroup_create(
                    self.streams["fault_results"],
                    self.consumer_groups["aggregator"],
                    id="0",
                    mkstream=True
                )
            except redis.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    logger.error(f"创建结果聚合消费者组失败: {e}")
                    
        except Exception as e:
            logger.error(f"初始化流失败: {e}")
            raise
    
    async def publish_motor_data(self, vehicle_id: str, sensor_data: Dict[str, Any], 
                                metadata: Dict[str, Any] = None) -> bool:
        """发布电机数据到流中"""
        try:
            if not self.redis_client:
                await self.connect()
            
            # 构建消息
            message = {
                "vehicle_id": vehicle_id,
                "timestamp": datetime.now().isoformat(),
                "sensor_data": json.dumps(sensor_data),
                "metadata": json.dumps(metadata or {}),
                "data_type": "motor_sensor_data"
            }
            
            # 发布到原始数据流
            message_id = await self.redis_client.xadd(
                self.streams["raw_data"],
                message,
                maxlen=50000  # 限制流长度防止内存溢出，支持50辆车
            )
            
            logger.debug(f"📤 发布电机数据: 车辆{vehicle_id}, 消息ID: {message_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 发布电机数据失败: {e}")
            return False
    
    async def start_fault_diagnosis_consumer(self, fault_type: FaultType, 
                                           consumer_id: str) -> None:
        """启动特定故障类型的诊断消费者"""
        group_name = self.consumer_groups[fault_type.value]
        analyzer = self.analyzers[fault_type.value]
        
        logger.debug(f"🎯 启动{fault_type.value}诊断消费者: {consumer_id}")
        
        while self.is_running:
            try:
                # 从消费者组读取消息
                messages = await self.redis_client.xreadgroup(
                    group_name,
                    consumer_id,
                    {self.streams["raw_data"]: ">"},
                    count=1,
                    block=1000  # 1秒超时
                )
                
                for stream, msgs in messages:
                    for message_id, fields in msgs:
                        start_time = time.time()
                        
                        try:
                            # 解析消息
                            vehicle_id = fields["vehicle_id"]
                            sensor_data = json.loads(fields["sensor_data"])
                            metadata = json.loads(fields.get("metadata", "{}"))
                            
                            # 执行故障诊断
                            diagnosis_result = await self._diagnose_fault(
                                analyzer, fault_type.value, sensor_data, 
                                vehicle_id, consumer_id
                            )
                            
                            if diagnosis_result:
                                # 发布诊断结果，保留原始sensor_data
                                await self._publish_diagnosis_result(
                                    vehicle_id, diagnosis_result, message_id, sensor_data
                                )
                            
                            # 确认消息处理完成
                            await self.redis_client.xack(
                                self.streams["raw_data"],
                                group_name,
                                message_id
                            )
                            
                            # 记录性能统计
                            processing_time = time.time() - start_time
                            await self._record_performance(
                                fault_type.value, processing_time, consumer_id
                            )
                            
                        except Exception as e:
                            logger.error(f"❌ 处理消息失败 {message_id}: {e}")
                            self.stats["error_count"] += 1
                            
            except Exception as e:
                if "NOGROUP" in str(e):
                    logger.warning(f"消费者组不存在，尝试重新创建: {group_name}")
                    await self._initialize_streams()
                else:
                    logger.error(f"❌ 消费者{consumer_id}读取失败: {e}")
                    await asyncio.sleep(1)
    
    async def _diagnose_fault(self, analyzer, fault_type: str, sensor_data: Dict,
                            vehicle_id: str, consumer_id: str) -> Optional[DiagnosisResult]:
        """执行故障诊断"""
        try:
            start_time = time.time()
            
            # 调用对应的分析器
            result = analyzer.analyze(sensor_data)
            
            processing_time = time.time() - start_time
            
            if result:
                diagnosis_result = DiagnosisResult(
                    fault_type=fault_type,
                    timestamp=result["timestamp"],
                    status=result["status"],
                    score=result["score"],
                    features=result["features"],
                    charts=result.get("charts", {}),
                    consumer_id=consumer_id,
                    processing_time=processing_time
                )
                
                logger.debug(f"✅ {fault_type}诊断完成: 车辆{vehicle_id}, "
                           f"状态{result['status']}, 评分{result['score']:.3f}")
                
                return diagnosis_result
            
        except Exception as e:
            logger.error(f"❌ {fault_type}诊断失败: {e}")
            
        return None
    
    async def _publish_diagnosis_result(self, vehicle_id: str, 
                                      result: DiagnosisResult, 
                                      original_message_id: str,
                                      original_sensor_data: Dict = None) -> None:
        """发布诊断结果到结果流"""
        try:
            result_message = {
                "vehicle_id": vehicle_id,
                "fault_type": result.fault_type,
                "timestamp": result.timestamp,
                "status": result.status,
                "score": str(result.score),  # 保持字符串格式以符合Redis要求
                "features": json.dumps(result.features),
                "charts": json.dumps(result.charts),
                "consumer_id": result.consumer_id,
                "processing_time": str(result.processing_time),
                "original_message_id": original_message_id
            }
            
            # 🔧 关键修复：保留原始sensor_data，包含time_series和frequency_spectrum
            if original_sensor_data:
                result_message["sensor_data"] = json.dumps(original_sensor_data)
            
            await self.redis_client.xadd(
                self.streams["fault_results"],
                result_message,
                maxlen=50000  # 保留更多诊断结果用于分析
            )
            
        except Exception as e:
            logger.error(f"❌ 发布诊断结果失败: {e}")
    
    async def _record_performance(self, fault_type: str, processing_time: float,
                                consumer_id: str) -> None:
        """记录性能指标"""
        try:
            # 发布性能指标到监控流
            performance_data = {
                "metric_type": "processing_time",
                "fault_type": fault_type,
                "consumer_id": consumer_id,
                "processing_time": str(processing_time),
                "timestamp": datetime.now().isoformat(),
                "messages_processed": str(self.stats["messages_processed"])
            }
            
            await self.redis_client.xadd(
                self.streams["performance_metrics"],
                performance_data,
                maxlen=10000
            )
            
            # 更新本地统计
            self.stats["messages_processed"] += 1
            if fault_type not in self.stats["processing_times"]:
                self.stats["processing_times"][fault_type] = []
            
            # 只保留最近100个处理时间
            self.stats["processing_times"][fault_type].append(processing_time)
            if len(self.stats["processing_times"][fault_type]) > 100:
                self.stats["processing_times"][fault_type].pop(0)
                
        except Exception as e:
            logger.error(f"❌ 记录性能指标失败: {e}")
    
    async def start_result_aggregator(self, consumer_id: str = "aggregator_001") -> None:
        """启动结果聚合器 - 将多种故障诊断结果合并"""
        group_name = self.consumer_groups["aggregator"]
        
        logger.debug(f"📊 启动结果聚合器: {consumer_id}")
        
        # 车辆故障状态缓存
        vehicle_states = {}
        
        while self.is_running:
            try:
                messages = await self.redis_client.xreadgroup(
                    group_name,
                    consumer_id,
                    {self.streams["fault_results"]: ">"},
                    count=10,  # 批量处理
                    block=1000
                )
                
                for stream, msgs in messages:
                    for message_id, fields in msgs:
                        try:
                            vehicle_id = fields["vehicle_id"]
                            fault_type = fields["fault_type"]
                            status = fields["status"]
                            score = float(fields["score"])
                            timestamp = fields["timestamp"]
                            
                            # 更新车辆状态
                            if vehicle_id not in vehicle_states:
                                vehicle_states[vehicle_id] = {}
                            
                            vehicle_states[vehicle_id][fault_type] = {
                                "status": status,
                                "score": score,
                                "timestamp": timestamp
                            }
                            
                            # 计算综合健康评分
                            overall_health = await self._calculate_overall_health(
                                vehicle_states[vehicle_id]
                            )
                            
                            # 发布综合评估结果
                            await self._publish_overall_assessment(
                                vehicle_id, overall_health, vehicle_states[vehicle_id]
                            )
                            
                            # 确认消息
                            await self.redis_client.xack(
                                self.streams["fault_results"],
                                group_name,
                                message_id
                            )
                            
                        except Exception as e:
                            logger.error(f"❌ 聚合处理失败 {message_id}: {e}")
                            
            except Exception as e:
                logger.error(f"❌ 结果聚合器读取失败: {e}")
                await asyncio.sleep(1)
    
    async def _calculate_overall_health(self, fault_states: Dict[str, Dict]) -> Dict[str, Any]:
        """计算车辆整体健康状态"""
        total_score = 0.0
        fault_count = 0
        warning_count = 0
        critical_count = 0
        
        # 故障权重（可根据实际情况调整）
        fault_weights = {
            "turn_fault": 0.25,      # 匝间短路
            "insulation": 0.20,      # 绝缘失效
            "bearing": 0.25,         # 轴承故障
            "eccentricity": 0.15,    # 偏心故障
            "broken_bar": 0.15       # 断条故障
        }
        
        for fault_type, state in fault_states.items():
            weight = fault_weights.get(fault_type, 0.2)
            score = state["score"]
            status = state["status"]
            
            # 验证并修复异常的score值
            if not isinstance(score, (int, float)) or math.isnan(score) or math.isinf(score):
                logger.warning(f"发现异常评分值 {fault_type}: {score}，使用默认值0.5")
                score = 0.5
            elif score < 0:
                logger.warning(f"发现负数评分值 {fault_type}: {score}，设置为0")
                score = 0.0
            elif score > 1:
                logger.warning(f"发现超范围评分值 {fault_type}: {score}，限制为1.0")
                score = 1.0
            
            total_score += score * weight
            
            if status == "fault":
                critical_count += 1
            elif status == "warning":
                warning_count += 1
            else:
                fault_count += 1
        
        # 确保total_score在合理范围内 (0-1)
        total_score = max(0.0, min(1.0, total_score))
        
        # 确定整体状态
        if critical_count > 0:
            overall_status = "critical"
        elif warning_count > 1:  # 多个预警
            overall_status = "warning"
        elif warning_count > 0:
            overall_status = "caution"
        else:
            overall_status = "healthy"
        
        # 计算健康评分 (0-100)
        health_score = round(max(0, min(100, 100 - (total_score * 100))), 1)
        
        # 添加调试日志
        logger.debug(f"健康评分计算: total_score={total_score:.3f}, health_score={health_score}%")
        
        return {
            "overall_status": overall_status,
            "health_score": health_score,
            "total_score": total_score,
            "fault_summary": {
                "critical_faults": critical_count,
                "warnings": warning_count,
                "normal": fault_count
            },
            "last_updated": datetime.now().isoformat()
        }
    
    async def _publish_overall_assessment(self, vehicle_id: str, 
                                        overall_health: Dict[str, Any],
                                        fault_states: Dict[str, Dict]) -> None:
        """发布整体评估结果"""
        try:
            assessment_message = {
                "vehicle_id": vehicle_id,
                "assessment_type": "overall_health",
                "overall_health": json.dumps(overall_health),
                "fault_states": json.dumps(fault_states),
                "timestamp": datetime.now().isoformat()
            }
            
            await self.redis_client.xadd(
                "vehicle_health_assessments",
                assessment_message,
                maxlen=20000
            )
            
            # 如果是严重故障，发送告警
            if overall_health["overall_status"] == "critical":
                await self._send_critical_alert(vehicle_id, overall_health, fault_states)
                
        except Exception as e:
            logger.error(f"❌ 发布整体评估失败: {e}")
    
    async def _send_critical_alert(self, vehicle_id: str, 
                                 overall_health: Dict[str, Any],
                                 fault_states: Dict[str, Dict]) -> None:
        """发送严重故障告警"""
        try:
            critical_faults = [
                fault_type for fault_type, state in fault_states.items()
                if state["status"] == "fault"
            ]
            
            alert_message = {
                "alert_type": "critical_fault",
                "vehicle_id": vehicle_id,
                "severity": "high",
                "health_score": str(overall_health["health_score"]),
                "critical_faults": json.dumps(critical_faults),
                "alert_timestamp": datetime.now().isoformat(),
                "requires_immediate_action": "true"
            }
            
            await self.redis_client.xadd(
                self.streams["system_alerts"],
                alert_message,
                maxlen=5000
            )
            
            logger.warning(f"🚨 发送严重故障告警: 车辆{vehicle_id}, "
                         f"健康评分{overall_health['health_score']}, "
                         f"故障类型{critical_faults}")
            
        except Exception as e:
            logger.error(f"❌ 发送告警失败: {e}")
    
    async def start_distributed_system(self, num_consumers_per_fault: int = 2) -> None:
        """启动完整的分布式诊断系统"""
        if self.is_running:
            logger.warning("系统已在运行中")
            return
        
        self.is_running = True
        self.stats["start_time"] = datetime.now()
        
        logger.debug(f"🚀 启动分布式故障诊断系统 - 每种故障类型{num_consumers_per_fault}个消费者")
        
        try:
            # 确保Redis连接
            if not await self.connect():
                raise Exception("无法连接到Redis")
            
            # 为每种故障类型启动多个消费者
            for fault_type in FaultType:
                for i in range(num_consumers_per_fault):
                    consumer_id = f"{fault_type.value}_consumer_{i+1:03d}"
                    task = asyncio.create_task(
                        self.start_fault_diagnosis_consumer(fault_type, consumer_id)
                    )
                    self.consumer_tasks.append(task)
            
            # 启动结果聚合器
            aggregator_task = asyncio.create_task(
                self.start_result_aggregator("main_aggregator")
            )
            self.consumer_tasks.append(aggregator_task)
            
            logger.debug(f"✅ 分布式系统启动完成 - 总共{len(self.consumer_tasks)}个任务")
            
        except Exception as e:
            logger.error(f"❌ 启动分布式系统失败: {e}")
            await self.stop()
            raise
    
    async def stop(self) -> None:
        """停止分布式系统"""
        logger.info("🛑 正在停止分布式诊断系统...")
        
        self.is_running = False
        
        # 取消所有任务
        for task in self.consumer_tasks:
            if not task.done():
                task.cancel()
        
        # 等待所有任务完成
        if self.consumer_tasks:
            await asyncio.gather(*self.consumer_tasks, return_exceptions=True)
        
        # 关闭Redis连接
        if self.redis_client:
            await self.redis_client.close()
        
        self.consumer_tasks.clear()
        logger.info("✅ 分布式系统已停止")
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        if not self.stats["start_time"]:
            return {"status": "not_started"}
        
        uptime = (datetime.now() - self.stats["start_time"]).total_seconds()
        
        # 计算平均处理时间
        avg_processing_times = {}
        for fault_type, times in self.stats["processing_times"].items():
            if times:
                avg_processing_times[fault_type] = sum(times) / len(times)
        
        return {
            "status": "running" if self.is_running else "stopped",
            "uptime_seconds": uptime,
            "messages_processed": self.stats["messages_processed"],
            "error_count": self.stats["error_count"],
            "average_processing_times": avg_processing_times,
            "active_consumers": len(self.consumer_tasks),
            "throughput": self.stats["messages_processed"] / max(uptime, 1) if uptime > 0 else 0
        }

# 全局分布式诊断系统实例
distributed_diagnosis = DistributedDiagnosisStream() 