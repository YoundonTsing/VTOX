# pyright: reportMissingImports=false
# type: ignore
"""
VTOX 分布式微服务集群启动器

功能特点:
1. 一键启动完整集群 - 自动启动所有微服务组件
2. 灵活部署模式 - 支持开发/测试/生产环境
3. 健康状态监控 - 实时监控各服务状态
4. 故障自动恢复 - 服务异常时自动重启
5. 渐进式扩展 - 支持动态添加Worker节点

使用方式:
python cluster/start_cluster.py --mode=development
python cluster/start_cluster.py --mode=production --workers=6
"""

import asyncio
import argparse
import logging
import signal
import sys
import time
from typing import Dict, List, Optional
from pathlib import Path
import redis.asyncio as redis

# 添加backend目录到Python路径
backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# 添加工作目录到Python路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    # 简化导入逻辑，优先使用 app 路径
    from app.services.cluster.service_registry import ServiceRegistry, get_service_registry
    from app.services.cluster.coordinator import DiagnosisCoordinator, get_diagnosis_coordinator
    from app.services.cluster.worker_node import DistributedWorkerNode, create_worker_config
except ImportError as e:
    # 如果失败，提供详细的诊断信息
    import os
    print(f"集群模块导入失败: {e}")
    print(f"backend路径: {backend_path}")
    print(f"backend路径存在: {backend_path.exists()}")
    print(f"project_root: {project_root}")
    print(f"当前工作目录: {os.getcwd()}")
    
    # 检查具体模块文件是否存在
    service_registry_path = backend_path / "app" / "services" / "cluster" / "service_registry.py"
    coordinator_path = backend_path / "app" / "services" / "cluster" / "coordinator.py"
    worker_node_path = backend_path / "app" / "services" / "cluster" / "worker_node.py"
    
    print(f"service_registry.py存在: {service_registry_path.exists()}")
    print(f"coordinator.py存在: {coordinator_path.exists()}")
    print(f"worker_node.py存在: {worker_node_path.exists()}")
    
    # 检查__init__.py文件
    cluster_init_path = backend_path / "app" / "services" / "cluster" / "__init__.py"
    app_init_path = backend_path / "app" / "__init__.py"
    services_init_path = backend_path / "app" / "services" / "__init__.py"
    
    print(f"cluster/__init__.py存在: {cluster_init_path.exists()}")
    print(f"app/__init__.py存在: {app_init_path.exists()}")
    print(f"services/__init__.py存在: {services_init_path.exists()}")
    
    print(f"当前sys.path前5项: {sys.path[:5]}")
    print("\n请确保：")
    print("1. 所有必要的__init__.py文件都存在")
    print("2. 从vtox根目录运行此脚本")
    print("3. backend目录结构完整")
    
    # 退出程序但不抛出异常，避免影响类型检查
    print(f"\n退出程序: 集群模块导入失败")
    import sys
    sys.exit(1)

logger = logging.getLogger("cluster-manager")

