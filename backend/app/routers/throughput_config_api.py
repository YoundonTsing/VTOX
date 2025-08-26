# -*- coding: utf-8 -*-
"""
吞吐量配置管理API
允许用户动态调整新鲜度因子、时间窗口、递减曲线等参数
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
import logging
from ..config.throughput_config import get_config, update_config, reset_config
from ..services.auto_refresh_service import get_auto_refresh_service

logger = logging.getLogger(__name__)
router = APIRouter()

class ThroughputConfigUpdate(BaseModel):
    """吞吐量配置更新模型"""
    freshness_window_minutes: Optional[int] = Field(None, ge=10, le=180, description="新鲜度时间窗口(10-180分钟)")
    min_freshness_factor: Optional[float] = Field(None, ge=0.1, le=0.8, description="最小新鲜度因子(0.1-0.8)")
    decay_curve_type: Optional[Literal["linear", "exponential", "logarithmic", "sqrt"]] = Field(None, description="递减曲线类型")
    decay_steepness: Optional[float] = Field(None, ge=0.1, le=2.0, description="递减陡峭程度(0.1-2.0)")
    auto_refresh_enabled: Optional[bool] = Field(None, description="是否启用自动刷新")
    refresh_threshold_minutes: Optional[int] = Field(None, ge=5, le=120, description="自动刷新阈值(5-120分钟)")
    refresh_base_value: Optional[float] = Field(None, ge=1.0, le=20.0, description="刷新基础值(1.0-20.0)")
    base_throughput_multiplier: Optional[float] = Field(None, ge=2.0, le=15.0, description="基础吞吐量乘数(2.0-15.0)")
    activity_weight: Optional[float] = Field(None, ge=0.0, le=1.0, description="活跃度权重(0.0-1.0)")
    freshness_weight: Optional[float] = Field(None, ge=0.0, le=1.0, description="新鲜度权重(0.0-1.0)")

class ThroughputConfigResponse(BaseModel):
    """吞吐量配置响应模型"""
    freshness_window_minutes: int
    min_freshness_factor: float
    decay_curve_type: str
    decay_steepness: float
    auto_refresh_enabled: bool
    refresh_threshold_minutes: int
    refresh_base_value: float
    base_throughput_multiplier: float
    activity_weight: float
    freshness_weight: float

@router.get("/api/v1/config/throughput", response_model=ThroughputConfigResponse)
async def get_throughput_config():
    """获取当前吞吐量配置"""
    try:
        config = get_config()
        return ThroughputConfigResponse(
            freshness_window_minutes=config.freshness_window_minutes,
            min_freshness_factor=config.min_freshness_factor,
            decay_curve_type=config.decay_curve_type,
            decay_steepness=config.decay_steepness,
            auto_refresh_enabled=config.auto_refresh_enabled,
            refresh_threshold_minutes=config.refresh_threshold_minutes,
            refresh_base_value=config.refresh_base_value,
            base_throughput_multiplier=config.base_throughput_multiplier,
            activity_weight=config.activity_weight,
            freshness_weight=config.freshness_weight
        )
    except Exception as e:
        logger.error(f"获取吞吐量配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/api/v1/config/throughput")
async def update_throughput_config(config_update: ThroughputConfigUpdate):
    """更新吞吐量配置"""
    try:
        # 验证权重和不能超过1.0
        if (config_update.activity_weight is not None and 
            config_update.freshness_weight is not None):
            if config_update.activity_weight + config_update.freshness_weight > 1.0:
                raise HTTPException(
                    status_code=400, 
                    detail="活跃度权重 + 新鲜度权重不能超过1.0"
                )
        
        # 更新配置
        update_data = {k: v for k, v in config_update.dict().items() if v is not None}
        
        if update_data:
            update_config(**update_data)
            logger.info(f"✅ 吞吐量配置已更新: {update_data}")
            
            return {
                "status": "success",
                "message": f"已更新 {len(update_data)} 个配置项",
                "updated_items": list(update_data.keys()),
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "no_change",
                "message": "没有提供需要更新的配置项",
                "timestamp": datetime.now().isoformat()
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新吞吐量配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/v1/config/throughput/reset")
async def reset_throughput_config():
    """重置吞吐量配置为默认值"""
    try:
        reset_config()
        logger.info("✅ 吞吐量配置已重置为默认值")
        
        return {
            "status": "success",
            "message": "配置已重置为默认值",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"重置吞吐量配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/v1/config/throughput/refresh")
async def manual_refresh_data():
    """手动触发数据刷新"""
    try:
        refresh_service = await get_auto_refresh_service()
        success = await refresh_service.manual_refresh("手动API触发")
        
        if success:
            return {
                "status": "success",
                "message": "数据刷新成功",
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="数据刷新失败")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"手动刷新数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/config/throughput/preview")
async def preview_freshness_curve(
    age_minutes: float = Query(..., ge=0, le=180, description="数据年龄(分钟)"),
    curve_type: str = Query("logarithmic", description="递减曲线类型"),
    steepness: float = Query(0.5, ge=0.1, le=2.0, description="递减陡峭程度"),
    window_minutes: int = Query(60, ge=10, le=180, description="时间窗口(分钟)"),
    min_factor: float = Query(0.3, ge=0.1, le=0.8, description="最小新鲜度因子")
):
    """预览新鲜度因子曲线"""
    try:
        # 临时创建配置对象进行预览
        from ..config.throughput_config import ThroughputConfig
        preview_config = ThroughputConfig()
        preview_config.decay_curve_type = curve_type
        preview_config.decay_steepness = steepness
        preview_config.freshness_window_minutes = window_minutes
        preview_config.min_freshness_factor = min_factor
        
        # 计算新鲜度因子
        freshness_factor = preview_config.calculate_freshness_factor(age_minutes)
        
        # 生成曲线预览数据
        preview_points = []
        for age in range(0, window_minutes + 1, 5):  # 每5分钟一个点
            factor = preview_config.calculate_freshness_factor(age)
            preview_points.append({
                "age_minutes": age,
                "freshness_factor": round(factor, 4)
            })
        
        return {
            "status": "success",
            "data": {
                "current_age": age_minutes,
                "current_factor": round(freshness_factor, 4),
                "curve_preview": preview_points,
                "config": {
                    "curve_type": curve_type,
                    "steepness": steepness,
                    "window_minutes": window_minutes,
                    "min_factor": min_factor
                }
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"预览新鲜度曲线失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))