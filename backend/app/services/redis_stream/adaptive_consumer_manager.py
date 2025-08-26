#!/usr/bin/env python3
"""
🧠 Redis Stream 自适应消费者管理器
实时监控系统负载，智能调整消费者数量，提供非侵入式的自适应扩展能力
"""

import asyncio
import logging
import time
import json
import psutil
import redis.asyncio as redis
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import deque, defaultdict
import aiohttp
import numpy as np
from enum import Enum
import math

logger = logging.getLogger(__name__)

class ScalingAction(Enum):
    """扩展行为枚举"""
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    MAINTAIN = "maintain"
    EMERGENCY_STOP = "emergency_stop"

@dataclass
class SystemMetrics:
    """系统指标"""
    timestamp: datetime
    # Redis Stream指标
    stream_lengths: Dict[str, int] = field(default_factory=dict)
    consumer_lag: Dict[str, int] = field(default_factory=dict)
    processing_rate: Dict[str, float] = field(default_factory=dict)
    pending_messages: Dict[str, int] = field(default_factory=dict)
    
    # 系统资源指标
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    memory_available_gb: float = 0.0
    
    # 应用指标
    active_consumers: Dict[str, int] = field(default_factory=dict)
    total_consumers: int = 0
    throughput: float = 0.0
    error_rate: float = 0.0
    
    # 网络指标
    redis_latency_ms: float = 0.0
    api_response_time_ms: float = 0.0

@dataclass
class ScalingDecision:
    """扩展决策"""
    action: ScalingAction
    fault_type: str
    current_count: int
    target_count: int
    confidence: float  # 0-1，决策置信度
    reasoning: List[str]  # 决策原因
    priority: int  # 1-10，优先级
    estimated_impact: Dict[str, float]  # 预期影响

@dataclass
class AdaptiveConfig:
    """自适应配置"""
    # 监控配置
    monitoring_interval: int = 15  # 监控间隔（秒）
    metrics_history_size: int = 100  # 历史指标保留数量
    
    # 扩展阈值
    high_load_threshold: float = 0.8  # 高负载阈值
    low_load_threshold: float = 0.3   # 低负载阈值
    cpu_safe_threshold: float = 70.0  # CPU安全阈值
    memory_safe_threshold: float = 80.0  # 内存安全阈值
    
    # 扩展策略
    max_consumers_per_fault: int = 15  # 每种故障最大消费者数
    min_consumers_per_fault: int = 2   # 每种故障最小消费者数
    scale_step_size: int = 2           # 每次扩展步长
    
    # 安全机制
    max_scale_operations_per_hour: int = 6  # 每小时最大扩展操作数
    cooldown_period_minutes: int = 10       # 扩展冷却期
    emergency_stop_error_rate: float = 0.1  # 紧急停止错误率阈值
    
    # 预测参数
    prediction_window_minutes: int = 30     # 预测窗口
    trend_sensitivity: float = 0.7          # 趋势敏感度

