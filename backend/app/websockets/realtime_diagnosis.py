from fastapi import WebSocket, WebSocketDisconnect
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Set, Deque
from collections import deque
import time
from ..services.analyzer.turn_fault_analyzer import TurnFaultAnalyzer
from ..services.analyzer.broken_bar_analyzer import BrokenBarAnalyzer
from ..services.analyzer.insulation_analyzer import InsulationAnalyzer
from ..services.analyzer.bearing_analyzer import BearingAnalyzer
from ..services.analyzer.eccentricity_analyzer import EccentricityAnalyzer
import random
import pandas as pd # Added for time_series data handling

# 导入简单内存队列服务
from ..services.simple_queue import simple_queue, TOPICS

# 导入轻量级桥接组件
from ..services.redis_stream.stream_to_frontend_bridge import stream_bridge

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("realtime-diagnosis")

class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 按客户端类型存储连接
        self.active_connections: Dict[str, List[WebSocket]] = {
            "frontend": [],  # 前端连接
            "datasource": []  # 数据源连接
        }
        # 诊断器实例
        self.analyzers = {
            "turn_fault": TurnFaultAnalyzer(),
            "broken_bar": BrokenBarAnalyzer(),
            "insulation": InsulationAnalyzer(),
            "bearing": BearingAnalyzer(),
            "eccentricity": EccentricityAnalyzer()
        }
        
        # 数据处理队列 - 增加容量以适应高频数据
        self.data_queue: Deque[dict] = deque(maxlen=1000)  # 最多缓存1000条数据
        
        # 处理状态
        self.is_processing = False
        self.processing_task = None
        
        # 数据处理速率控制 - 提高处理能力
        self.min_processing_rate = 10   # 最小处理速率（每秒）
        self.max_processing_rate = 50   # 最大处理速率（每秒）
        self.target_processing_rate = 25  # 目标处理速率（每秒）
        self.last_process_time = time.time()
        self.processed_count = 0
        
        # 性能监控
        self.processing_times = deque(maxlen=50)  # 存储最近50次处理时间
        self.last_rate_adjustment = time.time()
        self.rate_adjustment_interval = 5.0  # 每5秒调整一次处理速率
        
        # 数据采样控制
        self.sampling_enabled = True
        self.sampling_rate = 1.0  # 初始采样率100%
        self.last_data_source_id = None
        self.data_source_counter = {}
        self.last_data_timestamp = {}
        self.min_time_between_samples = 0.1  # 同一数据源至少间隔100ms
        
        # 统计信息
        self.stats = {
            "received_count": 0,       # 接收的数据包总数
            "processed_count": 0,      # 处理的数据包总数
            "dropped_count": 0,        # 丢弃的数据包总数
            "sampled_count": 0,        # 采样处理的数据包数
            "error_count": 0,          # 处理错误次数
            "start_time": time.time(), # 启动时间
            "queue_max_length": 0,     # 队列最大长度
            "avg_processing_time": 0,  # 平均处理时间
            "max_processing_time": 0,  # 最大处理时间
            "current_sampling_rate": self.sampling_rate, # 当前采样率
            "current_processing_rate": self.target_processing_rate, # 当前处理速率
            "redis_sent_count": 0,     # 发送到Redis的消息数
            "redis_error_count": 0     # Redis发送错误次数
        }
        
        # 状态监控任务
        self.status_monitor_task = None
        
        # Redis集成标志
        self.use_redis = True  # 是否使用Redis
        
        # 启动队列处理任务
        self.start_queue_processor()
        
        # 启动状态监控
        self.start_status_monitor()
        
        # Redis Stream桥接组件标志（延迟初始化）
        self.bridge_initialized = False
    
    async def connect(self, websocket: WebSocket, client_type: str):
        """处理新的WebSocket连接"""
        await websocket.accept()
        if client_type not in self.active_connections:
            self.active_connections[client_type] = []
        self.active_connections[client_type].append(websocket)
        logger.info(f"{client_type} 客户端已连接，当前连接数: {len(self.active_connections[client_type])}")
        
        # 确保队列处理器正在运行
        self.start_queue_processor()
        # 确保状态监控正在运行
        self.start_status_monitor()
        
        # 启动Redis Stream桥接组件（仅在前端连接且未初始化时）
        if client_type == "frontend" and not self.bridge_initialized:
            # 检查全局桥接器是否已初始化
            try:
                from ..services.redis_stream.stream_to_frontend_bridge import stream_bridge
                if stream_bridge.redis_client is not None:
                    # 全局桥接器已初始化，标记为已初始化状态
                    self.bridge_initialized = True
                    logger.info("🔗 检测到全局Redis Stream桥接器已初始化，跳过重复初始化")
                else:
                    # 需要初始化桥接器
                    self.start_stream_bridge()
            except Exception as e:
                logger.warning(f"⚠️ 检查桥接器状态失败: {e}，尝试重新初始化")
                self.start_stream_bridge()
    
    def disconnect(self, websocket: WebSocket, client_type: str):
        """处理WebSocket连接断开"""
        if websocket in self.active_connections.get(client_type, []):
            self.active_connections[client_type].remove(websocket)
            logger.info(f"{client_type} 客户端已断开，当前连接数: {len(self.active_connections[client_type])}")
    
    def start_queue_processor(self):
        """启动队列处理器"""
        try:
            # 检查是否已有运行中的任务
            if self.processing_task is None or self.processing_task.done():
                try:
                    # 尝试获取当前事件循环
                    loop = asyncio.get_running_loop()
                    self.processing_task = loop.create_task(self.process_queue())
                    logger.info("队列处理器已启动")
                except RuntimeError:
                    # 没有运行中的事件循环，任务将在WebSocket连接时启动
                    logger.info("队列处理器将在WebSocket连接时启动")
                    self.processing_task = None
        except Exception as e:
            logger.error(f"启动队列处理器失败: {e}")
    
    def adjust_processing_rate(self):
        """动态调整处理速率"""
        now = time.time()
        
        # 每隔一段时间调整一次
        if now - self.last_rate_adjustment < self.rate_adjustment_interval:
            return
            
        self.last_rate_adjustment = now
        
        # 计算平均处理时间
        if not self.processing_times:
            return
            
        avg_processing_time = sum(self.processing_times) / len(self.processing_times)
        queue_size = len(self.data_queue)
        
        # 根据队列长度和处理时间调整速率
        if queue_size > 50 and avg_processing_time < 0.05:
            # 队列较长且处理速度快，增加处理速率
            self.target_processing_rate = min(self.target_processing_rate + 2, self.max_processing_rate)
            logger.info(f"队列较长({queue_size})，增加处理速率至: {self.target_processing_rate}/秒")
        elif queue_size < 10 and avg_processing_time > 0.1:
            # 队列较短且处理速度慢，降低处理速率
            self.target_processing_rate = max(self.target_processing_rate - 1, self.min_processing_rate)
            logger.info(f"处理较慢({avg_processing_time:.3f}s)，降低处理速率至: {self.target_processing_rate}/秒")
        elif queue_size > 80:
            # 队列接近满，大幅增加处理速率
            self.target_processing_rate = self.max_processing_rate
            logger.warning(f"队列接近满({queue_size}/{self.data_queue.maxlen})，处理速率设为最大: {self.target_processing_rate}/秒")
    
    async def process_queue(self):
        """处理队列中的数据"""
        logger.info("开始处理数据队列")
        try:
            while True:
                # 检查队列是否为空
                if not self.data_queue:
                    # 队列为空，等待一段时间
                    await asyncio.sleep(0.1)
                    continue
                
                # 实现速率限制
                current_time = time.time()
                elapsed = current_time - self.last_process_time
                
                if elapsed >= 1.0:  # 每秒重置计数
                    self.last_process_time = current_time
                    self.processed_count = 0
                    # 调整处理速率
                    self.adjust_processing_rate()
                
                if self.processed_count >= self.target_processing_rate:
                    # 达到每秒处理上限，等待到下一秒
                    await asyncio.sleep(max(0, 1.0 - elapsed))
                    continue
                
                # 从队列中获取数据
                if self.data_queue:
                    data = self.data_queue.popleft()
                    
                    # 记录处理开始时间
                    start_time = time.time()
                    
                    # 处理数据
                    await self.process_data(data)
                    
                    # 记录处理时间
                    processing_time = time.time() - start_time
                    self.processing_times.append(processing_time)
                    
                    self.processed_count += 1
                    
                    # 记录队列状态
                    queue_size = len(self.data_queue)
                    if queue_size > 0 and queue_size % 10 == 0:
                        logger.info(f"当前队列中还有 {queue_size} 条数据等待处理，处理速率: {self.target_processing_rate}/秒")
                    
                    # 适当延迟，避免CPU占用过高
                    # 根据处理时间动态调整延迟
                    delay = max(0.01, min(0.05, 0.05 - processing_time))
                    await asyncio.sleep(delay)
        except asyncio.CancelledError:
            logger.info("队列处理器已取消")
        except Exception as e:
            logger.error(f"队列处理器出错: {e}", exc_info=True)
            # 重启处理器
            asyncio.create_task(self.restart_processor())
    
    async def restart_processor(self):
        """重启队列处理器"""
        await asyncio.sleep(1)  # 等待1秒后重启
        self.start_queue_processor()
        logger.info("队列处理器已重启")
    
    def start_status_monitor(self):
        """启动状态监控任务"""
        try:
            # 检查是否已有运行中的任务
            if self.status_monitor_task is None or self.status_monitor_task.done():
                try:
                    # 尝试获取当前事件循环
                    loop = asyncio.get_running_loop()
                    self.status_monitor_task = loop.create_task(self.monitor_status())
                    logger.info("状态监控任务已启动")
                except RuntimeError:
                    # 没有运行中的事件循环，任务将在WebSocket连接时启动
                    logger.info("状态监控任务将在WebSocket连接时启动")
                    self.status_monitor_task = None
        except Exception as e:
            logger.error(f"启动状态监控任务失败: {e}")
    
    async def monitor_status(self):
        """监控系统状态并更新统计信息"""
        try:
            while True:
                # 更新统计信息
                self.update_stats()
                
                # 每30秒记录一次系统状态
                if self.stats["processed_count"] > 0 and self.stats["processed_count"] % 100 == 0:
                    self.log_system_status()
                
                # 每10秒检查一次
                await asyncio.sleep(10)
        except asyncio.CancelledError:
            logger.info("状态监控任务已取消")
        except Exception as e:
            logger.error(f"状态监控任务出错: {e}", exc_info=True)
            # 重启监控任务
            asyncio.create_task(self.restart_monitor())
    
    async def restart_monitor(self):
        """重启状态监控任务"""
        await asyncio.sleep(1)  # 等待1秒后重启
        self.start_status_monitor()
        logger.info("状态监控任务已重启")
    
    def update_stats(self):
        """更新统计信息"""
        # 更新队列最大长度
        current_queue_len = len(self.data_queue)
        self.stats["queue_max_length"] = max(self.stats["queue_max_length"], current_queue_len)
        
        # 更新平均处理时间
        if self.processing_times:
            self.stats["avg_processing_time"] = sum(self.processing_times) / len(self.processing_times)
            self.stats["max_processing_time"] = max(self.processing_times)
        
        # 更新当前采样率和处理速率
        self.stats["current_sampling_rate"] = self.sampling_rate
        self.stats["current_processing_rate"] = self.target_processing_rate
    
    def log_system_status(self):
        """记录系统状态"""
        uptime = time.time() - self.stats["start_time"]
        hours, remainder = divmod(uptime, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
        
        # 计算处理速率
        processing_rate = self.stats["processed_count"] / uptime if uptime > 0 else 0
        
        # 记录状态日志
        logger.info(
            f"系统状态 - 运行时间: {uptime_str}, "
            f"队列: {len(self.data_queue)}/{self.data_queue.maxlen}, "
            f"采样率: {self.sampling_rate:.2f}, "
            f"处理速率: {self.target_processing_rate}/秒, "
            f"平均处理时间: {self.stats['avg_processing_time']*1000:.2f}ms, "
            f"已接收: {self.stats['received_count']}, "
            f"已处理: {self.stats['processed_count']}, "
            f"已丢弃: {self.stats['dropped_count']}, "
            f"平均速率: {processing_rate:.2f}/秒"
        )
    
    async def process_data(self, data: dict):
        """处理单条数据 - 支持多故障模式"""
        try:
            # 检查数据类型
            fault_type = data.get("fault_type", "unknown")
            
            # 如果是多故障数据，需要分别处理每种故障类型
            if fault_type == "multi_fault":
                await self.process_multi_fault_data(data)
                return
            
            # 处理单一故障类型
            await self.process_single_fault_data(data, fault_type)
            
        except Exception as e:
            logger.error(f"处理数据时出错: {e}", exc_info=True)
            self.stats["error_count"] += 1

    async def process_multi_fault_data(self, data: dict):
        """处理多故障混合数据"""
        try:
            active_faults = data.get("active_faults", [])
            fault_severities = data.get("fault_severities", {})
            
            if not active_faults:
                # 如果没有活跃故障，仍然发送基础数据给前端
                await self.send_basic_multi_fault_result(data)
                return
            
            # 收集每个故障类型的分析特征
            fault_features = {}
            
            # 为每个活跃的故障类型生成分析结果
            for fault_type in active_faults:
                if fault_type in self.analyzers:
                    # 创建单故障数据格式供分析器使用
                    single_fault_data = self.extract_single_fault_data(data, fault_type)
                    
                    # 运行分析器获取特征
                    analyzer = self.analyzers[fault_type]
                    analysis_result = analyzer.analyze(single_fault_data)
                    
                    if analysis_result and 'features' in analysis_result:
                        fault_features[fault_type] = analysis_result['features']
                        
                        # 同时发送单独的故障分析结果
                        result = {
                            **analysis_result,
                            "fault_type": fault_type,
                            "data_source": data.get("connection_id", "unknown"),
                            "timestamp": datetime.now().isoformat(),
                            "queue_size": len(self.data_queue),
                            "system_stats": {
                                "sampling_rate": self.sampling_rate,
                                "processing_rate": self.target_processing_rate,
                                "queue_usage": len(self.data_queue) / self.data_queue.maxlen if self.data_queue.maxlen else 0
                            }
                        }
                        
                        # 添加详细调试日志
                        logger.info(f"发送 {fault_type} 分析结果 - 评分: {result.get('score', 0):.3f}, 状态: {result.get('status', 'unknown')}")
                        logger.info(f"{fault_type} 特征数据: {result.get('features', {})}")
                        
                        # 检查频谱数据
                        if 'frequency_spectrum' in result:
                            freq_data = result['frequency_spectrum']
                            freq_len = len(freq_data.get('frequency', []))
                            logger.info(f"{fault_type} 频谱数据已包含，频率点数: {freq_len}")
                            if freq_len == 0:
                                logger.warning(f"{fault_type} 频谱数据为空！")
                        else:
                            logger.warning(f"{fault_type} 分析结果中缺少频谱数据！")
                        
                        # 检查时间序列数据
                        if 'time_series' in result:
                            logger.info(f"{fault_type} 包含时间序列数据")
                        else:
                            logger.info(f"{fault_type} 不包含时间序列数据")
                        
                        await self.broadcast_to_frontends(result)
            
            # 发送综合的多故障结果，包含所有特征
            await self.send_comprehensive_multi_fault_result(data, active_faults, fault_severities, fault_features)
            
        except Exception as e:
            logger.error(f"处理多故障数据时出错: {e}")
            self.stats["error_count"] += 1

    def extract_single_fault_data(self, multi_fault_data: dict, fault_type: str) -> dict:
        """从多故障数据中提取单故障数据格式"""
        # 复制基础数据结构
        single_data = {
            "timestamp": multi_fault_data.get("timestamp"),
            "connection_id": multi_fault_data.get("connection_id", "unknown"),
            "fault_type": fault_type,
            "fault_active": True,
            "fault_severity": multi_fault_data.get("fault_severities", {}).get(fault_type, 0.0),
            "data": multi_fault_data.get("data", []),
            "sampling_rate": multi_fault_data.get("sampling_rate", 8000),
            "batch_size": multi_fault_data.get("batch_size", 0)
        }
        return single_data

    async def send_basic_multi_fault_result(self, data: dict):
        """发送基础多故障结果（无活跃故障时）"""
        basic_result = {
            "fault_type": "multi_fault",
            "data_source": data.get("connection_id", "unknown"),
            "timestamp": datetime.now().isoformat(),
            "status": "normal",
            "score": 0.0,
            "active_faults": [],
            "fault_severities": data.get("fault_severities", {}),
            "system_stats": {
                "sampling_rate": self.sampling_rate,
                "processing_rate": self.target_processing_rate,
                "queue_usage": len(self.data_queue) / self.data_queue.maxlen if self.data_queue.maxlen else 0
            }
        }
        
        # 添加时间序列数据
        if 'data' in data and data['data']:
            df = pd.DataFrame(data['data'])
            if '时间' in df.columns:
                sample_rate = max(1, len(df) // 200)
                time_series = {"time": df['时间'].iloc[::sample_rate].tolist()}
                
                # 添加主要信号
                if all(col in df.columns for col in ['Ia', 'Ib', 'Ic']):
                    time_series["values_a"] = df['Ia'].iloc[::sample_rate].tolist()
                    time_series["values_b"] = df['Ib'].iloc[::sample_rate].tolist()
                    time_series["values_c"] = df['Ic'].iloc[::sample_rate].tolist()
                
                basic_result["time_series"] = time_series
        
        await self.broadcast_to_frontends(basic_result)

    async def send_comprehensive_multi_fault_result(self, data: dict, active_faults: list, fault_severities: dict, fault_features: dict):
        """发送综合多故障分析结果"""
        # 计算综合评分
        max_severity = max(fault_severities.values()) if fault_severities else 0.0
        avg_severity = sum(fault_severities.values()) / len(fault_severities) if fault_severities else 0.0
        
        # 确定整体状态
        if max_severity > 0.7:
            overall_status = "critical"
        elif max_severity > 0.5:
            overall_status = "warning"
        elif max_severity > 0.2:
            overall_status = "attention"
        else:
            overall_status = "normal"
        
        comprehensive_result = {
            "fault_type": "multi_fault",
            "data_source": data.get("connection_id", "unknown"),
            "timestamp": datetime.now().isoformat(),
            "status": overall_status,
            "score": max_severity,
            "avg_score": avg_severity,
            "active_faults": active_faults,
            "fault_severities": fault_severities,
            "fault_count": len(active_faults),
            "fault_features": fault_features, # 添加故障特征
            "system_stats": {
                "sampling_rate": self.sampling_rate,
                "processing_rate": self.target_processing_rate,
                "queue_usage": len(self.data_queue) / self.data_queue.maxlen if self.data_queue.maxlen else 0
            }
        }
        
        # 如果包含匝间短路故障，添加频谱数据
        if 'turn_fault' in active_faults and 'turn_fault' in self.analyzers:
            try:
                # 重新运行匝间短路分析器来获取频谱数据
                single_fault_data = self.extract_single_fault_data(data, 'turn_fault')
                turn_result = self.analyzers['turn_fault'].analyze(single_fault_data)
                if turn_result and 'frequency_spectrum' in turn_result:
                    comprehensive_result['frequency_spectrum'] = turn_result['frequency_spectrum']
                    logger.info(f"添加匝间短路频谱数据到综合结果，频率点数: {len(turn_result['frequency_spectrum'].get('frequency', []))}")
            except Exception as e:
                logger.error(f"获取匝间短路频谱数据时出错: {e}")
        
        # 添加详细的时间序列数据
        if 'data' in data and data['data']:
            df = pd.DataFrame(data['data'])
            if '时间' in df.columns:
                sample_rate = max(1, len(df) // 200)
                time_series = {"time": df['时间'].iloc[::sample_rate].tolist()}
                
                # 添加所有可用的信号
                if all(col in df.columns for col in ['Ia', 'Ib', 'Ic']):
                    time_series["values_a"] = df['Ia'].iloc[::sample_rate].tolist()
                    time_series["values_b"] = df['Ib'].iloc[::sample_rate].tolist()
                    time_series["values_c"] = df['Ic'].iloc[::sample_rate].tolist()
                
                # 添加振动信号
                if 'vibration_x' in df.columns:
                    time_series["vibration_x"] = df['vibration_x'].iloc[::sample_rate].tolist()
                if 'vibration_y' in df.columns:
                    time_series["vibration_y"] = df['vibration_y'].iloc[::sample_rate].tolist()
                
                # 添加绝缘特征
                if 'insulation_resistance' in df.columns:
                    time_series["insulation_resistance"] = df['insulation_resistance'].iloc[::sample_rate].tolist()
                if 'leakage_current' in df.columns:
                    time_series["leakage_current"] = df['leakage_current'].iloc[::sample_rate].tolist()
                
                # 添加温度
                if 'temperature' in df.columns:
                    time_series["temperature"] = df['temperature'].iloc[::sample_rate].tolist()
                
                comprehensive_result["time_series"] = time_series
        
        await self.broadcast_to_frontends(comprehensive_result)

    async def process_single_fault_data(self, data: dict, fault_type: str):
        """处理单一故障数据"""
        # 选择对应的分析器
        analyzer = self.analyzers.get(fault_type)
        if not analyzer:
            logger.warning(f"未找到故障类型 '{fault_type}' 的分析器")
            return
        
        # 分析数据
        result = analyzer.analyze(data)
        
        if result:
            # 添加标准字段，符合数据流逻辑
            result.update({
                "fault_type": fault_type,
                "vehicle_id": data.get("vehicle_id", data.get("connection_id", "unknown")),
                "timestamp": datetime.now().isoformat(),
                "location": data.get("location", self._extract_location_from_vehicle_id(data.get("vehicle_id", ""))),
            })
            
            # 广播到前端
            await self.broadcast_to_frontends(result)
    
    def _extract_location_from_vehicle_id(self, vehicle_id: str) -> str:
        """从车辆ID提取位置信息"""
        if not vehicle_id:
            return "未知位置"
        
        # 地区映射
        location_map = {
            "粤B": "深圳福田区",
            "陕A": "西安高新区", 
            "粤A": "广州天河区",
            "沪A": "上海浦东区",
            "京A": "北京海淀区",
            "苏A": "南京鼓楼区",
            "浙A": "杭州滨江区",
            "川A": "成都高新区",
            "渝A": "重庆渝中区"
        }
        
        for region, location in location_map.items():
            if region in vehicle_id:
                return location
        
        return "未知位置"

    def enqueue_data(self, data: dict) -> bool:
        """将数据加入处理队列，实现背压控制"""
        # 更新统计信息
        self.stats["received_count"] += 1
        
        # 如果启用了Redis，发送原始数据到Redis
        if self.use_redis:
            # 异步发送到Redis，但不等待结果
            asyncio.create_task(self._send_to_redis(data))
        
        # 检查队列是否已满（self.data_queue.maxlen 可能为 None，需要安全比较）
        queue_maxlen = self.data_queue.maxlen if self.data_queue.maxlen is not None else 0
        if queue_maxlen > 0 and len(self.data_queue) >= queue_maxlen:
            if self.use_redis:
                # 如果Redis可用，优先使用Redis处理，跳过本地队列
                logger.info(f"本地队列已满 ({queue_maxlen})，数据已发送至Redis队列处理")
                return True  # 返回成功，因为数据已发送到Redis
            else:
                # Redis不可用时，只能丢弃数据
                logger.warning(f"数据队列已满 ({queue_maxlen})，丢弃数据")
                # 更新统计信息
                self.stats["dropped_count"] += 1
                # 调整采样率
                self.adjust_sampling_rate()
                return False
        
        # 采样控制
        if not self.should_sample_data(data):
            self.stats["sampled_count"] += 1
            return True  # 返回成功但实际不处理
        
        # 加入队列
        self.data_queue.append(data)
        
        # 定期调整采样率
        if random.random() < 0.05:  # 5%的概率调整采样率
            self.adjust_sampling_rate()
            
        return True
    
    async def _send_to_redis(self, data: dict):
        """发送数据到Redis"""
        try:
            success = await simple_queue.send_message(TOPICS['FAULT_DATA'], data)
            if success:
                self.stats["redis_sent_count"] += 1
                logger.debug(f"数据已发送到Redis: {data.get('connection_id', 'unknown')}")
            else:
                self.stats["redis_error_count"] += 1
                logger.warning(f"发送数据到Redis失败")
        except Exception as e:
            logger.error(f"发送数据到Redis时出错: {e}")
            self.stats["redis_error_count"] += 1
    
    async def handle_redis_result(self, result: dict):
        """处理从Redis接收的分析结果"""
        try:
            # 广播结果到前端
            await self.broadcast_to_frontends(result)
            logger.debug(f"从Redis接收的分析结果已广播到前端")
        except Exception as e:
            logger.error(f"处理Redis分析结果时出错: {e}")
    
    def get_system_stats(self) -> dict:
        """获取系统统计信息，用于心跳响应"""
        self.update_stats()
        stats = {
            "uptime": time.time() - self.stats["start_time"],
            "queue_size": len(self.data_queue),
            "queue_capacity": self.data_queue.maxlen,
            "queue_usage": len(self.data_queue) / self.data_queue.maxlen if self.data_queue.maxlen else 0,
            "sampling_rate": self.sampling_rate,
            "processing_rate": self.target_processing_rate,
            "avg_processing_time": self.stats["avg_processing_time"],
            "received_count": self.stats["received_count"],
            "processed_count": self.stats["processed_count"],
            "dropped_count": self.stats["dropped_count"],
            "error_count": self.stats["error_count"]
        }
        
        # 添加Redis相关统计
        if self.use_redis:
            stats.update({
                "redis_enabled": True,
                "redis_sent_count": self.stats["redis_sent_count"],
                "redis_error_count": self.stats["redis_error_count"]
            })
        else:
            stats["redis_enabled"] = False
            
        return stats
    
    def cleanup(self):
        """清理资源"""
        if self.processing_task:
            self.processing_task.cancel()
        if self.status_monitor_task:
            self.status_monitor_task.cancel()
    
    def should_sample_data(self, data: dict) -> bool:
        """决定是否对数据进行采样处理"""
        if not self.sampling_enabled:
            return True
            
        # 获取数据源ID
        source_id = data.get("connection_id", "unknown")
        
        # 检查数据源的上次处理时间
        now = time.time()
        last_time = self.last_data_timestamp.get(source_id, 0)
        if now - last_time < self.min_time_between_samples:
            # 数据太频繁，需要采样
            self.data_source_counter[source_id] = self.data_source_counter.get(source_id, 0) + 1
            
            # 根据采样率决定是否处理
            if random.random() > self.sampling_rate:
                return False
                
        # 更新最后处理时间
        self.last_data_timestamp[source_id] = now
        return True
    
    def adjust_sampling_rate(self):
        """根据队列长度调整采样率"""
        queue_size = len(self.data_queue)
        queue_capacity = self.data_queue.maxlen
        
        # 队列使用率
        usage_ratio = queue_size / queue_capacity if queue_capacity else 0
        
        # 根据队列使用率调整采样率
        if usage_ratio > 0.8:  # 队列使用超过80%
            self.sampling_rate = max(0.1, self.sampling_rate - 0.2)
            logger.warning(f"队列接近满载 ({queue_size}/{queue_capacity})，降低采样率至 {self.sampling_rate:.1f}")
        elif usage_ratio > 0.5:  # 队列使用超过50%
            self.sampling_rate = max(0.3, self.sampling_rate - 0.1)
            logger.info(f"队列负载较高 ({queue_size}/{queue_capacity})，降低采样率至 {self.sampling_rate:.1f}")
        elif usage_ratio < 0.2 and self.sampling_rate < 1.0:  # 队列使用低于20%
            self.sampling_rate = min(1.0, self.sampling_rate + 0.1)
            logger.info(f"队列负载较低 ({queue_size}/{queue_capacity})，提高采样率至 {self.sampling_rate:.1f}")
    
    async def broadcast_to_frontends(self, message: dict):
        """广播消息到所有前端连接"""
        if not self.active_connections["frontend"]:
            return
        
        # 标准化消息格式，符合数据流逻辑
        standardized_message = self._standardize_frontend_message(message)
        
        # 序列化消息
        encoded_message = json.dumps(standardized_message)
        
        # 广播到所有前端
        disconnected = []
        for connection in self.active_connections["frontend"]:
            try:
                await connection.send_text(encoded_message)
            except Exception as e:
                logger.error(f"广播消息失败: {e}")
                disconnected.append(connection)
        
        # 清理断开的连接
        for conn in disconnected:
            self.disconnect(conn, "frontend")
    
    def _standardize_frontend_message(self, message: dict) -> dict:
        """标准化前端消息格式，符合数据流逻辑"""
        # 基础标准格式
        standardized = {
            "fault_type": message.get("fault_type", "unknown"),
            "vehicle_id": message.get("vehicle_id", message.get("data_source", "unknown")),
            "timestamp": message.get("timestamp", datetime.now().isoformat()),
            "status": message.get("status", "unknown"),
            "score": float(message.get("score", 0.0)),  # 确保score为数值类型
        }
        
        # 添加特征数据
        if "features" in message:
            standardized["features"] = message["features"]
        
        # 添加时间序列数据
        if "time_series" in message:
            standardized["time_series"] = message["time_series"]
        
        # 添加频谱数据
        if "frequency_spectrum" in message:
            standardized["spectrum"] = message["frequency_spectrum"]
        elif "spectrum" in message:
            standardized["spectrum"] = message["spectrum"]
        
        # 添加图表数据
        charts = {}
        if "charts" in message:
            charts = message["charts"]
        if "time_domain" in message:
            charts["time_domain"] = message["time_domain"]
        if "frequency_domain" in message:
            charts["frequency_domain"] = message["frequency_domain"]
        if charts:
            standardized["charts"] = charts
        
        # 添加位置信息（如果可用）
        if "location" in message:
            standardized["location"] = message["location"]
        
        # 计算健康评分
        score = standardized["score"]
        if score <= 0.2:
            health_score = 95.0 - (score * 25)  # 正常范围 95-90
        elif score <= 0.5:
            health_score = 90.0 - ((score - 0.2) * 100)  # 警告范围 90-60
        else:
            health_score = 60.0 - ((score - 0.5) * 120)  # 故障范围 60-0
        
        standardized["health_score"] = max(0.0, min(100.0, health_score))
        
        return standardized
    
    def start_stream_bridge(self):
        """启动Redis Stream桥接组件（轻量级数据转发）"""
        if not self.bridge_initialized:
            # 再次检查全局桥接器状态，避免重复初始化
            try:
                from ..services.redis_stream.stream_to_frontend_bridge import stream_bridge
                if stream_bridge.redis_client is not None and stream_bridge.websocket_manager is not None:
                    self.bridge_initialized = True
                    logger.info("🚀 检测到全局桥接器已就绪，跳过重复初始化")
                    return
            except Exception as e:
                logger.debug(f"检查桥接器状态异常: {e}")
            
            # 需要初始化
            asyncio.create_task(self._initialize_stream_bridge())
        else:
            logger.debug("🔗 Redis Stream桥接组件已初始化，跳过启动")
    
    async def _initialize_stream_bridge(self):
        """异步初始化Redis Stream桥接组件"""
        try:
            # 再次检查是否已初始化，避免并发初始化
            if self.bridge_initialized:
                logger.debug("🚀 桥接组件已初始化，取消重复初始化")
                return
            
            logger.info("🔗 初始化Redis Stream到前端桥接组件...")
            
            # 初始化桥接组件
            success = await stream_bridge.initialize(self)
            
            if success:
                self.bridge_initialized = True
                logger.info("✅ Redis Stream桥接组件初始化成功")
                
                # 检查是否需要启动监听任务
                if not stream_bridge.is_monitoring:
                    asyncio.create_task(stream_bridge.start_monitoring())
                    logger.info("🚀 Redis Stream桥接监听已启动")
                else:
                    logger.info("📊 Redis Stream桥接监听已在运行")
            else:
                logger.error("❌ Redis Stream桥接组件初始化失败")
                
        except Exception as e:
            logger.error(f"❌ 启动Redis Stream桥接组件失败: {e}")
            # 不影响主系统运行，继续运行

# 创建连接管理器实例
manager = ConnectionManager()

# 添加心跳响应处理
async def handle_heartbeat(websocket: WebSocket, data: dict):
    """处理心跳请求"""
    try:
        # 获取系统统计信息
        stats = manager.get_system_stats()
        
        response = {
            "type": "heartbeat_response",
            "timestamp": datetime.now().isoformat(),
            "server_time": time.time(),
            "queue_size": len(manager.data_queue),
            "processing_rate": manager.target_processing_rate,
            "sampling_rate": manager.sampling_rate,
            "stats": stats
        }
        await websocket.send_text(json.dumps(response))
    except Exception as e:
        logger.error(f"发送心跳响应失败: {e}")

async def handle_frontend_connection(websocket: WebSocket):
    """处理前端WebSocket连接"""
    await manager.connect(websocket, "frontend")
    try:
        while True:
            # 接收前端命令（如果有）
            data_str = await websocket.receive_text()
            try:
                data = json.loads(data_str)
                
                # 处理心跳请求
                if data.get("type") == "heartbeat":
                    await handle_heartbeat(websocket, data)
                # 这里可以添加处理其他前端命令的逻辑
            except json.JSONDecodeError:
                logger.warning(f"收到无效的JSON数据: {data_str[:100]}")
            
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        manager.disconnect(websocket, "frontend")
    except Exception as e:
        logger.error(f"处理前端连接时出错: {e}", exc_info=True)
        manager.disconnect(websocket, "frontend")

async def handle_datasource_connection(websocket: WebSocket):
    """处理数据源WebSocket连接"""
    await manager.connect(websocket, "datasource")
    try:
        while True:
            # 接收数据源发送的数据
            data_str = await websocket.receive_text()
            data = json.loads(data_str)
            
            # 将数据加入队列
            success = manager.enqueue_data(data)
            
            # 发送确认，包含队列状态（减少确认频率以降低网络负载）
            if success and len(manager.data_queue) % 10 == 0:  # 每10个数据包发送一次确认
                response = {
                    "status": "received_batch",
                    "queue_size": len(manager.data_queue),
                    "timestamp": datetime.now().isoformat(),
                    "processed_count": manager.stats["processed_count"]
                }
                try:
                    await websocket.send_text(json.dumps(response))
                except Exception as e:
                    logger.debug(f"发送确认消息失败: {e}")  # 降级为debug日志
    except WebSocketDisconnect:
        manager.disconnect(websocket, "datasource")
    except Exception as e:
        logger.error(f"处理数据源连接时出错: {e}", exc_info=True)
        manager.disconnect(websocket, "datasource") 

# Redis消息处理函数
async def handle_fault_data_from_redis(data: dict):
    """处理从Redis接收的故障数据"""
    # 这里可以直接处理数据或加入队列
    # 在第一阶段，我们可以简单记录，但不做额外处理
    logger.debug(f"从Redis接收到故障数据: {data.get('connection_id', 'unknown')}")

async def handle_analysis_result_from_redis(result: dict):
    """处理从Redis接收的分析结果"""
    await manager.handle_redis_result(result)

# 应用关闭时清理资源
async def shutdown_event():
    """应用关闭时执行清理"""
    manager.cleanup()
    logger.info("已清理WebSocket连接管理器资源") 