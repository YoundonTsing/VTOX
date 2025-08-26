from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import asyncio

from ..services.redis_stream.stream_manager import stream_manager
from .auth import get_current_user

router = APIRouter(prefix="/api/v1/diagnosis-stream", tags=["分布式故障诊断"])
logger = logging.getLogger("diagnosis-stream-api")

@router.post("/initialize")
async def initialize_diagnosis_system(
    redis_url: str = "redis://localhost:6379",
    current_user = Depends(get_current_user)
):
    """初始化分布式诊断系统"""
    try:
        success = await stream_manager.initialize(redis_url)
        if success:
            return {
                "status": "success",
                "message": "分布式诊断系统初始化成功",
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="系统初始化失败")
    except Exception as e:
        logger.error(f"初始化失败: {e}")
        raise HTTPException(status_code=500, detail=f"初始化失败: {str(e)}")

@router.post("/start")
async def start_diagnosis_system(
    consumers_per_fault: int = Query(10, description="每种故障类型的消费者数量，支持50辆车"),
    enable_aggregation: bool = Query(True, description="是否启用结果聚合"),
    enable_monitoring: bool = Query(True, description="是否启用性能监控"),
    current_user = Depends(get_current_user)
):
    """启动分布式诊断系统"""
    try:
        config = {
            "consumers_per_fault": consumers_per_fault,
            "enable_aggregation": enable_aggregation,
            "enable_monitoring": enable_monitoring
        }
        
        success = await stream_manager.start_diagnosis_system(config)
        if success:
            return {
                "status": "success",
                "message": "分布式诊断系统启动成功",
                "config": config,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="系统启动失败")
            
    except Exception as e:
        logger.error(f"启动失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动失败: {str(e)}")

