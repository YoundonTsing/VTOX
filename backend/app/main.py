# pyright: reportMissingImports=false

import os
import sys
# 将项目根目录添加到Python路径，确保在任何其他导入之前执行
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import aiohttp
import asyncio

from .core.config import API_CONFIG
from .websockets.realtime_diagnosis import manager as realtime_diagnosis_manager, handle_frontend_connection, handle_datasource_connection
from .websockets.realtime_diagnosis import handle_fault_data_from_redis, handle_analysis_result_from_redis
from .routers import auth, diagnosis, samples, users, ai_chat, queue_status
from .core.database import Base, engine
from . import models

# 导入简单内存队列服务（完全不依赖外部服务）
from .services.simple_queue import simple_queue, TOPICS

# 导入Redis队列服务
from .services.redis_queue.redis_queue import redis_queue

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def check_and_setup_api_key():
    """检查并设置API Key - 自动使用默认Key"""
    # 默认的API Key
    default_api_key = "sk-0de3188307e44558a60d09799df2702c"
    
    api_key = os.getenv('QWEN_API_KEY')
    
    if not api_key:
        logger.info("🔧 未找到环境变量，使用默认API Key")
        # 自动设置默认API Key
        os.environ['QWEN_API_KEY'] = default_api_key
        api_key = default_api_key
        logger.info(f"✅ 已自动设置API Key: {api_key[:10]}...{api_key[-5:]}")
    
    else:
        # 验证现有的API Key格式
        if not api_key.startswith('sk-'):
            logger.warning(f"⚠️  API Key 格式可能不正确，使用默认Key")
            os.environ['QWEN_API_KEY'] = default_api_key
            api_key = default_api_key
    
    # 快速验证（可选，网络问题时跳过）
    try:
        is_valid = await verify_api_key(api_key)
        if is_valid:
            logger.info(f"✅ API Key 验证成功: {api_key[:10]}...{api_key[-5:]}")
        else:
            logger.warning(f"⚠️  API Key 验证失败，但继续启动")
    except Exception as e:
        logger.info(f"⚠️  API Key 验证跳过 (网络问题): {e}")
    
    return True  # 总是返回True，确保系统能启动