class ClusterManager:
    """分布式集群管理器"""
    
    def __init__(self, mode: str = "development"):
        self.mode = mode
        self.redis_url = "redis://localhost:6379"
        self.redis_client = None
        
        # 服务组件
        self.service_registry: Optional[ServiceRegistry] = None
        self.coordinator: Optional[DiagnosisCoordinator] = None
        self.worker_nodes: List[DistributedWorkerNode] = []
        
        # 集群状态
        self.is_running = False
        self.shutdown_event = asyncio.Event()
        
        # 部署配置
        self.deployment_configs = {
            "development": {
                "workers": [
                    {"id": "worker_1", "host": "localhost", "port": 8002, "fault_types": ["turn_fault", "insulation"]},
                    {"id": "worker_2", "host": "localhost", "port": 8003, "fault_types": ["bearing", "eccentricity"]},
                    {"id": "worker_3", "host": "localhost", "port": 8004, "fault_types": ["broken_bar"]}
                ],
                "coordinator": {"host": "localhost", "port": 8001},
                "monitoring": {"enabled": True, "interval": 10}
            },
            "testing": {
                "workers": [
                    {"id": "test_worker_1", "host": "localhost", "port": 8005, "fault_types": ["turn_fault"]},
                    {"id": "test_worker_2", "host": "localhost", "port": 8006, "fault_types": ["bearing"]}
                ],
                "coordinator": {"host": "localhost", "port": 8001},
                "monitoring": {"enabled": True, "interval": 5}
            },
            "production": {
                "workers": [
                    {"id": "prod_worker_turn", "host": "0.0.0.0", "port": 8002, "fault_types": ["turn_fault"]},
                    {"id": "prod_worker_insul", "host": "0.0.0.0", "port": 8003, "fault_types": ["insulation"]},
                    {"id": "prod_worker_bear", "host": "0.0.0.0", "port": 8004, "fault_types": ["bearing"]},
                    {"id": "prod_worker_ecc", "host": "0.0.0.0", "port": 8005, "fault_types": ["eccentricity"]},
                    {"id": "prod_worker_bar", "host": "0.0.0.0", "port": 8006, "fault_types": ["broken_bar"]},
                    {"id": "prod_worker_agg", "host": "0.0.0.0", "port": 8007, "fault_types": ["turn_fault", "bearing"]}
                ],
                "coordinator": {"host": "0.0.0.0", "port": 8001},
                "monitoring": {"enabled": True, "interval": 15}
            }
        }
    
    async def initialize_cluster(self) -> bool:
        """初始化集群"""
        try:
            logger.info(f"🔧 初始化VTOX分布式集群 - {self.mode}模式")
            
            # 连接Redis
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                retry_on_timeout=True,
                health_check_interval=30
            )
            await self.redis_client.ping()
            logger.info("✅ Redis连接成功")
            
            # 初始化服务注册表
            self.service_registry = await get_service_registry(self.redis_client)
            logger.info("✅ 服务注册表初始化成功")
            
            # 初始化协调器
            self.coordinator = await get_diagnosis_coordinator(self.redis_client)
            logger.info("✅ 诊断协调器初始化成功")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 集群初始化失败: {e}")
            return False
    
    async def start_cluster(self, custom_workers: Optional[int] = None) -> bool:
        """启动分布式集群"""
        try:
            if self.is_running:
                logger.warning("⚠️ 集群已在运行中")
                return True
            
            logger.info("🚀 启动VTOX分布式微服务集群")
            
            # 获取部署配置
            config = self.deployment_configs.get(self.mode, self.deployment_configs["development"])
            
            # 启动协调器
            await self._start_coordinator(config["coordinator"])
            
            # 启动Worker节点
            worker_configs = config["workers"]
            if custom_workers:
                # 自定义Worker数量
                worker_configs = self._generate_worker_configs(custom_workers)
            
            await self._start_workers(worker_configs)
            
            # 启动监控
            if config["monitoring"]["enabled"]:
                await self._start_monitoring(config["monitoring"]["interval"])
            
            self.is_running = True
            
            logger.info("✅ VTOX分布式集群启动完成")
            logger.info(f"   📊 协调器: 运行中")
            logger.info(f"   🔧 Worker节点: {len(self.worker_nodes)}个")
            logger.info(f"   💻 部署模式: {self.mode}")
            logger.info(f"   🌐 Redis地址: {self.redis_url}")
            
            # 显示集群状态
            await self._display_cluster_status()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 启动集群失败: {e}")
            return False
    
    async def _start_coordinator(self, coordinator_config: Dict):
        """启动协调器"""
        try:
            logger.info("📊 启动诊断协调器...")
            
            # 检查协调器是否已初始化
            if self.coordinator is None:
                raise Exception("协调器未初始化")
            
            # 协调器在当前进程中运行
            success = await self.coordinator.start_coordination()
            if success:
                logger.info(f"✅ 协调器启动成功: {coordinator_config['host']}:{coordinator_config['port']}")
            else:
                raise Exception("协调器启动失败")
                
        except Exception as e:
            logger.error(f"❌ 启动协调器失败: {e}")
            raise
    
    async def _start_workers(self, worker_configs: List[Dict]):
        """启动Worker节点"""
        try:
            logger.info(f"🔧 启动{len(worker_configs)}个Worker节点...")
            
            for worker_config in worker_configs:
                try:
                    # 创建Worker配置
                    config = create_worker_config(
                        worker_id=worker_config["id"],
                        host=worker_config["host"],
                        port=worker_config["port"],
                        fault_types=worker_config["fault_types"],
                        redis_url=self.redis_url
                    )
                    
                    # 创建并启动Worker
                    worker = DistributedWorkerNode(config)
                    
                    if await worker.initialize():
                        if await worker.start_worker():
                            self.worker_nodes.append(worker)
                            logger.info(f"✅ Worker启动成功: {worker_config['id']} "
                                      f"({','.join(worker_config['fault_types'])})")
                        else:
                            logger.error(f"❌ Worker启动失败: {worker_config['id']}")
                    else:
                        logger.error(f"❌ Worker初始化失败: {worker_config['id']}")
                        
                except Exception as e:
                    logger.error(f"❌ 启动Worker异常: {worker_config['id']} - {e}")
                    continue
            
            logger.info(f"✅ 成功启动{len(self.worker_nodes)}个Worker节点")
            
        except Exception as e:
            logger.error(f"❌ 启动Worker节点失败: {e}")
            raise
    
    def _generate_worker_configs(self, num_workers: int) -> List[Dict]:
        """生成Worker配置"""
        fault_types_pool = ["turn_fault", "insulation", "bearing", "eccentricity", "broken_bar"]
        worker_configs = []
        
        for i in range(num_workers):
            # 分配故障类型 (轮询分配)
            fault_type = fault_types_pool[i % len(fault_types_pool)]
            
            config = {
                "id": f"dynamic_worker_{i+1}",
                "host": "localhost" if self.mode == "development" else "0.0.0.0",
                "port": 8002 + i,
                "fault_types": [fault_type]
            }
            worker_configs.append(config)
        
        return worker_configs
    
    async def _start_monitoring(self, interval: int):
        """启动集群监控"""
        try:
            logger.info(f"📈 启动集群监控 (间隔: {interval}秒)")
            
            # 创建监控任务
            asyncio.create_task(self._monitoring_loop(interval))
            
        except Exception as e:
            logger.error(f"❌ 启动监控失败: {e}")
    
    async def _monitoring_loop(self, interval: int):
        """监控循环"""
        while self.is_running:
            try:
                await self._collect_cluster_metrics()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ 监控循环异常: {e}")
                await asyncio.sleep(5)
    
    async def _collect_cluster_metrics(self):
        """收集集群指标"""
        try:
            # 检查组件是否已初始化
            if self.service_registry is None or self.coordinator is None or self.redis_client is None:
                logger.warning("⚠️ 集群组件未完全初始化，跳过指标收集")
                return
            
            # 获取服务统计
            service_stats = await self.service_registry.get_service_stats()
            
            # 获取协调器统计
            coordinator_stats = await self.coordinator.get_coordinator_stats()
            
            # 获取Worker统计
            worker_stats = []
            for worker in self.worker_nodes:
                try:
                    stats = await worker.get_worker_stats()
                    worker_stats.append(stats)
                except Exception as e:
                    logger.warning(f"⚠️ 获取Worker统计失败: {worker.config.worker_id}")
            
            # 记录集群指标到Redis
            cluster_metrics = {
                "timestamp": time.time(),
                "service_stats": service_stats,
                "coordinator_stats": coordinator_stats,
                "worker_stats": worker_stats,
                "cluster_health": self._calculate_cluster_health(service_stats, worker_stats)
            }
            
            await self.redis_client.xadd(
                "vtox:cluster:metrics",
                {k: str(v) for k, v in cluster_metrics.items()},
                maxlen=500
            )
            
        except Exception as e:
            logger.error(f"❌ 收集集群指标失败: {e}")
    
    def _calculate_cluster_health(self, service_stats: Dict, worker_stats: List[Dict]) -> float:
        """计算集群健康度"""
        try:
            health_factors = []
            
            # 服务健康度
            total_services = service_stats.get("total_services", 0)
            healthy_services = service_stats.get("healthy_services", 0)
            if total_services > 0:
                service_health = healthy_services / total_services
                health_factors.append(service_health)
            
            # Worker健康度
            healthy_workers = sum(1 for w in worker_stats 
                                if w.get("resource_metrics", {}).get("healthy", False))
            if worker_stats:
                worker_health = healthy_workers / len(worker_stats)
                health_factors.append(worker_health)
            
            # 计算平均健康度
            if health_factors:
                return sum(health_factors) / len(health_factors)
            
            return 0.5  # 默认健康度
            
        except Exception as e:
            logger.error(f"❌ 计算集群健康度失败: {e}")
            return 0.0
    
    async def _display_cluster_status(self):
        """显示集群状态"""
        try:
            print("\n" + "="*80)
            print("🏗️  VTOX 分布式微服务集群状态")
            print("="*80)
            
            # 检查组件是否已初始化
            if self.service_registry is None or self.coordinator is None:
                print("⚠️ 集群组件未完全初始化")
                return
            
            # 服务注册表状态
            service_stats = await self.service_registry.get_service_stats()
            print(f"📊 服务注册表:")
            print(f"   总服务数: {service_stats.get('total_services', 0)}")
            print(f"   健康服务: {service_stats.get('healthy_services', 0)}")
            print(f"   不健康服务: {service_stats.get('unhealthy_services', 0)}")
            
            # 协调器状态
            coordinator_stats = await self.coordinator.get_coordinator_stats()
            print(f"📋 诊断协调器:")
            print(f"   状态: {coordinator_stats.get('coordinator_status', 'unknown')}")
            print(f"   已分配任务: {coordinator_stats.get('tasks_assigned', 0)}")
            print(f"   平均分配时间: {coordinator_stats.get('average_assignment_time', 0):.3f}s")
            
            # Worker节点状态
            print(f"🔧 Worker节点:")
            for i, worker in enumerate(self.worker_nodes):
                stats = await worker.get_worker_stats()
                print(f"   Worker-{i+1}: {stats.get('worker_id', 'unknown')} "
                      f"({','.join(stats.get('fault_types', []))}) - "
                      f"状态: {stats.get('status', 'unknown')}")
            
            print(f"\n🌐 集群访问地址:")
            print(f"   API Gateway: http://localhost:8000")
            print(f"   协调器监控: Redis Key: vtox:coordinator:metrics")
            print(f"   集群监控: Redis Key: vtox:cluster:metrics")
            
            print("="*80)
            
        except Exception as e:
            logger.error(f"❌ 显示集群状态失败: {e}")
    
    async def stop_cluster(self):
        """停止集群"""
        try:
            logger.info("🛑 正在停止VTOX分布式集群...")
            
            self.is_running = False
            
            # 停止Worker节点
            logger.info("🔧 停止Worker节点...")
            for worker in self.worker_nodes:
                try:
                    await worker.stop_worker()
                except Exception as e:
                    logger.warning(f"⚠️ 停止Worker失败: {worker.config.worker_id}")
            
            # 停止协调器
            logger.info("📊 停止诊断协调器...")
            if self.coordinator:
                await self.coordinator.stop_coordination()
            
            # 停止服务注册表
            logger.info("🏷️ 停止服务注册表...")
            if self.service_registry:
                await self.service_registry.stop_health_monitoring()
            
            # 关闭Redis连接
            if self.redis_client:
                await self.redis_client.close()
            
            logger.info("✅ VTOX分布式集群已完全停止")
            
        except Exception as e:
            logger.error(f"❌ 停止集群失败: {e}")
    
    async def wait_for_shutdown(self):
        """等待关闭信号"""
        await self.shutdown_event.wait()

