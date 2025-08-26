"""
🚗 车队管理路由 - 管理MultiVehicleSimulator
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
import logging
import asyncio
import subprocess
import signal
import os
from datetime import datetime
import json

from .auth import get_current_user

router = APIRouter(prefix="/api/v1/vehicle-fleet", tags=["车队管理"])
logger = logging.getLogger("vehicle-fleet-api")

# 全局车队管理器状态
fleet_manager_state = {
    "process": None,
    "status": "stopped",  # stopped, starting, running, stopping, error
    "start_time": None,
    "config": None,
    "stats": None
}

class FleetConfig:
    """车队配置"""
    def __init__(self, fleet_size: int = 10, auth_token: str = None, 
                 api_base_url: str = "http://localhost:8000"):
        self.fleet_size = fleet_size
        self.auth_token = auth_token
        self.api_base_url = api_base_url
        self.vehicles = []

@router.post("/initialize")
async def initialize_fleet(
    fleet_size: int = Query(50, ge=1, le=100, description="车队大小（支持1-100辆车）"),
    api_base_url: str = Query("http://localhost:8000", description="API基础URL"),
    current_user = Depends(get_current_user)
):
    """初始化车队配置"""
    try:
        # 获取当前用户的JWT令牌（从请求头中提取）
        # 注意：这里需要从request中获取Authorization头
        from fastapi import Request
        
        fleet_manager_state["config"] = {
            "fleet_size": fleet_size,
            "api_base_url": api_base_url,
            "auth_token": "will_be_set_from_request",
            "user_id": current_user.id if hasattr(current_user, 'id') else 'unknown'
        }
        
        fleet_manager_state["status"] = "initialized"
        
        return {
            "status": "success",
            "message": f"车队配置初始化成功（{fleet_size}辆车）",
            "config": {
                "fleet_size": fleet_size,
                "api_base_url": api_base_url
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"车队初始化失败: {e}")
        raise HTTPException(status_code=500, detail=f"车队初始化失败: {str(e)}")

@router.post("/start")
async def start_fleet_simulation(
    background_tasks: BackgroundTasks,
    duration_seconds: Optional[int] = Query(None, description="运行时长（秒），不指定则持续运行"),
    test_mode: bool = Query(False, description="是否为测试模式"),
    current_user = Depends(get_current_user)
):
    """启动车队模拟"""
    try:
        if fleet_manager_state["status"] == "running":
            raise HTTPException(status_code=400, detail="车队模拟已在运行中")
        
        if not fleet_manager_state.get("config"):
            raise HTTPException(status_code=400, detail="请先初始化车队配置")
        
        fleet_manager_state["status"] = "starting"
        fleet_manager_state["start_time"] = datetime.now()
        
        # 在后台启动MultiVehicleSimulator
        background_tasks.add_task(
            _run_fleet_simulation, 
            duration_seconds, 
            test_mode,
            current_user
        )
        
        return {
            "status": "success",
            "message": "车队模拟启动中...",
            "config": fleet_manager_state["config"],
            "duration": duration_seconds,
            "test_mode": test_mode,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        fleet_manager_state["status"] = "error"
        logger.error(f"启动车队模拟失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动车队模拟失败: {str(e)}")

@router.post("/stop")
async def stop_fleet_simulation(
    current_user = Depends(get_current_user)
):
    """停止车队模拟"""
    try:
        if fleet_manager_state["status"] != "running":
            raise HTTPException(status_code=400, detail="车队模拟未运行")
        
        fleet_manager_state["status"] = "stopping"
        
        # 终止进程
        if fleet_manager_state["process"]:
            try:
                fleet_manager_state["process"].terminate()
                # 等待进程结束
                await asyncio.sleep(2)
                if fleet_manager_state["process"].poll() is None:
                    fleet_manager_state["process"].kill()
                fleet_manager_state["process"] = None
            except Exception as e:
                logger.error(f"终止车队进程失败: {e}")
        
        fleet_manager_state["status"] = "stopped"
        
        return {
            "status": "success",
            "message": "车队模拟已停止",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"停止车队模拟失败: {e}")
        raise HTTPException(status_code=500, detail=f"停止车队模拟失败: {str(e)}")

@router.get("/status")
async def get_fleet_status(
    current_user = Depends(get_current_user)
):
    """获取车队状态"""
    try:
        # 更新进程状态
        if fleet_manager_state["process"]:
            if fleet_manager_state["process"].poll() is not None:
                # 进程已结束
                fleet_manager_state["status"] = "stopped"
                fleet_manager_state["process"] = None
        
        runtime = None
        if fleet_manager_state["start_time"]:
            runtime = (datetime.now() - fleet_manager_state["start_time"]).total_seconds()
        
        return {
            "status": fleet_manager_state["status"],
            "config": fleet_manager_state.get("config"),
            "start_time": fleet_manager_state["start_time"].isoformat() if fleet_manager_state["start_time"] else None,
            "runtime_seconds": runtime,
            "process_alive": fleet_manager_state["process"] is not None,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取车队状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取车队状态失败: {str(e)}")

@router.get("/logs")
async def get_fleet_logs(
    lines: int = Query(50, ge=1, le=1000, description="日志行数"),
    current_user = Depends(get_current_user)
):
    """获取车队运行日志"""
    try:
        # 这里可以读取MultiVehicleSimulator的日志文件
        # 暂时返回模拟数据
        logs = [
            f"[{datetime.now().isoformat()}] INFO: 车队模拟器运行中...",
            f"[{datetime.now().isoformat()}] INFO: 车辆数据发送统计更新"
        ]
        
        return {
            "status": "success",
            "logs": logs[-lines:],
            "total_lines": len(logs),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取车队日志失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取车队日志失败: {str(e)}")

@router.get("/stats")
async def get_fleet_stats(
    current_user = Depends(get_current_user)
):
    """获取车队统计信息"""
    try:
        # 这里应该从MultiVehicleSimulator获取真实统计
        # 暂时返回模拟数据
        if fleet_manager_state["status"] != "running":
            return {
                "status": "not_running",
                "message": "车队未运行",
                "timestamp": datetime.now().isoformat()
            }
        
        # 模拟统计数据
        stats = {
            "fleet_summary": {
                "total_vehicles": fleet_manager_state.get("config", {}).get("fleet_size", 0),
                "running_vehicles": 3,
                "total_messages_sent": 1250,
                "total_errors": 15,
                "overall_success_rate": 0.988
            },
            "vehicles": [
                {
                    "vehicle_id": "VEHICLE_001",
                    "config": {"fault_type": "normal", "location": "北京"},
                    "stats": {"total_sent": 420, "total_errors": 3, "success_rate": 0.993}
                },
                {
                    "vehicle_id": "VEHICLE_002", 
                    "config": {"fault_type": "turn_fault", "location": "上海"},
                    "stats": {"total_sent": 415, "total_errors": 7, "success_rate": 0.983}
                },
                {
                    "vehicle_id": "VEHICLE_003",
                    "config": {"fault_type": "bearing", "location": "深圳"}, 
                    "stats": {"total_sent": 415, "total_errors": 5, "success_rate": 0.988}
                }
            ],
            "timestamp": datetime.now().isoformat()
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"获取车队统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取车队统计失败: {str(e)}")

async def _run_fleet_simulation(duration_seconds: Optional[int], test_mode: bool, current_user):
    """后台运行车队模拟"""
    try:
        logger.info(f"开始启动车队模拟 - 用户: {getattr(current_user, 'username', 'unknown')}")
        
        # 构建命令
        script_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "databases", "test_multi_vehicle.py")
        
        cmd = ["python", script_path]
        if test_mode:
            cmd.append("--test-mode")
        if duration_seconds:
            cmd.extend(["--duration", str(duration_seconds)])
        
        # 启动进程
        fleet_manager_state["process"] = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.path.dirname(script_path)
        )
        
        fleet_manager_state["status"] = "running"
        logger.info(f"车队模拟进程已启动: PID {fleet_manager_state['process'].pid}")
        
        # 等待进程结束
        stdout, stderr = await asyncio.to_thread(fleet_manager_state["process"].communicate)
        
        if fleet_manager_state["process"].returncode == 0:
            logger.info("车队模拟正常结束")
            fleet_manager_state["status"] = "stopped"
        else:
            logger.error(f"车队模拟异常结束: {stderr}")
            fleet_manager_state["status"] = "error"
        
        fleet_manager_state["process"] = None
        
    except Exception as e:
        logger.error(f"车队模拟运行异常: {e}")
        fleet_manager_state["status"] = "error"
        fleet_manager_state["process"] = None 