class AdaptiveConsumerManager:
    """自适应消费者管理器"""
    
    def __init__(self, 
                 redis_url: str = "redis://localhost:6379",
                 api_base_url: str = "http://localhost:8000",
                 config: Optional[AdaptiveConfig] = None):
        self.redis_url = redis_url
        self.api_base_url = api_base_url
        self.config = config or AdaptiveConfig()
        
        # 连接和认证
        self.redis_client: Optional[redis.Redis] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.auth_token: Optional[str] = None
        
        # 数据存储
        self.metrics_history: deque = deque(maxlen=self.config.metrics_history_size)
        self.scaling_history: List[ScalingDecision] = []
        self.last_scaling_time: Dict[str, datetime] = {}
        
        # 运行状态
        self.is_running = False
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # 故障类型映射
        self.fault_types = [
            "turn_fault", "insulation", "bearing", 
            "eccentricity", "broken_bar"
        ]
        
        # 智能决策引擎
        self.decision_engine = IntelligentDecisionEngine(self.config)
        
        # 统计信息
        self.stats = {
            "total_scaling_operations": 0,
            "successful_scale_ups": 0,
            "successful_scale_downs": 0,
            "prevented_operations": 0,
            "emergency_stops": 0,
            "start_time": None
        }

    async def initialize(self) -> bool:
        """初始化管理器"""
        try:
            logger.info("🧠 初始化自适应消费者管理器...")
            
            # 初始化Redis连接
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            
            # 初始化HTTP会话
            self.session = aiohttp.ClientSession()
            
            # 认证
            if not await self._authenticate():
                logger.error("❌ API认证失败")
                return False
            
            logger.info("✅ 自适应管理器初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 初始化失败: {e}")
            return False

    async def start_adaptive_monitoring(self):
        """启动自适应监控"""
        if self.is_running:
            logger.warning("⚠️ 自适应监控已在运行中")
            return
        
        self.is_running = True
        self.stats["start_time"] = datetime.now()
        
        logger.info("🚀 启动实时自适应扩展监控")
        logger.info(f"📊 监控间隔: {self.config.monitoring_interval}秒")
        logger.info(f"🎯 目标: 智能维持最优消费者数量")
        
        self.monitoring_task = asyncio.create_task(self._adaptive_monitoring_loop())

    async def stop_adaptive_monitoring(self):
        """停止自适应监控"""
        logger.info("🛑 停止自适应监控...")
        
        self.is_running = False
        
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("✅ 自适应监控已停止")

    async def _adaptive_monitoring_loop(self):
        """自适应监控主循环"""
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while self.is_running:
            try:
                # 收集系统指标
                metrics = await self._collect_system_metrics()
                if metrics:
                    self.metrics_history.append(metrics)
                    
                    # 智能决策
                    decisions = await self._make_scaling_decisions(metrics)
                    
                    # 执行决策
                    for decision in decisions:
                        if await self._should_execute_decision(decision):
                            await self._execute_scaling_decision(decision)
                    
                    consecutive_errors = 0
                else:
                    consecutive_errors += 1
                    
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"❌ 监控循环异常: {e}")
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.critical(f"💀 连续{max_consecutive_errors}次错误，停止监控")
                    break
            
            await asyncio.sleep(self.config.monitoring_interval)

    async def _collect_system_metrics(self) -> Optional[SystemMetrics]:
        """收集系统指标"""
        try:
            metrics = SystemMetrics(timestamp=datetime.now())
            
            # Redis Stream指标
            await self._collect_redis_metrics(metrics)
            
            # 系统资源指标
            await self._collect_system_resources(metrics)
            
            # 应用指标
            await self._collect_application_metrics(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ 收集指标失败: {e}")
            return None

    async def _collect_redis_metrics(self, metrics: SystemMetrics):
        """收集Redis Stream指标"""
        try:
            # 获取Stream长度
            stream_names = [
                "motor_raw_data", "fault_diagnosis_results", 
                "vehicle_health_assessments", "performance_metrics", "system_alerts"
            ]
            
            for stream_name in stream_names:
                try:
                    length = await self.redis_client.xlen(stream_name)
                    metrics.stream_lengths[stream_name] = length
                    
                    # 获取消费者组信息
                    groups_info = await self.redis_client.xinfo_groups(stream_name)
                    for group_info in groups_info:
                        group_name = group_info['name'].decode() if isinstance(group_info['name'], bytes) else group_info['name']
                        pending = group_info['pending']
                        
                        # 提取故障类型
                        fault_type = self._extract_fault_type_from_group(group_name)
                        if fault_type:
                            metrics.pending_messages[fault_type] = pending
                            
                except Exception as e:
                    logger.debug(f"跳过Stream {stream_name}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ 收集Redis指标失败: {e}")

    async def _collect_system_resources(self, metrics: SystemMetrics):
        """收集系统资源指标"""
        try:
            # CPU使用率
            metrics.cpu_usage = psutil.cpu_percent(interval=1)
            
            # 内存使用率
            memory = psutil.virtual_memory()
            metrics.memory_usage = memory.percent
            metrics.memory_available_gb = memory.available / (1024**3)
            
            # Redis延迟测试
            start_time = time.time()
            await self.redis_client.ping()
            metrics.redis_latency_ms = (time.time() - start_time) * 1000
            
        except Exception as e:
            logger.error(f"❌ 收集系统资源失败: {e}")

    async def _collect_application_metrics(self, metrics: SystemMetrics):
        """收集应用指标"""
        try:
            # 通过API获取系统状态
            async with self.session.get(
                f"{self.api_base_url}/api/v1/diagnosis-stream/system/status",
                headers=self._get_auth_headers()
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    system_data = data.get("data", {})
                    
                    metrics.total_consumers = system_data.get("active_consumers", 0)
                    metrics.throughput = system_data.get("throughput", 0.0)
                    metrics.error_rate = system_data.get("error_rate", 0.0)
                    
                    # 按故障类型统计消费者数量
                    for fault_type in self.fault_types:
                        # 估算每种故障类型的消费者数量（基于总数平均分配）
                        metrics.active_consumers[fault_type] = metrics.total_consumers // len(self.fault_types)
                        
        except Exception as e:
            logger.debug(f"收集应用指标失败: {e}")

    async def _make_scaling_decisions(self, current_metrics: SystemMetrics) -> List[ScalingDecision]:
        """制定扩展决策"""
        decisions = []
        
        try:
            for fault_type in self.fault_types:
                decision = await self.decision_engine.analyze_fault_type(
                    fault_type, current_metrics, self.metrics_history
                )
                
                if decision and decision.action != ScalingAction.MAINTAIN:
                    decisions.append(decision)
                    
        except Exception as e:
            logger.error(f"❌ 制定决策失败: {e}")
        
        # 按优先级排序
        decisions.sort(key=lambda x: x.priority, reverse=True)
        
        return decisions

    async def _should_execute_decision(self, decision: ScalingDecision) -> bool:
        """判断是否应该执行决策"""
        try:
            # 检查冷却期
            last_scale_time = self.last_scaling_time.get(decision.fault_type)
            if last_scale_time:
                time_since_last = datetime.now() - last_scale_time
                if time_since_last.total_seconds() < self.config.cooldown_period_minutes * 60:
                    logger.info(f"⏳ {decision.fault_type} 在冷却期中，跳过扩展")
                    self.stats["prevented_operations"] += 1
                    return False
            
            # 检查操作频率限制
            recent_operations = len([
                d for d in self.scaling_history 
                if hasattr(d, 'timestamp') and (datetime.now() - d.timestamp) < timedelta(hours=1)
            ])
            
            if recent_operations >= self.config.max_scale_operations_per_hour:
                logger.warning(f"⚠️ 达到每小时最大操作数限制: {recent_operations}")
                self.stats["prevented_operations"] += 1
                return False
            
            # 检查置信度
            if decision.confidence < 0.6:  # 置信度阈值
                logger.info(f"📊 {decision.fault_type} 决策置信度过低: {decision.confidence:.2f}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 决策检查失败: {e}")
            return False

    async def _execute_scaling_decision(self, decision: ScalingDecision):
        """执行扩展决策"""
        try:
            logger.info(f"🎯 执行扩展决策: {decision.fault_type} {decision.action.value}")
            logger.info(f"   📊 当前: {decision.current_count} → 目标: {decision.target_count}")
            logger.info(f"   🧠 置信度: {decision.confidence:.2f}")
            logger.info(f"   💭 原因: {', '.join(decision.reasoning)}")
            
            # 调用现有的扩展API
            success = await self._call_scaling_api(decision.fault_type, decision.target_count)
            
            if success:
                # 记录成功操作
                self.last_scaling_time[decision.fault_type] = datetime.now()
                self.scaling_history.append(decision)
                self.stats["total_scaling_operations"] += 1
                
                if decision.action == ScalingAction.SCALE_UP:
                    self.stats["successful_scale_ups"] += 1
                elif decision.action == ScalingAction.SCALE_DOWN:
                    self.stats["successful_scale_downs"] += 1
                
                logger.info(f"✅ {decision.fault_type} 扩展成功")
                
                # 等待一段时间让变更生效
                await asyncio.sleep(5)
                
            else:
                logger.error(f"❌ {decision.fault_type} 扩展失败")
                
        except Exception as e:
            logger.error(f"❌ 执行扩展决策异常: {e}")

    async def _call_scaling_api(self, fault_type: str, target_count: int) -> bool:
        """调用扩展API"""
        try:
            async with self.session.post(
                f"{self.api_base_url}/api/v1/diagnosis-stream/system/scale",
                params={
                    "fault_type": fault_type,
                    "new_count": target_count
                },
                headers=self._get_auth_headers()
            ) as response:
                return response.status == 200
                
        except Exception as e:
            logger.error(f"❌ API调用失败: {e}")
            return False

    async def _authenticate(self) -> bool:
        """API认证"""
        try:
            async with self.session.post(
                f"{self.api_base_url}/auth/token",
                json={"username": "user1", "password": "password123"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    self.auth_token = result.get("access_token")
                    return True
                return False
        except:
            return False

    def _get_auth_headers(self) -> Dict[str, str]:
        """获取认证头"""
        return {"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}

    def _extract_fault_type_from_group(self, group_name: str) -> Optional[str]:
        """从消费者组名称提取故障类型"""
        for fault_type in self.fault_types:
            if fault_type in group_name:
                return fault_type
        return None

    async def get_adaptive_stats(self) -> Dict[str, Any]:
        """获取自适应管理统计"""
        uptime = (datetime.now() - self.stats["start_time"]).total_seconds() if self.stats["start_time"] else 0
        
        return {
            "status": "running" if self.is_running else "stopped",
            "uptime_seconds": uptime,
            "config": {
                "monitoring_interval": self.config.monitoring_interval,
                "max_consumers_per_fault": self.config.max_consumers_per_fault,
                "cpu_safe_threshold": self.config.cpu_safe_threshold,
                "memory_safe_threshold": self.config.memory_safe_threshold
            },
            "statistics": self.stats,
            "recent_metrics": {
                "total_samples": len(self.metrics_history),
                "latest_cpu_usage": self.metrics_history[-1].cpu_usage if self.metrics_history else 0,
                "latest_memory_usage": self.metrics_history[-1].memory_usage if self.metrics_history else 0,
                "latest_throughput": self.metrics_history[-1].throughput if self.metrics_history else 0
            },
            "recent_decisions": [
                {
                    "fault_type": d.fault_type,
                    "action": d.action.value,
                    "confidence": d.confidence,
                    "reasoning": d.reasoning
                }
                for d in self.scaling_history[-10:]  # 最近10个决策
            ]
        }

    async def cleanup(self):
        """清理资源"""
        try:
            await self.stop_adaptive_monitoring()
            
            if self.redis_client:
                await self.redis_client.close()
            
            if self.session:
                await self.session.close()
            
            logger.info("✅ 自适应管理器资源清理完成")
            
        except Exception as e:
            logger.error(f"❌ 资源清理失败: {e}")


class IntelligentDecisionEngine:
    """智能决策引擎"""
    
    def __init__(self, config: AdaptiveConfig):
        self.config = config

    async def analyze_fault_type(self, 
                               fault_type: str, 
                               current_metrics: SystemMetrics,
                               history: deque) -> Optional[ScalingDecision]:
        """分析特定故障类型的扩展需求"""
        try:
            current_consumers = current_metrics.active_consumers.get(fault_type, 2)
            pending_messages = current_metrics.pending_messages.get(fault_type, 0)
            
            # 计算负载指标
            load_factor = self._calculate_load_factor(current_metrics, fault_type)
            
            # 趋势分析
            trend = self._analyze_trend(history, fault_type)
            
            # 资源检查
            resource_availability = self._check_resource_availability(current_metrics)
            
            # 决策逻辑
            action, target_count, confidence, reasoning = self._make_decision(
                fault_type, current_consumers, load_factor, trend, 
                resource_availability, pending_messages
            )
            
            if action == ScalingAction.MAINTAIN:
                return None
            
            return ScalingDecision(
                action=action,
                fault_type=fault_type,
                current_count=current_consumers,
                target_count=target_count,
                confidence=confidence,
                reasoning=reasoning,
                priority=self._calculate_priority(action, load_factor, pending_messages),
                estimated_impact=self._estimate_impact(action, current_consumers, target_count)
            )
            
        except Exception as e:
            logger.error(f"❌ 分析故障类型 {fault_type} 失败: {e}")
            return None

    def _calculate_load_factor(self, metrics: SystemMetrics, fault_type: str) -> float:
        """计算负载因子"""
        try:
            pending = metrics.pending_messages.get(fault_type, 0)
            consumers = max(metrics.active_consumers.get(fault_type, 1), 1)
            
            # 基于待处理消息数和消费者数计算负载
            base_load = pending / consumers if consumers > 0 else 0
            
            # 考虑系统整体吞吐量
            throughput_factor = min(metrics.throughput / 1000, 1.0)  # 标准化到0-1
            
            # 综合负载因子
            load_factor = (base_load * 0.7 + throughput_factor * 0.3) / 100
            
            return min(load_factor, 1.0)
            
        except Exception:
            return 0.5  # 默认中等负载

    def _analyze_trend(self, history: deque, fault_type: str) -> float:
        """分析趋势（正值表示上升趋势，负值表示下降趋势）"""
        try:
            if len(history) < 5:
                return 0.0
            
            # 取最近的数据点
            recent_data = list(history)[-10:]
            pending_values = [
                m.pending_messages.get(fault_type, 0) for m in recent_data
            ]
            
            if len(pending_values) < 2:
                return 0.0
            
            # 简单线性趋势计算
            x = np.arange(len(pending_values))
            y = np.array(pending_values)
            
            if len(x) > 1:
                slope = np.polyfit(x, y, 1)[0]
                return float(slope)
            
            return 0.0
            
        except Exception:
            return 0.0

    def _check_resource_availability(self, metrics: SystemMetrics) -> Dict[str, bool]:
        """检查资源可用性"""
        return {
            "cpu_available": metrics.cpu_usage < self.config.cpu_safe_threshold,
            "memory_available": metrics.memory_usage < self.config.memory_safe_threshold,
            "redis_responsive": metrics.redis_latency_ms < 100,  # 100ms阈值
        }

    def _make_decision(self, 
                      fault_type: str,
                      current_consumers: int,
                      load_factor: float,
                      trend: float,
                      resource_availability: Dict[str, bool],
                      pending_messages: int) -> Tuple[ScalingAction, int, float, List[str]]:
        """制定决策"""
        
        reasoning = []
        confidence = 0.5
        
        # 紧急情况检查
        if pending_messages > 10000:  # 紧急阈值
            reasoning.append(f"紧急情况：待处理消息数过高 ({pending_messages})")
            if all(resource_availability.values()) and current_consumers < self.config.max_consumers_per_fault:
                target = min(current_consumers + self.config.scale_step_size * 2, self.config.max_consumers_per_fault)
                return ScalingAction.SCALE_UP, target, 0.9, reasoning
        
        # 扩展决策
        if load_factor > self.config.high_load_threshold:
            reasoning.append(f"高负载检测 (负载因子: {load_factor:.2f})")
            confidence += 0.3
            
            if trend > 0:
                reasoning.append(f"上升趋势检测 (趋势: {trend:.2f})")
                confidence += 0.2
            
            if all(resource_availability.values()):
                reasoning.append("系统资源充足")
                confidence += 0.2
            else:
                reasoning.append("系统资源不足，限制扩展")
                confidence -= 0.3
            
            if current_consumers < self.config.max_consumers_per_fault and confidence > 0.6:
                target = min(current_consumers + self.config.scale_step_size, self.config.max_consumers_per_fault)
                return ScalingAction.SCALE_UP, target, confidence, reasoning
        
        # 缩减决策
        elif load_factor < self.config.low_load_threshold:
            reasoning.append(f"低负载检测 (负载因子: {load_factor:.2f})")
            confidence += 0.3
            
            if trend < 0:
                reasoning.append(f"下降趋势检测 (趋势: {trend:.2f})")
                confidence += 0.2
            
            if current_consumers > self.config.min_consumers_per_fault and confidence > 0.6:
                target = max(current_consumers - 1, self.config.min_consumers_per_fault)
                return ScalingAction.SCALE_DOWN, target, confidence, reasoning
        
        # 维持现状
        return ScalingAction.MAINTAIN, current_consumers, 0.8, ["负载正常，维持当前配置"]

    def _calculate_priority(self, action: ScalingAction, load_factor: float, pending_messages: int) -> int:
        """计算优先级"""
        base_priority = 5
        
        if action == ScalingAction.SCALE_UP:
            # 扩展优先级基于负载和待处理消息
            priority = base_priority + int(load_factor * 3) + min(pending_messages // 1000, 2)
        elif action == ScalingAction.SCALE_DOWN:
            # 缩减优先级较低
            priority = max(base_priority - 2, 1)
        else:
            priority = base_priority
        
        return min(priority, 10)

    def _estimate_impact(self, action: ScalingAction, current: int, target: int) -> Dict[str, float]:
        """估算影响"""
        if action == ScalingAction.SCALE_UP:
            improvement_ratio = target / max(current, 1)
            return {
                "throughput_improvement": (improvement_ratio - 1) * 0.8,  # 80%效率
                "latency_reduction": (improvement_ratio - 1) * 0.6,
                "resource_increase": (target - current) * 0.1  # 每个消费者约10%资源
            }
        elif action == ScalingAction.SCALE_DOWN:
            reduction_ratio = current / max(target, 1)
            return {
                "throughput_reduction": (reduction_ratio - 1) * 0.8,
                "resource_savings": (current - target) * 0.1
            }
        
        return {}


# 全局实例
adaptive_consumer_manager = AdaptiveConsumerManager() 