@router.post("/vehicles/{vehicle_id}/data")
async def publish_vehicle_data(
    vehicle_id: str,
    sensor_data: Dict[str, Any],
    location: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    current_user = Depends(get_current_user)
):
    
    try:
        # 发布到Redis Stream - 使用正确的方法名
        success = await stream_manager.publish_motor_data(
            vehicle_id=vehicle_id,
            sensor_data=sensor_data,
            location=location or "未知位置",
            additional_metadata=metadata or {}
        )
        
        if success:
            return {
                "status": "success",
                "message": f"车辆 {vehicle_id} 数据发布成功",
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="数据发布失败")
            
    except Exception as e:
        logger.error(f"发布数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"发布数据失败: {str(e)}")

# 性能统计变量 - 用于高频数据调试
_stats = {
    "total_received": 0,
    "total_success": 0,
    "total_errors": 0,
    "start_time": datetime.now(),
    "last_report_time": datetime.now(),
    "last_report_count": 0,
    "vehicle_counters": {}
}

def _print_performance_debug(vehicle_id: str, sensor_data: Dict[str, Any], success: bool):
    """实时性能调试打印"""
    global _stats
    
    _stats["total_received"] += 1
    if success:
        _stats["total_success"] += 1
    else:
        _stats["total_errors"] += 1
    
    # 车辆计数器
    if vehicle_id not in _stats["vehicle_counters"]:
        _stats["vehicle_counters"][vehicle_id] = {"received": 0, "success": 0, "errors": 0}
    
    _stats["vehicle_counters"][vehicle_id]["received"] += 1
    if success:
        _stats["vehicle_counters"][vehicle_id]["success"] += 1
    else:
        _stats["vehicle_counters"][vehicle_id]["errors"] += 1
    
    # 获取数据详情
    data_points = len(sensor_data.get("data", []))
    fault_type = sensor_data.get("fault_type", "unknown")
    sampling_rate = sensor_data.get("sampling_rate", 0)
    
    # 高频数据检测
    is_high_freq = vehicle_id.startswith("HIGH_FREQ") or sampling_rate >= 1000
    
    # 每100个数据包或错误时打印详细信息
    if _stats["total_received"] % 100 == 1 or not success or is_high_freq:
        current_time = datetime.now()
        runtime = (current_time - _stats["start_time"]).total_seconds()
        current_rate = _stats["total_received"] / max(1, runtime)
        
        status_icon = "✅" if success else "❌"
        freq_icon = "⚡" if is_high_freq else "🚗"
        
        logger.info(f"{freq_icon}{status_icon} 模拟器数据接收:")
        logger.info(f"   车辆ID: {vehicle_id}")
        logger.info(f"   数据点数: {data_points}")
        logger.info(f"   故障类型: {fault_type}")
        logger.info(f"   采样率: {sampling_rate} Hz")
        logger.info(f"   处理结果: {'成功' if success else '失败'}")
        
        # 车辆统计
        vehicle_stats = _stats["vehicle_counters"][vehicle_id]
        logger.info(f"   车辆统计: 接收{vehicle_stats['received']} 成功{vehicle_stats['success']} 错误{vehicle_stats['errors']}")
        
        # 每5秒打印总体统计
        interval = (current_time - _stats["last_report_time"]).total_seconds()
        if interval >= 5.0:
            success_rate = _stats["total_success"] / max(1, _stats["total_received"]) * 100
            interval_count = _stats["total_received"] - _stats["last_report_count"]
            interval_rate = interval_count / interval
            
            logger.info(f"📊 后端接收性能统计:")
            logger.info(f"   总接收: {_stats['total_received']}")
            logger.info(f"   成功率: {success_rate:.1f}%")
            logger.info(f"   当前速率: {interval_rate:.1f} 数据包/秒")
            logger.info(f"   平均速率: {current_rate:.1f} 数据包/秒")
            logger.info(f"   运行时间: {runtime:.1f}s")
            logger.info(f"   活跃车辆: {len(_stats['vehicle_counters'])}")
            
            _stats["last_report_time"] = current_time
            _stats["last_report_count"] = _stats["total_received"]

# 为模拟器添加无需认证的专用API端点
@router.post("/simulator/vehicles/{vehicle_id}/data")
async def publish_simulator_vehicle_data(
    vehicle_id: str,
    sensor_data: Dict[str, Any],
    location: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    模拟器专用API端点 - 无需JWT认证
    专为multi_vehicle_simulator.py设计，简化认证流程
    支持高频数据实时调试
    """
    success = False
    try:
        # 自动初始化stream_manager（如果尚未初始化）
        if not stream_manager.is_initialized:
            logger.info("🔧 自动初始化Redis Stream管理器...")
            init_success = await stream_manager.initialize("redis://localhost:6379")
            if not init_success:
                logger.error("❌ Stream管理器初始化失败")
                raise HTTPException(status_code=500, detail="Stream管理器初始化失败")
            logger.info("✅ Stream管理器初始化成功")
        
        # 使用正确的方法名发布到Redis Stream
        success = await stream_manager.publish_motor_data(
            vehicle_id=vehicle_id,
            sensor_data=sensor_data,
            location=location or "模拟器位置",
            additional_metadata={
                **(metadata or {}),
                "source": "multi_vehicle_simulator",
                "auth_bypassed": True,
                "api_receive_time": datetime.now().isoformat()
            }
        )
        
        # 实时调试打印
        _print_performance_debug(vehicle_id, sensor_data, success)
        
        if success:
            return {
                "status": "success", 
                "message": f"模拟器车辆 {vehicle_id} 数据发布成功",
                "timestamp": datetime.now().isoformat(),
                "data_points": len(sensor_data.get("data", [])),
                "processing_stats": {
                    "total_received": _stats["total_received"],
                    "success_rate": _stats["total_success"] / max(1, _stats["total_received"]) * 100
                }
            }
        else:
            raise HTTPException(status_code=500, detail="数据发布失败")
            
    except Exception as e:
        # 错误时也要调试打印
        _print_performance_debug(vehicle_id, sensor_data, False)
        logger.error(f"❌ 模拟器数据发布失败: {vehicle_id} - {e}")
        raise HTTPException(status_code=500, detail=f"发布数据失败: {str(e)}")

@router.get("/vehicles/{vehicle_id}/health")
async def get_vehicle_health(
    vehicle_id: str,
    current_user = Depends(get_current_user)
):
    """获取车辆整体健康状态"""
    try:
        health_status = await stream_manager.get_vehicle_health_status(vehicle_id)
        
        if health_status:
            return {
                "status": "success",
                "data": health_status
            }
        else:
            return {
                "status": "not_found",
                "message": f"未找到车辆{vehicle_id}的健康状态数据",
                "vehicle_id": vehicle_id
            }
            
    except Exception as e:
        logger.error(f"获取健康状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取健康状态失败: {str(e)}")

@router.get("/vehicles/{vehicle_id}/diagnosis-history")
async def get_diagnosis_history(
    vehicle_id: str,
    fault_type: Optional[str] = Query(None, description="故障类型过滤"),
    hours: int = Query(24, description="查询时间范围（小时）"),
    current_user = Depends(get_current_user)
):
    """获取车辆故障诊断历史"""
    try:
        history = await stream_manager.get_fault_diagnosis_history(
            vehicle_id=vehicle_id,
            fault_type=fault_type,
            hours=hours
        )
        
        return {
            "status": "success",
            "data": {
                "vehicle_id": vehicle_id,
                "fault_type_filter": fault_type,
                "time_range_hours": hours,
                "total_records": len(history),
                "diagnosis_history": history
            }
        }
        
    except Exception as e:
        logger.error(f"获取诊断历史失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取诊断历史失败: {str(e)}")

@router.get("/alerts/critical")
async def get_critical_alerts(
    limit: int = Query(10, description="返回告警数量限制"),
    current_user = Depends(get_current_user)
):
    """获取最新的严重故障告警"""
    try:
        alerts = await stream_manager.get_critical_alerts(limit)
        
        return {
            "status": "success",
            "data": {
                "total_alerts": len(alerts),
                "alerts": alerts
            }
        }
        
    except Exception as e:
        logger.error(f"获取告警失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取告警失败: {str(e)}")

@router.get("/system/performance")
async def get_system_performance(
    current_user = Depends(get_current_user)
):
    """获取分布式系统性能统计"""
    try:
        performance = await stream_manager.get_system_performance()
        
        return {
            "status": "success",
            "data": performance
        }
        
    except Exception as e:
        logger.error(f"获取性能统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取性能统计失败: {str(e)}")

@router.post("/system/scale")
async def scale_consumers(
    fault_type: str,
    new_count: int = Query(..., description="新的消费者数量"),
    current_user = Depends(get_current_user)
):
    """动态扩展特定故障类型的消费者数量"""
    try:
        # 验证故障类型
        valid_fault_types = ["turn_fault", "insulation", "bearing", "eccentricity", "broken_bar"]
        if fault_type not in valid_fault_types:
            raise HTTPException(
                status_code=400, 
                detail=f"无效的故障类型。支持的类型: {valid_fault_types}"
            )
        
        if new_count < 1 or new_count > 20:
            raise HTTPException(
                status_code=400,
                detail="消费者数量必须在1-20之间"
            )
        
        success = await stream_manager.scale_consumers(fault_type, new_count)
        
        if success:
            return {
                "status": "success",
                "message": f"成功扩展{fault_type}消费者数量至{new_count}",
                "fault_type": fault_type,
                "new_count": new_count,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="扩展消费者失败")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"扩展消费者失败: {e}")
        raise HTTPException(status_code=500, detail=f"扩展消费者失败: {str(e)}")

@router.post("/system/stop")
async def stop_diagnosis_system(
    current_user = Depends(get_current_user)
):
    """停止分布式诊断系统"""
    try:
        success = await stream_manager.stop_system()
        
        if success:
            return {
                "status": "success",
                "message": "分布式诊断系统已停止",
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="停止系统失败")
            
    except Exception as e:
        logger.error(f"停止系统失败: {e}")
        raise HTTPException(status_code=500, detail=f"停止系统失败: {str(e)}")

@router.get("/fault-types")
async def get_supported_fault_types():
    """获取支持的故障类型列表"""
    fault_types = [
        {
            "type": "turn_fault",
            "name": "匝间短路诊断",
            "description": "检测电机绕组匝间短路故障"
        },
        {
            "type": "insulation",
            "name": "绝缘失效检测", 
            "description": "检测电机绝缘系统失效故障"
        },
        {
            "type": "bearing",
            "name": "轴承故障诊断",
            "description": "检测电机轴承磨损、损坏等故障"
        },
        {
            "type": "eccentricity", 
            "name": "偏心故障诊断",
            "description": "检测电机转子偏心故障"
        },
        {
            "type": "broken_bar",
            "name": "断条故障诊断",
            "description": "检测感应电机转子断条故障"
        }
    ]
    
    return {
        "status": "success",
        "data": {
            "total_types": len(fault_types),
            "fault_types": fault_types
        }
    }

@router.get("/system/status")
async def get_system_status():
    """获取分布式诊断系统状态"""
    try:
        performance = await stream_manager.get_system_performance()
        
        # 提取关键状态信息
        system_stats = performance.get("system_stats", {})
        
        return {
            "status": "success",
            "data": {
                "system_status": system_stats.get("status", "unknown"),
                "uptime_seconds": system_stats.get("uptime_seconds", 0),
                "messages_processed": system_stats.get("messages_processed", 0),
                "error_count": system_stats.get("error_count", 0),
                "active_consumers": system_stats.get("active_consumers", 0),
                "throughput": system_stats.get("throughput", 0),
                "is_initialized": stream_manager.is_initialized,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"获取系统状态失败: {e}")
        return {
            "status": "error",
            "message": f"获取系统状态失败: {str(e)}",
            "data": {
                "system_status": "error",
                "is_initialized": stream_manager.is_initialized,
                "timestamp": datetime.now().isoformat()
            }
        }

# 车队管理API
@router.get("/fleet/overview")
async def get_fleet_overview(
    current_user = Depends(get_current_user)
):
    """获取车队整体概览"""
    try:
        # 这里可以扩展为获取多个车辆的状态汇总
        # 目前返回一个简化的概览
        
        return {
            "status": "success",
            "data": {
                "total_vehicles": 0,  # 需要从Redis中统计
                "healthy_vehicles": 0,
                "warning_vehicles": 0,
                "critical_vehicles": 0,
                "last_updated": datetime.now().isoformat(),
                "message": "车队概览功能正在开发中"
            }
        }
        
    except Exception as e:
        logger.error(f"获取车队概览失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取车队概览失败: {str(e)}")

# 测试和演示API
@router.post("/demo/simulate-vehicle-data")
async def simulate_vehicle_data(
    vehicle_id: str = "DEMO_VEHICLE_001",
    fault_type: Optional[str] = Query(None, description="模拟的故障类型"),
    current_user = Depends(get_current_user)
):
    """模拟车辆数据用于演示分布式诊断系统 - 临时禁用以避免干扰模拟器"""
    
    # 临时禁用演示API，防止干扰外部模拟器数据
    return {
        "status": "disabled",
        "message": "演示API已临时禁用，请使用外部模拟器",
        "timestamp": datetime.now().isoformat()
    }
    
    # 原始代码已注释
    """
    try:
        import numpy as np
        import random
        
        # 生成模拟传感器数据
        time_series = np.linspace(0, 1, 800).tolist()
        
        # 基础三相电流数据
        base_frequency = 50  # Hz
        base_amplitude = 10  # A
        
        # 根据故障类型调整数据特征
        if fault_type == "turn_fault":
            # 匝间短路：三相不平衡
            ia = [base_amplitude * np.sin(2 * np.pi * base_frequency * t) * (1 + 0.1 * random.random()) for t in time_series]
            ib = [base_amplitude * np.sin(2 * np.pi * base_frequency * t - 2 * np.pi / 3) * (1 + 0.2 * random.random()) for t in time_series]
            ic = [base_amplitude * np.sin(2 * np.pi * base_frequency * t + 2 * np.pi / 3) * (1 + 0.05 * random.random()) for t in time_series]
        elif fault_type == "bearing":
            # 轴承故障：添加冲击脉冲
            ia = [base_amplitude * np.sin(2 * np.pi * base_frequency * t) + 
                  2 * random.random() * np.sin(2 * np.pi * 120 * t) for t in time_series]
            ib = [base_amplitude * np.sin(2 * np.pi * base_frequency * t - 2 * np.pi / 3) for t in time_series]
            ic = [base_amplitude * np.sin(2 * np.pi * base_frequency * t + 2 * np.pi / 3) for t in time_series]
        elif fault_type == "broken_bar":
            # 断条故障：边频带
            slip = 0.02
            sideband_freq = base_frequency * (1 - 2 * slip)
            ia = [base_amplitude * np.sin(2 * np.pi * base_frequency * t) + 
                  0.5 * np.sin(2 * np.pi * sideband_freq * t) for t in time_series]
            ib = [base_amplitude * np.sin(2 * np.pi * base_frequency * t - 2 * np.pi / 3) for t in time_series]
            ic = [base_amplitude * np.sin(2 * np.pi * base_frequency * t + 2 * np.pi / 3) for t in time_series]
        else:
            # 正常状态
            ia = [base_amplitude * np.sin(2 * np.pi * base_frequency * t) for t in time_series]
            ib = [base_amplitude * np.sin(2 * np.pi * base_frequency * t - 2 * np.pi / 3) for t in time_series]
            ic = [base_amplitude * np.sin(2 * np.pi * base_frequency * t + 2 * np.pi / 3) for t in time_series]
        
        # 构建传感器数据
        sensor_data = {
            "data": [
                {
                    "时间": t,
                    "Ia": ia[i],
                    "Ib": ib[i], 
                    "Ic": ic[i],
                    "vibration_x": random.uniform(-0.1, 0.1),
                    "resistance": random.uniform(100, 200),
                    "leakage_current": random.uniform(0.001, 0.01)
                }
                for i, t in enumerate(time_series)
            ],
            "sampling_rate": 800
        }
        
        # 发布数据
        success = await stream_manager.publish_motor_data(
            vehicle_id=vehicle_id,
            sensor_data=sensor_data,
            location="测试地点",
            additional_metadata={
                "simulation": True,
                "simulated_fault": fault_type or "normal",
                "demo_mode": True
            }
        )
        
        if success:
            return {
                "status": "success",
                "message": f"成功发布车辆{vehicle_id}的模拟数据",
                "vehicle_id": vehicle_id,
                "fault_type": fault_type,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="数据发布失败")
            
    except Exception as e:
        logger.error(f"模拟数据生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"模拟数据生成失败: {str(e)}") 
    """ 

@router.post("/bridge/control", response_model=Dict[str, Any], tags=["诊断"])
async def control_stream_bridge(
    action: str = Query(..., description="控制动作: 'start' 或 'stop'")
):
    """
    控制Redis Stream到前端的桥接器
    
    - start: 启动桥接器，开始数据处理
    - stop: 暂停桥接器，停止数据处理
    """
    try:
        # 导入桥接器
        from ..services.redis_stream.stream_to_frontend_bridge import stream_bridge
        
        if action == "start":
            # 启动桥接器
            if not stream_bridge.is_monitoring:
                asyncio.create_task(stream_bridge.start_monitoring())
                return {"status": "success", "message": "桥接器已启动", "is_monitoring": True}
            else:
                return {"status": "success", "message": "桥接器已处于启动状态", "is_monitoring": True}
        
        elif action == "stop":
            # 停止桥接器
            await stream_bridge.stop_monitoring()
            return {"status": "success", "message": "桥接器已停止", "is_monitoring": False}
        
        else:
            return {"status": "error", "message": f"不支持的操作: {action}"}
            
    except Exception as e:
        logger.error(f"控制桥接器失败: {str(e)}")
        return {"status": "error", "message": f"控制桥接器失败: {str(e)}"}

@router.get("/bridge/status", response_model=Dict[str, Any], tags=["诊断"])
async def get_bridge_status():
    """获取Redis Stream到前端桥接器的状态"""
    try:
        from ..services.redis_stream.stream_to_frontend_bridge import stream_bridge
        stats = stream_bridge.get_bridge_stats()
        
        # 添加额外的诊断信息
        additional_info = {
            "status_description": {
                "healthy": "桥接器运行正常，正在处理消息",
                "unhealthy": "桥接器闲置超时，可能需要重启"
            }.get(stats.get("health_status", "unknown"), "状态未知"),
            "recommendations": []
        }
        
        # 根据状态提供建议
        if stats.get("health_status") == "unhealthy":
            additional_info["recommendations"].extend([
                "建议使用 POST /api/v1/diagnosis-stream/bridge/restart 重启桥接器",
                "检查Redis连接和WebSocket管理器状态",
                "检查是否有数据生产者正在发送消息"
            ])
        elif stats.get("processed_messages", 0) == 0:
            additional_info["recommendations"].append(
                "若持续无消息处理，请检查数据生产者状态"
            )
            
        return {
            "status": "success", 
            "data": {**stats, **additional_info},
            "is_monitoring": stats.get("is_monitoring", False)
        }
    except Exception as e:
        logger.error(f"获取桥接器状态失败: {str(e)}")
        return {"status": "error", "message": f"获取桥接器状态失败: {str(e)}"}

@router.post("/bridge/optimization/enable", response_model=Dict[str, Any], tags=["诊断"])
async def enable_cache_optimization():
    """启用Redis Stream缓存优化模式"""
    try:
        from ..services.redis_stream.stream_to_frontend_bridge import stream_bridge
        
        success = await stream_bridge.enable_cache_optimization()
        if success:
            return {
                "status": "success", 
                "message": "缓存优化模式已启用",
                "optimization_enabled": True
            }
        else:
            return {
                "status": "error", 
                "message": "缓存优化器未初始化，无法启用"
            }
    except Exception as e:
        logger.error(f"启用缓存优化失败: {str(e)}")
        return {"status": "error", "message": f"启用缓存优化失败: {str(e)}"}

@router.post("/bridge/optimization/disable", response_model=Dict[str, Any], tags=["诊断"])
async def disable_cache_optimization():
    """禁用Redis Stream缓存优化模式"""
    try:
        from ..services.redis_stream.stream_to_frontend_bridge import stream_bridge
        
        success = await stream_bridge.disable_cache_optimization()
        if success:
            return {
                "status": "success", 
                "message": "缓存优化模式已禁用",
                "optimization_enabled": False
            }
        else:
            return {
                "status": "error", 
                "message": "禁用缓存优化失败"
            }
    except Exception as e:
        logger.error(f"禁用缓存优化失败: {str(e)}")
        return {"status": "error", "message": f"禁用缓存优化失败: {str(e)}"}

@router.get("/bridge/optimization/stats", response_model=Dict[str, Any], tags=["诊断"])
async def get_optimization_stats():
    """获取缓存优化统计信息"""
    try:
        from ..services.redis_stream.stream_to_frontend_bridge import stream_bridge
        
        stats = await stream_bridge.get_optimization_stats()
        return {
            "status": "success", 
            "data": stats
        }
    except Exception as e:
        logger.error(f"获取缓存优化统计失败: {str(e)}")
        return {"status": "error", "message": f"获取缓存优化统计失败: {str(e)}"} 

@router.post("/bridge/restart", response_model=Dict[str, Any], tags=["诊断"])
async def restart_bridge():
    """重新启动Redis Stream桥接器（用于解决闲置问题）"""
    try:
        from ..services.redis_stream.stream_to_frontend_bridge import stream_bridge
        
        logger.info("🔄 手动重启桥接器...")
        
        # 停止当前监听
        if stream_bridge.is_monitoring:
            await stream_bridge.stop_monitoring()
            await asyncio.sleep(1)  # 等待停止完成
        
        # 重新启动监听
        if not stream_bridge.is_monitoring:
            asyncio.create_task(stream_bridge.start_monitoring())
            await asyncio.sleep(1)  # 等待启动
            
            return {
                "status": "success",
                "message": "桥接器重启成功",
                "data": {
                    "restarted_at": datetime.now().isoformat(),
                    "is_monitoring": stream_bridge.is_monitoring
                }
            }
        else:
            return {
                "status": "error",
                "message": "桥接器重启失败，仍在运行中"
            }
            
    except Exception as e:
        logger.error(f"重启桥接器失败: {str(e)}")
        return {"status": "error", "message": f"重启桥接器失败: {str(e)}"}

@router.get("/maintenance/stats", response_model=Dict[str, Any], tags=["诊断", "维护"])
async def get_stream_maintenance_stats(current_user = Depends(get_current_user)):
    """获取Stream维护统计信息"""
    try:
        from ..services.redis_stream.stream_manager import stream_manager
        
        stats = await stream_manager.get_maintenance_stats()
        return {
            "status": "success",
            "data": stats
        }
    except Exception as e:
        logger.error(f"获取维护统计失败: {str(e)}")
        return {"status": "error", "message": f"获取维护统计失败: {str(e)}"}

@router.post("/maintenance/start", response_model=Dict[str, Any], tags=["诊断", "维护"])
async def start_stream_maintenance(current_user = Depends(get_current_user)):
    """启动Stream维护功能"""
    try:
        from ..services.redis_stream.stream_manager import stream_manager
        
        success = await stream_manager.start_stream_maintenance()
        if success:
            return {
                "status": "success",
                "message": "Stream维护功能已启动",
                "maintenance_enabled": True
            }
        else:
            return {
                "status": "error",
                "message": "Stream维护功能启动失败，请检查系统状态"
            }
    except Exception as e:
        logger.error(f"启动Stream维护失败: {str(e)}")
        return {"status": "error", "message": f"启动Stream维护失败: {str(e)}"}

@router.post("/maintenance/stop", response_model=Dict[str, Any], tags=["诊断", "维护"])
async def stop_stream_maintenance(current_user = Depends(get_current_user)):
    """停止Stream维护功能"""
    try:
        from ..services.redis_stream.stream_manager import stream_manager
        
        await stream_manager.stop_stream_maintenance()
        return {
            "status": "success",
            "message": "Stream维护功能已停止",
            "maintenance_enabled": False
        }
    except Exception as e:
        logger.error(f"停止Stream维护失败: {str(e)}")
        return {"status": "error", "message": f"停止Stream维护失败: {str(e)}"}

@router.post("/maintenance/trim/{stream_name}", response_model=Dict[str, Any], tags=["诊断", "维护"])
async def manual_trim_stream(
    stream_name: str,
    max_length: Optional[int] = Query(None, description="最大长度，不指定则使用默认配置"),
    current_user = Depends(get_current_user)
):
    """手动裁剪指定Stream"""
    try:
        from ..services.redis_stream.stream_manager import stream_manager
        
        result = await stream_manager.manual_trim_stream(stream_name, max_length)
        return {
            "status": "success" if result.get("success", False) else "error",
            "data": result
        }
    except Exception as e:
        logger.error(f"手动裁剪Stream失败: {str(e)}")
        return {"status": "error", "message": f"手动裁剪Stream失败: {str(e)}"}

@router.put("/maintenance/config", response_model=Dict[str, Any], tags=["诊断", "维护"])
async def update_maintenance_config(
    config_updates: Dict[str, Any],
    current_user = Depends(get_current_user)
):
    """更新维护配置"""
    try:
        from ..services.redis_stream.stream_manager import stream_manager
        
        success = await stream_manager.update_maintenance_config(config_updates)
        if success:
            return {
                "status": "success",
                "message": "维护配置已更新",
                "updated_config": config_updates
            }
        else:
            return {
                "status": "error",
                "message": "更新维护配置失败"
            }
    except Exception as e:
        logger.error(f"更新维护配置失败: {str(e)}")
        return {"status": "error", "message": f"更新维护配置失败: {str(e)}"}

@router.get("/streams/info", response_model=Dict[str, Any], tags=["诊断", "维护"])
async def get_streams_info(current_user = Depends(get_current_user)):
    """获取所有Stream的详细信息"""
    try:
        from ..services.redis_stream.stream_manager import stream_manager
        
        info = await stream_manager.get_stream_info()
        return {
            "status": "success",
            "data": info
        }
    except Exception as e:
        logger.error(f"获取Stream信息失败: {str(e)}")
        return {"status": "error", "message": f"获取Stream信息失败: {str(e)}"} 

# 🧠 自适应消费者管理API
@router.post("/adaptive/start", response_model=Dict[str, Any], tags=["诊断", "自适应"])
async def start_adaptive_consumer_management(current_user = Depends(get_current_user)):
    """启动实时自适应消费者管理"""
    try:
        from ..services.redis_stream.adaptive_consumer_manager import adaptive_consumer_manager
        
        # 初始化管理器
        if not await adaptive_consumer_manager.initialize():
            return {
                "status": "error",
                "message": "自适应管理器初始化失败"
            }
        
        # 启动监控
        await adaptive_consumer_manager.start_adaptive_monitoring()
        
        return {
            "status": "success",
            "message": "实时自适应消费者管理已启动",
            "features": [
                "智能负载监控",
                "自动扩展决策", 
                "趋势分析预测",
                "资源安全检查",
                "非侵入式执行"
            ],
            "config": {
                "monitoring_interval": adaptive_consumer_manager.config.monitoring_interval,
                "max_consumers_per_fault": adaptive_consumer_manager.config.max_consumers_per_fault,
                "cpu_safe_threshold": adaptive_consumer_manager.config.cpu_safe_threshold,
                "memory_safe_threshold": adaptive_consumer_manager.config.memory_safe_threshold
            }
        }
    except Exception as e:
        logger.error(f"启动自适应管理失败: {str(e)}")
        return {"status": "error", "message": f"启动自适应管理失败: {str(e)}"}

@router.post("/adaptive/stop", response_model=Dict[str, Any], tags=["诊断", "自适应"])
async def stop_adaptive_consumer_management(current_user = Depends(get_current_user)):
    """停止实时自适应消费者管理"""
    try:
        from ..services.redis_stream.adaptive_consumer_manager import adaptive_consumer_manager
        
        await adaptive_consumer_manager.stop_adaptive_monitoring()
        
        return {
            "status": "success",
            "message": "实时自适应消费者管理已停止"
        }
    except Exception as e:
        logger.error(f"停止自适应管理失败: {str(e)}")
        return {"status": "error", "message": f"停止自适应管理失败: {str(e)}"}

@router.get("/adaptive/stats", response_model=Dict[str, Any], tags=["诊断", "自适应"])
async def get_adaptive_management_stats(current_user = Depends(get_current_user)):
    """获取自适应管理统计信息"""
    try:
        from ..services.redis_stream.adaptive_consumer_manager import adaptive_consumer_manager
        
        stats = await adaptive_consumer_manager.get_adaptive_stats()
        return {
            "status": "success",
            "data": stats
        }
    except Exception as e:
        logger.error(f"获取自适应统计失败: {str(e)}")
        return {"status": "error", "message": f"获取自适应统计失败: {str(e)}"}

@router.put("/adaptive/config", response_model=Dict[str, Any], tags=["诊断", "自适应"])
async def update_adaptive_config(
    config_updates: Dict[str, Any],
    current_user = Depends(get_current_user)
):
    """更新自适应管理配置"""
    try:
        from ..services.redis_stream.adaptive_consumer_manager import adaptive_consumer_manager
        
        # 验证配置参数
        valid_keys = {
            "monitoring_interval", "high_load_threshold", "low_load_threshold",
            "cpu_safe_threshold", "memory_safe_threshold", "max_consumers_per_fault",
            "min_consumers_per_fault", "scale_step_size", "cooldown_period_minutes"
        }
        
        invalid_keys = set(config_updates.keys()) - valid_keys
        if invalid_keys:
            return {
                "status": "error",
                "message": f"无效的配置参数: {list(invalid_keys)}",
                "valid_keys": list(valid_keys)
            }
        
        # 更新配置
        for key, value in config_updates.items():
            if hasattr(adaptive_consumer_manager.config, key):
                setattr(adaptive_consumer_manager.config, key, value)
        
        return {
            "status": "success",
            "message": "自适应配置已更新",
            "updated_config": config_updates
        }
    except Exception as e:
        logger.error(f"更新自适应配置失败: {str(e)}")
        return {"status": "error", "message": f"更新自适应配置失败: {str(e)}"}

@router.get("/adaptive/decisions/history", response_model=Dict[str, Any], tags=["诊断", "自适应"])
async def get_scaling_decisions_history(
    limit: int = Query(20, description="返回决策数量限制"),
    fault_type: Optional[str] = Query(None, description="按故障类型过滤"),
    current_user = Depends(get_current_user)
):
    """获取扩展决策历史"""
    try:
        from ..services.redis_stream.adaptive_consumer_manager import adaptive_consumer_manager
        
        history = adaptive_consumer_manager.scaling_history
        
        # 按故障类型过滤
        if fault_type:
            history = [d for d in history if d.fault_type == fault_type]
        
        # 限制数量
        history = history[-limit:]
        
        # 格式化返回数据
        decisions = []
        for decision in history:
            decisions.append({
                "fault_type": decision.fault_type,
                "action": decision.action.value,
                "current_count": decision.current_count,
                "target_count": decision.target_count,
                "confidence": decision.confidence,
                "reasoning": decision.reasoning,
                "priority": decision.priority,
                "estimated_impact": decision.estimated_impact,
                "timestamp": getattr(decision, 'timestamp', None)
            })
        
        return {
            "status": "success",
            "data": {
                "decisions": decisions,
                "total_count": len(adaptive_consumer_manager.scaling_history),
                "filtered_count": len(decisions)
            }
        }
    except Exception as e:
        logger.error(f"获取决策历史失败: {str(e)}")
        return {"status": "error", "message": f"获取决策历史失败: {str(e)}"}

@router.post("/adaptive/simulate", response_model=Dict[str, Any], tags=["诊断", "自适应"])
async def simulate_scaling_decision(
    fault_type: str,
    pending_messages: int = Query(..., description="模拟的待处理消息数"),
    cpu_usage: float = Query(50.0, description="模拟的CPU使用率"),
    memory_usage: float = Query(60.0, description="模拟的内存使用率"),
    current_user = Depends(get_current_user)
):
    """模拟扩展决策（用于测试和调试）"""
    try:
        from ..services.redis_stream.adaptive_consumer_manager import adaptive_consumer_manager, SystemMetrics, IntelligentDecisionEngine
        from collections import deque
        
        # 创建模拟指标
        mock_metrics = SystemMetrics(
            timestamp=datetime.now(),
            pending_messages={fault_type: pending_messages},
            active_consumers={fault_type: 2},  # 假设当前2个消费者
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            throughput=100.0  # 假设吞吐量
        )
        
        # 创建决策引擎
        decision_engine = IntelligentDecisionEngine(adaptive_consumer_manager.config)
        
        # 模拟决策
        decision = await decision_engine.analyze_fault_type(
            fault_type, mock_metrics, deque()
        )
        
        if decision:
            return {
                "status": "success",
                "data": {
                    "simulation_input": {
                        "fault_type": fault_type,
                        "pending_messages": pending_messages,
                        "cpu_usage": cpu_usage,
                        "memory_usage": memory_usage
                    },
                    "decision": {
                        "action": decision.action.value,
                        "current_count": decision.current_count,
                        "target_count": decision.target_count,
                        "confidence": decision.confidence,
                        "reasoning": decision.reasoning,
                        "priority": decision.priority,
                        "estimated_impact": decision.estimated_impact
                    }
                }
            }
        else:
            return {
                "status": "success",
                "data": {
                    "simulation_input": {
                        "fault_type": fault_type,
                        "pending_messages": pending_messages,
                        "cpu_usage": cpu_usage,
                        "memory_usage": memory_usage
                    },
                    "decision": {
                        "action": "maintain",
                        "reasoning": ["模拟条件下无需扩展"]
                    }
                }
            }
    except Exception as e:
        logger.error(f"模拟扩展决策失败: {str(e)}")
        return {"status": "error", "message": f"模拟扩展决策失败: {str(e)}"} 