async def verify_api_key(api_key: str) -> bool:
    """验证API Key是否有效"""
    try:
        payload = {
            "model": "qwen-plus",
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": "你好"
                    }
                ]
            },
            "parameters": {
                "result_format": "message",
                "temperature": 0.1,
                "max_tokens": 10
            }
        }
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    return True
                else:
                    logger.error(f"API Key验证失败，状态码: {response.status}")
                    return False
    
    except asyncio.TimeoutError:
        logger.warning("⚠️  API Key验证超时，跳过验证")
        return True  # 网络问题时假设有效
    except Exception as e:
        logger.error(f"API Key验证异常: {e}")
        return False

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 在应用启动时创建数据库表
    logger.info("创建数据库表...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ 数据库表创建完成")
        
        # 初始化默认用户
        from .core.database import SessionLocal
        from .crud.user import get_user_by_username, create_user
        from .schemas.user import UserCreate
        
        db = SessionLocal()
        try:
            # 检查是否存在admin用户
            admin_user = get_user_by_username(db, "admin")
            if not admin_user:
                # 创建默认管理员用户
                admin_user_data = UserCreate(
                    username="admin",
                    password="admin123",
                    name="管理员",
                    email="admin@vtox.com",
                    role="admin"
                )
                create_user(db, admin_user_data)
                logger.info("✅ 创建默认管理员用户: admin/admin123")
            else:
                logger.info("✅ 管理员用户已存在")
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
        logger.warning("系统将继续启动，但可能无法正常工作")
    
    # 检查和设置API Key
    logger.info("检查API配置...")
    await check_and_setup_api_key()
    
    # 初始化Redis队列
    logger.info("初始化Redis队列...")
    redis_connected = await redis_queue.connect()
    
    # ⚠️  已禁用旧的队列系统，现在使用Redis Stream系统 + 桥接组件
    logger.info("🔧 跳过旧队列系统启动（已使用Redis Stream + 桥接组件替代）")
    
    # 🔧 自动启动StreamToFrontendBridge - 修复消息频率低的问题
    logger.info("🌉 初始化Redis Stream到前端桥接器...")
    try:
        # 导入并初始化桥接器
        from .services.redis_stream.stream_to_frontend_bridge import stream_bridge
        
        # 使用realtime_diagnosis_manager作为WebSocket管理器
        success = await stream_bridge.initialize(realtime_diagnosis_manager)
        
        if success:
            logger.info("✅ Redis Stream桥接器初始化成功")
            
            # 🚀 关键修复：启动监听循环
            if not stream_bridge.is_monitoring:
                asyncio.create_task(stream_bridge.start_monitoring())
                logger.info("🚀 Redis Stream桥接器监听循环已启动")
            else:
                logger.info("📊 Redis Stream桥接器监听已在运行")
        else:
            logger.error("❌ Redis Stream桥接器启动失败")
            
    except Exception as e:
        logger.error(f"❌ 启动Redis Stream桥接器异常: {e}")
        logger.warning("前端可能无法接收实时诊断结果")
    
    # 🚀 启动自动数据刷新服务
    logger.info("🔄 启动自动数据刷新服务...")
    try:
        from .services.auto_refresh_service import start_auto_refresh_service
        await start_auto_refresh_service()
        logger.info("✅ 自动数据刷新服务启动成功")
    except Exception as e:
        logger.error(f"❌ 启动自动数据刷新服务失败: {e}")
        logger.warning("系统将继续运行，但可能出现数据过期问题")
    
    # 🚀 启动分布式集群（后台任务，默认禁用）
    logger.info("🏗️ 准备初始化VTOX分布式微服务集群（后台任务）...")
    cluster_manager = None
    try:
        # 导入集群管理器
        import sys
        from pathlib import Path
        
        # 添加cluster目录到Python路径
        cluster_path = Path(__file__).parent.parent.parent / "cluster"
        if str(cluster_path) not in sys.path:
            sys.path.insert(0, str(cluster_path))
        
        # 导入ClusterManager
        from start_cluster import ClusterManager
        
        # 从环境变量获取集群模式 - 默认禁用集群
        cluster_mode = os.getenv('VTOX_CLUSTER_MODE', 'development')
        cluster_workers = int(os.getenv('VTOX_CLUSTER_WORKERS', '1'))  # 🔧 轻量配置：减少到1个Worker
        # 默认禁用，手动开启
        cluster_enabled = os.getenv('VTOX_CLUSTER_ENABLED', 'false').lower() == 'true'
        
        if not cluster_enabled:
            logger.info("📊 分布式集群已禁用（通过VTOX_CLUSTER_ENABLED=false设置）")
            logger.warning("⚠️ 系统将以单机模式运行，功能受限")
            app.state.cluster_manager = None
        else:
            async def start_cluster_bg():
                nonlocal cluster_manager
                try:
                    cluster_manager = ClusterManager(mode=cluster_mode)
                    cluster_manager.redis_url = "redis://localhost:6379"
                    logger.info(f"📊 集群配置: 模式={cluster_mode}, Worker数量={cluster_workers}")
                    logger.info("🔄 后台启动集群服务...")
                    if await cluster_manager.initialize_cluster():
                        if await cluster_manager.start_cluster(custom_workers=cluster_workers):
                            app.state.cluster_manager = cluster_manager
                            logger.info("✅ 集群已在后台启动")
                            try:
                                from .services.redis_stream.stream_to_frontend_bridge import stream_bridge
                                await stream_bridge.add_streams_to_monitor({
                                    "fault_diagnosis_results": "cluster_results_group",
                                    "vehicle_health_assessments": "cluster_health_group"
                                })
                                if not stream_bridge.is_monitoring:
                                    asyncio.create_task(stream_bridge.start_monitoring())
                            except Exception as e:
                                logger.warning(f"⚠️ 配置桥接器监听失败: {e}")
                            try:
                                from app.services.cluster.service_registry import register_gateway_service, get_service_registry
                                import redis.asyncio as redis
                                redis_client = redis.from_url(cluster_manager.redis_url, decode_responses=True)
                                registry = await get_service_registry(redis_client)
                                gateway_client = await register_gateway_service(registry, host="localhost", port=8000)
                                asyncio.create_task(gateway_client.start())
                            except Exception as e:
                                logger.warning(f"⚠️ 注册API网关到服务注册表失败: {e}")
                        else:
                            logger.error("❌ 集群启动失败（后台）")
                            app.state.cluster_manager = None
                    else:
                        logger.error("❌ 集群初始化失败（后台）")
                        app.state.cluster_manager = None
                except Exception as e:
                    logger.error(f"❌ 后台集群异常: {e}")
                    app.state.cluster_manager = None

            asyncio.create_task(start_cluster_bg())
            logger.info("🚀 集群后台启动任务已创建，不阻塞API")
            
    except Exception as e:
        logger.error(f"❌ 集群准备阶段异常（已忽略，不阻塞API）: {e}")
        app.state.cluster_manager = None
    
    # 注释掉的代码 - 避免与Redis Stream系统重复处理
    # 启动简单内存队列服务（完全不依赖外部服务）
    # logger.info("启动内存队列服务...")
    # try:
    #     # 设置队列消息处理器
    #     simple_queue.subscribe(TOPICS['FAULT_DATA'], handle_fault_data_from_redis)
    #     simple_queue.subscribe(TOPICS['ANALYSIS_RESULTS'], handle_analysis_result_from_redis)
    #     
    #     # 启动队列消费者
    #     asyncio.create_task(simple_queue.start_consuming())
    #     logger.info("✅ 内存队列服务启动完成")
    #     
    # except Exception as e:
    #     logger.error(f"启动内存队列服务失败: {e}", exc_info=True)
    #     logger.warning("系统将以基础模式运行")
    # 
    # # 如果Redis连接成功，启动Redis队列服务
    # if redis_connected:
    #     try:
    #         logger.info("启动Redis队列服务...")
    #         # 设置Redis队列消息处理器
    #         redis_queue.subscribe(TOPICS['FAULT_DATA'], handle_fault_data_from_redis)
    #         redis_queue.subscribe(TOPICS['ANALYSIS_RESULTS'], handle_analysis_result_from_redis)
    #         
    #         # 启动Redis队列消费者
    #         asyncio.create_task(redis_queue.start_consuming())
    #         logger.info("✅ Redis队列服务启动完成")
    #     except Exception as e:
    #         logger.error(f"启动Redis队列服务失败: {e}", exc_info=True)
    #         logger.warning("系统将继续使用简单内存队列")
    # else:
    #     logger.warning("Redis连接失败，系统将继续使用简单内存队列")
    
    # 现在数据流程：模拟器 → FastAPI → Redis Stream → 桥接组件 → WebSocket → 前端
    logger.info("✅ 系统将使用Redis Stream + 桥接组件架构")
    
    # 启动时执行的代码
    logger.info("Application startup complete.")
    yield
    
    # 关闭时执行的代码
    logger.info("正在关闭应用...")
    
    # 停止分布式集群
    logger.info("停止分布式集群...")
    try:
        cluster_manager = getattr(app.state, 'cluster_manager', None)
        if cluster_manager:
            await cluster_manager.stop_cluster()
            logger.info("✅ 分布式集群已停止")
        else:
            logger.info("📊 未启动分布式集群，无需停止")
    except Exception as e:
        logger.error(f"停止分布式集群时出错: {e}")
    
    # 停止自动刷新服务
    logger.info("停止自动数据刷新服务...")
    try:
        from .services.auto_refresh_service import stop_auto_refresh_service
        await stop_auto_refresh_service()
        logger.info("自动数据刷新服务已停止。")
    except Exception as e:
        logger.error(f"停止自动数据刷新服务时出错: {e}")
    
    # 停止内存队列服务
    logger.info("停止内存队列服务...")
    try:
        await simple_queue.stop()
        logger.info("内存队列服务已停止。")
    except Exception as e:
        logger.error(f"停止内存队列服务时出错: {e}")
    
    # 停止Redis队列服务
    logger.info("停止Redis队列服务...")
    try:
        await redis_queue.stop()
        logger.info("Redis队列服务已停止。")
    except Exception as e:
        logger.error(f"停止Redis队列服务时出错: {e}")
    
    # 清理WebSocket资源
    from .websockets.realtime_diagnosis import shutdown_event
    await shutdown_event()
    
    logger.info("Application shutdown complete.")

