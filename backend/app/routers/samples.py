"""
示例数据文件API
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os
import logging
import sys
from datetime import datetime
import urllib.parse

# 添加项目根路径到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

router = APIRouter(
    prefix="/samples",
    tags=["samples"]
)

logger = logging.getLogger(__name__)

# 示例文件目录
# 修改为指向项目根目录下的data/samples
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_ROOT = os.path.dirname(BASE_DIR)  # 项目根目录
SAMPLES_DIR = os.path.join(PROJECT_ROOT, "data", "samples")

# 故障类型名称映射
BEARING_FAULT_TYPE_NAMES = {
    "normal": "正常",
    "inner_race": "内圈故障",
    "outer_race": "外圈故障",
    "ball": "滚动体故障"
}

ECCENTRICITY_FAULT_TYPE_NAMES = {
    "normal": "正常",
    "static": "静态偏心",
    "dynamic": "动态偏心",
    "mixed": "混合偏心"
}

BROKEN_BAR_FAULT_TYPE_NAMES = {
    "normal": "正常",
    "broken_bar": "断条故障"
}

@router.get("/normal")
async def get_normal_sample():
    """获取正常运行的示例数据文件"""
    file_path = os.path.join(SAMPLES_DIR, "normal_sample.csv")
    if not os.path.exists(file_path):
        logger.error(f"示例文件不存在: {file_path}")
        raise HTTPException(status_code=404, detail="示例文件不存在")
    
    # 使用英文文件名
    filename = f"normal_sample_{datetime.now().strftime('%Y%m%d')}.csv"
    cn_filename = f"正常运行样本_{datetime.now().strftime('%Y%m%d')}.csv"
    # URL编码中文文件名
    encoded_filename = urllib.parse.quote(cn_filename)
    
    return FileResponse(
        path=file_path, 
        filename=filename,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\"; filename*=UTF-8''{encoded_filename}"}
    )

@router.get("/warning")
async def get_warning_sample():
    """获取预警状态的示例数据文件"""
    file_path = os.path.join(SAMPLES_DIR, "warning_sample.csv")
    if not os.path.exists(file_path):
        logger.error(f"示例文件不存在: {file_path}")
        raise HTTPException(status_code=404, detail="示例文件不存在")
    
    # 使用英文文件名
    filename = f"warning_sample_{datetime.now().strftime('%Y%m%d')}.csv"
    cn_filename = f"预警状态样本_{datetime.now().strftime('%Y%m%d')}.csv"
    # URL编码中文文件名
    encoded_filename = urllib.parse.quote(cn_filename)
    
    return FileResponse(
        path=file_path, 
        filename=filename,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\"; filename*=UTF-8''{encoded_filename}"}
    )

@router.get("/fault")
async def get_fault_sample():
    """获取故障状态的示例数据文件"""
    file_path = os.path.join(SAMPLES_DIR, "fault_sample.csv")
    if not os.path.exists(file_path):
        logger.error(f"示例文件不存在: {file_path}")
        raise HTTPException(status_code=404, detail="示例文件不存在")
    
    # 使用英文文件名
    filename = f"fault_sample_{datetime.now().strftime('%Y%m%d')}.csv"
    cn_filename = f"故障状态样本_{datetime.now().strftime('%Y%m%d')}.csv"
    # URL编码中文文件名
    encoded_filename = urllib.parse.quote(cn_filename)
    
    return FileResponse(
        path=file_path, 
        filename=filename,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\"; filename*=UTF-8''{encoded_filename}"}
    ) 

@router.get("/insulation/{type}")
async def get_insulation_sample(type: str):
    """
    获取绝缘状态示例数据文件
    :param type: 示例类型 (normal, degrading, critical)
    :return: CSV文件
    """
    # 映射类型到文件名
    file_map = {
        "normal": "insulation_normal_sample.csv",
        "degrading": "insulation_degrading_sample.csv",
        "critical": "insulation_critical_sample.csv"
    }
    
    if type not in file_map:
        logger.error(f"无效的示例类型: {type}")
        raise HTTPException(status_code=400, detail="无效的示例类型")
    
    file_path = os.path.join(SAMPLES_DIR, file_map[type])
    if not os.path.exists(file_path):
        logger.error(f"示例文件不存在: {file_path}")
        raise HTTPException(status_code=404, detail="示例文件不存在")
    
    # 中英文文件名映射
    cn_name_map = {
        "normal": f"绝缘正常样本_{datetime.now().strftime('%Y%m%d')}.csv",
        "degrading": f"绝缘劣化样本_{datetime.now().strftime('%Y%m%d')}.csv",
        "critical": f"绝缘危险样本_{datetime.now().strftime('%Y%m%d')}.csv"
    }
    
    # 使用英文文件名
    filename = f"insulation_{type}_sample_{datetime.now().strftime('%Y%m%d')}.csv"
    cn_filename = cn_name_map[type]
    # URL编码中文文件名
    encoded_filename = urllib.parse.quote(cn_filename)
    
    return FileResponse(
        path=file_path, 
        filename=filename,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\"; filename*=UTF-8''{encoded_filename}"}
    ) 

@router.get("/bearing/{type}")
async def get_bearing_sample(type: str):
    """
    获取轴承故障样本数据
    :param type: 轴承故障类型: normal, inner_race, outer_race, ball
    :return: 样本CSV文件
    """
    allowed_types = ["normal", "inner_race", "outer_race", "ball"]
    if type not in allowed_types:
        raise HTTPException(
            status_code=404,
            detail=f"不支持的轴承故障类型: {type}，可用类型: {', '.join(allowed_types)}"
        )
    
    sample_file = f"bearing_{type}_sample.csv"
    file_path = os.path.join(SAMPLES_DIR, sample_file)
    
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail=f"示例文件不存在: {file_path}"
        )
    
    return FileResponse(
        file_path,
        media_type="text/csv",
        filename=f"轴承{BEARING_FAULT_TYPE_NAMES.get(type, '')}样本_{datetime.now().strftime('%Y%m%d')}.csv"
    )

@router.get("/eccentricity/{type}")
async def get_eccentricity_sample(type: str):
    """
    获取偏心故障样本数据
    :param type: 偏心故障类型: normal, static, dynamic, mixed
    :return: 样本CSV文件
    """
    allowed_types = ["normal", "static", "dynamic", "mixed"]
    if type not in allowed_types:
        raise HTTPException(
            status_code=404,
            detail=f"不支持的偏心故障类型: {type}，可用类型: {', '.join(allowed_types)}"
        )
    
    sample_file = f"eccentricity_{type}_sample.csv"
    file_path = os.path.join(SAMPLES_DIR, sample_file)
    
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail=f"示例文件不存在: {file_path}"
        )
    
    return FileResponse(
        file_path,
        media_type="text/csv",
        filename=f"偏心{ECCENTRICITY_FAULT_TYPE_NAMES.get(type, '')}样本_{datetime.now().strftime('%Y%m%d')}.csv"
    )

@router.get("/broken-bar/{type}")
async def get_broken_bar_sample(type: str):
    """
    获取断条故障样本数据
    :param type: 断条故障类型: normal, broken_bar
    :return: 样本CSV文件
    """
    allowed_types = ["normal", "broken_bar"]
    if type not in allowed_types:
        raise HTTPException(
            status_code=404,
            detail=f"不支持的断条故障类型: {type}，可用类型: {', '.join(allowed_types)}"
        )
    
    sample_file = f"broken_bar_{type}_sample.csv"
    file_path = os.path.join(SAMPLES_DIR, sample_file)
    
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail=f"示例文件不存在: {file_path}"
        )
    
    return FileResponse(
        file_path,
        media_type="text/csv",
        filename=f"断条{BROKEN_BAR_FAULT_TYPE_NAMES.get(type, '')}样本_{datetime.now().strftime('%Y%m%d')}.csv"
    )