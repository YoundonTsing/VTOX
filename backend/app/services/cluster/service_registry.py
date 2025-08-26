"""
VTOX 分布式微服务集群 - 服务注册发现机制

设计原则:
1. 最小侵入性 - 现有代码零改动
2. 轻量级实现 - 基于Redis的服务注册
3. 高可用性 - 自动健康检查和故障转移
4. 横向扩展 - 支持动态服务增减
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import redis.asyncio as redis

logger = logging.getLogger("service-registry")

class ServiceType(Enum):
    """服务类型枚举"""
    API_GATEWAY = "api_gateway"
    COORDINATOR = "coordinator"
    WORKER = "worker"
    MONITOR = "monitor"
    BRIDGE = "bridge"

class ServiceStatus(Enum):
    """服务状态枚举"""
    STARTING = "starting"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    SHUTDOWN = "shutdown"

@dataclass
class ServiceInfo:
    """服务信息数据类"""
    service_id: str
    service_type: ServiceType
    service_name: str
    host: str
    port: int
    status: ServiceStatus
    capabilities: List[str]  # 服务能力，如 ["turn_fault", "insulation"]
    metadata: Dict[str, Any]
    last_heartbeat: float
    registered_at: float
    version: str = "1.0.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            **asdict(self),
            "service_type": self.service_type.value,
            "status": self.status.value,
            "last_heartbeat": self.last_heartbeat,
            "registered_at": self.registered_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ServiceInfo':
        """从字典创建实例"""
        return cls(
            service_id=data["service_id"],
            service_type=ServiceType(data["service_type"]),
            service_name=data["service_name"],
            host=data["host"],
            port=data["port"],
            status=ServiceStatus(data["status"]),
            capabilities=data["capabilities"],
            metadata=data["metadata"],
            last_heartbeat=data["last_heartbeat"],
            registered_at=data["registered_at"],
            version=data.get("version", "1.0.0")
        )

class ServiceRegistry:
    """
    轻量级服务注册发现机制
    基于Redis实现，无需外部依赖
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.services_key = "vtox:services"
        self.heartbeat_key = "vtox:heartbeats"
        self.events_key = "vtox:service_events"
        
        # 服务健康检查配置
        self.heartbeat_interval = 5   # 心跳间隔(秒) - 减少到5秒
        self.health_timeout = 20      # 健康超时(秒) - 减少到20秒
        
        # 事件回调
        self.event_callbacks: Dict[str, List[Callable]] = {
            "service_registered": [],
            "service_deregistered": [],
            "service_healthy": [],
            "service_unhealthy": []
        }
        
        # 健康检查任务
        self._health_check_task = None
        self._running = False
    
    async def register_service(self, service_info: ServiceInfo) -> bool:
        """注册服务"""
        try:
            service_info.registered_at = time.time()
            service_info.last_heartbeat = time.time()
            service_info.status = ServiceStatus.HEALTHY
            
            # 存储服务信息
            await self.redis.hset(
                self.services_key,
                service_info.service_id,
                json.dumps(service_info.to_dict())
            )
            
            # 发布服务注册事件
            await self._publish_event("service_registered", service_info.to_dict())
            
            logger.info(f"✅ 服务注册成功: {service_info.service_name}({service_info.service_id})")
            logger.info(f"   📍 地址: {service_info.host}:{service_info.port}")
            logger.info(f"   🛠️ 能力: {service_info.capabilities}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 服务注册失败: {e}")
            return False
    
    async def deregister_service(self, service_id: str) -> bool:
        """注销服务"""
        try:
            # 获取服务信息
            service_data = await self.redis.hget(self.services_key, service_id)
            if not service_data:
                logger.warning(f"⚠️ 尝试注销不存在的服务: {service_id}")
                return False
            
            service_info = ServiceInfo.from_dict(json.loads(service_data))
            service_info.status = ServiceStatus.SHUTDOWN
            
            # 删除服务
            await self.redis.hdel(self.services_key, service_id)
            await self.redis.hdel(self.heartbeat_key, service_id)
            
            # 发布服务注销事件
            await self._publish_event("service_deregistered", service_info.to_dict())
            
            logger.info(f"✅ 服务注销成功: {service_info.service_name}({service_id})")
            return True
            
        except Exception as e:
            logger.error(f"❌ 服务注销失败: {e}")
            return False
    
    async def heartbeat(self, service_id: str) -> bool:
        """发送心跳"""
        try:
            current_time = time.time()
            
            # 更新心跳时间
            await self.redis.hset(
                self.heartbeat_key,
                service_id,
                str(current_time)
            )
            
            # 更新服务状态为健康
            service_data = await self.redis.hget(self.services_key, service_id)
            if service_data:
                service_info = ServiceInfo.from_dict(json.loads(service_data))
                if service_info.status != ServiceStatus.HEALTHY:
                    service_info.status = ServiceStatus.HEALTHY
                    service_info.last_heartbeat = current_time
                    
                    await self.redis.hset(
                        self.services_key,
                        service_id,
                        json.dumps(service_info.to_dict())
                    )
                    
                    await self._publish_event("service_healthy", service_info.to_dict())
                    logger.info(f"💚 服务恢复健康: {service_info.service_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 心跳发送失败: {e}")
            return False
    
    async def get_services(self, service_type: Optional[ServiceType] = None,
                          capabilities: Optional[List[str]] = None,
                          status: Optional[ServiceStatus] = None) -> List[ServiceInfo]:
        """获取服务列表"""
        try:
            all_services = await self.redis.hgetall(self.services_key)
            services = []
            
            for service_id, service_data in all_services.items():
                try:
                    service_info = ServiceInfo.from_dict(json.loads(service_data))
                    
                    # 过滤条件
                    if service_type and service_info.service_type != service_type:
                        continue
                    
                    if status and service_info.status != status:
                        continue
                    
                    if capabilities:
                        if not any(cap in service_info.capabilities for cap in capabilities):
                            continue
                    
                    services.append(service_info)
                    
                except Exception as e:
                    logger.warning(f"⚠️ 解析服务信息失败: {service_id} - {e}")
                    continue
            
            return services
            
        except Exception as e:
            logger.error(f"❌ 获取服务列表失败: {e}")
            return []
    
    async def get_service(self, service_id: str) -> Optional[ServiceInfo]:
        """获取单个服务信息"""
        try:
            service_data = await self.redis.hget(self.services_key, service_id)
            if service_data:
                return ServiceInfo.from_dict(json.loads(service_data))
            return None
            
        except Exception as e:
            logger.error(f"❌ 获取服务信息失败: {e}")
            return None
    
    async def find_service_for_capability(self, capability: str,
                                        prefer_healthy: bool = True) -> Optional[ServiceInfo]:
        """根据能力查找合适的服务"""
        services = await self.get_services(
            capabilities=[capability],
            status=ServiceStatus.HEALTHY if prefer_healthy else None
        )
        
        if not services and prefer_healthy:
            # 如果没有健康的服务，尝试查找其他状态的服务
            services = await self.get_services(capabilities=[capability])
        
        if services:
            # 选择负载最低的服务（可以根据需要实现更复杂的负载均衡策略）
            return min(services, key=lambda s: s.metadata.get("current_load", 0))
        
        return None
    
    async def start_health_monitoring(self):
        """启动健康监控"""
        if self._running:
            logger.warning("⚠️ 健康监控已在运行中")
            return
        
        self._running = True
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("💓 启动服务健康监控")
    
    async def stop_health_monitoring(self):
        """停止健康监控"""
        self._running = False
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 停止服务健康监控")
    
    async def _health_check_loop(self):
        """健康检查循环"""
        while self._running:
            try:
                await self._check_service_health()
                await asyncio.sleep(self.heartbeat_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ 健康检查异常: {e}")
                await asyncio.sleep(5)  # 异常时短暂休息
    
    async def _check_service_health(self):
        """检查所有服务健康状态"""
        try:
            current_time = time.time()
            all_services = await self.redis.hgetall(self.services_key)
            
            for service_id, service_data in all_services.items():
                try:
                    service_info = ServiceInfo.from_dict(json.loads(service_data))
                    
                    # 检查心跳超时
                    heartbeat_data = await self.redis.hget(self.heartbeat_key, service_id)
                    if heartbeat_data:
                        last_heartbeat = float(heartbeat_data)
                        if current_time - last_heartbeat > self.health_timeout:
                            # 服务不健康
                            if service_info.status == ServiceStatus.HEALTHY:
                                service_info.status = ServiceStatus.UNHEALTHY
                                
                                await self.redis.hset(
                                    self.services_key,
                                    service_id,
                                    json.dumps(service_info.to_dict())
                                )
                                
                                await self._publish_event("service_unhealthy", service_info.to_dict())
                                logger.warning(f"💔 服务不健康: {service_info.service_name}")
                    
                    elif service_info.status == ServiceStatus.HEALTHY:
                        # 没有心跳记录但状态为健康，检查是否是刚注册的服务
                        time_since_registration = current_time - service_info.registered_at
                        if time_since_registration > 30:  # 注册超过30秒仍无心跳才警告
                            service_info.status = ServiceStatus.UNHEALTHY
                            
                            await self.redis.hset(
                                self.services_key,
                                service_id,
                                json.dumps(service_info.to_dict())
                            )
                            
                            await self._publish_event("service_unhealthy", service_info.to_dict())
                            logger.warning(f"💔 服务缺失心跳: {service_info.service_name}")
                
                except Exception as e:
                    logger.warning(f"⚠️ 检查服务健康状态失败: {service_id} - {e}")
                    
        except Exception as e:
            logger.error(f"❌ 健康检查失败: {e}")
    
    async def _publish_event(self, event_type: str, service_data: Dict[str, Any]):
        """发布服务事件"""
        try:
            event = {
                "event_type": event_type,
                "service_data": service_data,
                "timestamp": time.time()
            }
            
            await self.redis.lpush(
                self.events_key,
                json.dumps(event)
            )
            
            # 保留最近1000个事件
            await self.redis.ltrim(self.events_key, 0, 999)
            
            # 调用注册的回调函数
            for callback in self.event_callbacks.get(event_type, []):
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(service_data)
                    else:
                        callback(service_data)
                except Exception as e:
                    logger.error(f"❌ 事件回调执行失败: {e}")
            
        except Exception as e:
            logger.error(f"❌ 发布事件失败: {e}")
    
    def add_event_listener(self, event_type: str, callback: Callable):
        """添加事件监听器"""
        if event_type not in self.event_callbacks:
            self.event_callbacks[event_type] = []
        self.event_callbacks[event_type].append(callback)
    
    async def get_service_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        try:
            all_services = await self.get_services()
            
            stats = {
                "total_services": len(all_services),
                "services_by_type": {},
                "services_by_status": {},
                "healthy_services": 0,
                "unhealthy_services": 0
            }
            
            for service in all_services:
                # 按类型统计
                service_type = service.service_type.value
                if service_type not in stats["services_by_type"]:
                    stats["services_by_type"][service_type] = 0
                stats["services_by_type"][service_type] += 1
                
                # 按状态统计
                status = service.status.value
                if status not in stats["services_by_status"]:
                    stats["services_by_status"][status] = 0
                stats["services_by_status"][status] += 1
                
                # 健康状态统计
                if service.status == ServiceStatus.HEALTHY:
                    stats["healthy_services"] += 1
                else:
                    stats["unhealthy_services"] += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ 获取服务统计失败: {e}")
            return {}


class ServiceClient:
    """
    服务客户端 - 用于自动注册和心跳
    """
    
    def __init__(self, registry: ServiceRegistry, service_info: ServiceInfo):
        self.registry = registry
        self.service_info = service_info
        self._heartbeat_task = None
        self._running = False
    
    async def start(self) -> bool:
        """启动服务客户端"""
        try:
            # 注册服务
            success = await self.registry.register_service(self.service_info)
            if not success:
                return False
            
            # 启动心跳
            self._running = True
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            logger.info(f"🚀 服务客户端启动: {self.service_info.service_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 服务客户端启动失败: {e}")
            return False
    
    async def stop(self):
        """停止服务客户端"""
        try:
            self._running = False
            
            # 停止心跳
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
                try:
                    await self._heartbeat_task
                except asyncio.CancelledError:
                    pass
            
            # 注销服务
            await self.registry.deregister_service(self.service_info.service_id)
            
            logger.info(f"🛑 服务客户端停止: {self.service_info.service_name}")
            
        except Exception as e:
            logger.error(f"❌ 服务客户端停止失败: {e}")
    
    async def _heartbeat_loop(self):
        """心跳循环"""
        while self._running:
            try:
                await self.registry.heartbeat(self.service_info.service_id)
                await asyncio.sleep(self.registry.heartbeat_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ 心跳异常: {e}")
                await asyncio.sleep(5)
    
    def update_metadata(self, metadata: Dict[str, Any]):
        """更新服务元数据"""
        self.service_info.metadata.update(metadata)


# 全局服务注册表实例
service_registry: Optional[ServiceRegistry] = None

async def get_service_registry(redis_client: redis.Redis) -> ServiceRegistry:
    """获取全局服务注册表实例"""
    global service_registry
    
    if service_registry is None:
        service_registry = ServiceRegistry(redis_client)
        await service_registry.start_health_monitoring()
    
    return service_registry


def create_service_info(service_type: ServiceType, service_name: str,
                       host: str, port: int, capabilities: List[str],
                       metadata: Optional[Dict[str, Any]] = None) -> ServiceInfo:
    """创建服务信息"""
    return ServiceInfo(
        service_id=f"{service_type.value}_{uuid.uuid4().hex[:8]}",
        service_type=service_type,
        service_name=service_name,
        host=host,
        port=port,
        status=ServiceStatus.STARTING,
        capabilities=capabilities,
        metadata=metadata or {},
        last_heartbeat=0,
        registered_at=0
    )


# 便捷函数
async def register_gateway_service(registry: ServiceRegistry, host: str = "localhost", 
                                 port: int = 8000) -> ServiceClient:
    """注册API Gateway服务"""
    service_info = create_service_info(
        ServiceType.API_GATEWAY,
        "VTOX API Gateway",
        host, port,
        ["api_routing", "load_balancing", "authentication"],
        {"role": "gateway"}
    )
    return ServiceClient(registry, service_info)


async def register_coordinator_service(registry: ServiceRegistry, host: str = "localhost",
                                      port: int = 8001) -> ServiceClient:
    """注册协调器服务"""
    service_info = create_service_info(
        ServiceType.COORDINATOR,
        "VTOX Diagnosis Coordinator",
        host, port,
        ["task_coordination", "load_balancing", "consumer_management"],
        {"role": "coordinator"}
    )
    return ServiceClient(registry, service_info)


async def register_worker_service(registry: ServiceRegistry, host: str, port: int,
                                 fault_types: List[str]) -> ServiceClient:
    """注册Worker服务"""
    service_info = create_service_info(
        ServiceType.WORKER,
        f"VTOX Worker ({','.join(fault_types)})",
        host, port,
        fault_types,
        {"role": "worker", "fault_types": fault_types}
    )
    return ServiceClient(registry, service_info)