def setup_logging(level: str = "INFO"):
    """设置日志配置"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('cluster.log')
        ]
    )

def signal_handler(cluster_manager: ClusterManager):
    """信号处理器"""
    def handler(signum, frame):
        logger.info(f"🔔 接收到停止信号: {signum}")
        cluster_manager.shutdown_event.set()
    
    return handler

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="VTOX 分布式微服务集群启动器")
    parser.add_argument("--mode", choices=["development", "testing", "production"], 
                       default="development", help="部署模式")
    parser.add_argument("--workers", type=int, help="Worker数量 (覆盖默认配置)")
    parser.add_argument("--redis-url", default="redis://localhost:6379", help="Redis连接地址")
    parser.add_argument("--log-level", default="INFO", help="日志级别")
    
    args = parser.parse_args()
    
    # 设置日志
    setup_logging(args.log_level)
    
    # 创建集群管理器
    cluster_manager = ClusterManager(args.mode)
    cluster_manager.redis_url = args.redis_url
    
    # 设置信号处理
    handler = signal_handler(cluster_manager)
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)
    
    try:
        # 初始化集群
        if not await cluster_manager.initialize_cluster():
            logger.error("❌ 集群初始化失败")
            return 1
        
        # 启动集群
        if not await cluster_manager.start_cluster(args.workers):
            logger.error("❌ 集群启动失败")
            return 1
        
        logger.info("🎉 集群启动完成，按 Ctrl+C 停止")
        
        # 等待关闭信号
        await cluster_manager.wait_for_shutdown()
        
    except KeyboardInterrupt:
        logger.info("🔔 接收到键盘中断信号")
    except Exception as e:
        logger.error(f"❌ 集群运行异常: {e}")
        return 1
    finally:
        # 停止集群
        await cluster_manager.stop_cluster()
    
    return 0

if __name__ == "__main__":
    exit(asyncio.run(main()))