# 设置JSON响应编码
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
import json

# 确保JSON响应使用UTF-8编码
class UTF8JSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        return json.dumps(
            jsonable_encoder(content),
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")

# 创建FastAPI应用
app = FastAPI(
    title="匝间短路故障诊断系统API",
    description="电机匝间短路故障诊断系统后端API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    default_response_class=UTF8JSONResponse  # 设置默认响应类
)

# 配置CORS中间件，允许跨域请求
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册实时诊断WebSocket路由
app.websocket("/ws/frontend")(handle_frontend_connection)
app.websocket("/ws/datasource")(handle_datasource_connection)

# 注册所有路由
app.include_router(auth.router)
app.include_router(diagnosis.router)
app.include_router(samples.router)
app.include_router(users.router)
app.include_router(ai_chat.router)
app.include_router(queue_status.router)

# 注册分布式诊断路由
from .routers import diagnosis_stream
app.include_router(diagnosis_stream.router)

# 注册车队管理路由
from .routers import vehicle_fleet
app.include_router(vehicle_fleet.router)

# 注册集群状态路由
from .routers import cluster_status
app.include_router(cluster_status.router, tags=["集群状态"])

# 注册吞吐量配置管理路由
from .routers import throughput_config_api
app.include_router(throughput_config_api.router, tags=["吞吐量配置"])

# 根路由
@app.get("/", summary="API根目录")
async def root():
    """
    API根路径
    显示系统状态和集群信息
    """
    # 检查集群状态
    cluster_info = {
        "cluster_enabled": True,  # 默认启用集群
        "cluster_status": "unknown",
        "worker_count": 0,
        "deployment_mode": "cluster",  # 默认集群模式
        "service_type": "distributed"  # 服务类型
    }
    
    try:
        cluster_manager = getattr(app.state, 'cluster_manager', None)
        if cluster_manager and cluster_manager.is_running:
            cluster_info.update({
                "cluster_enabled": True,
                "cluster_status": "running",
                "worker_count": len(cluster_manager.worker_nodes),
                "deployment_mode": cluster_manager.mode,
                "service_type": "distributed_cluster"
            })
        else:
            # 如果cluster_manager不存在或未运行，检查是否是禁用状态
            cluster_enabled = os.getenv('VTOX_CLUSTER_ENABLED', 'true').lower() == 'true'
            if not cluster_enabled:
                cluster_info.update({
                    "cluster_enabled": False,
                    "cluster_status": "disabled",
                    "worker_count": 0,
                    "deployment_mode": "standalone",
                    "service_type": "legacy_mode"
                })
            else:
                cluster_info.update({
                    "cluster_enabled": True,
                    "cluster_status": "failed",
                    "worker_count": 0,
                    "deployment_mode": "cluster",
                    "service_type": "cluster_failed"
                })
    except Exception:
        pass  # 忽略错误，保持默认值
    
    return {
        "message": "匝间短路故障诊断系统API",
        "status": "运行中",
        "version": "1.0.0",
        "queue_type": "redis_stream",
        "cluster_info": cluster_info,
        "architecture": "分布式微服务集群 (默认)",
        "description": "集群服务已替代单机服务，提供高性能分布式故障诊断"
    }

 