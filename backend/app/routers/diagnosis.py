from fastapi import APIRouter, UploadFile, File, HTTPException, status, BackgroundTasks
from fastapi.responses import JSONResponse
import pandas as pd
import tempfile
import os
import logging
from datetime import datetime
import shutil
from typing import Optional
import sys
import numpy as np
import math
import json

# 添加项目根路径到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from app.services.diagnosis.turn_to_turn_diagnosis import analyze_turn_to_turn_fault
    from app.services.diagnosis.insulation_diagnosis import analyze_insulation_health
    from app.services.diagnosis.bearing_diagnosis import analyze_bearing_health
    from app.services.diagnosis.eccentricity_diagnosis import analyze_eccentricity_health
    from app.services.diagnosis.broken_bar_diagnosis import analyze_broken_bar_health
    from app.utils.data_preprocessor import preprocess_motor_data
    from app.models.diagnosis_models import DiagnosisResult, InsulationDiagnosisResult, BearingDiagnosisResult, EccentricityDiagnosisResult, BrokenBarDiagnosisResult
except ImportError:
    # 如果上面的导入失败，尝试相对导入
    from ..services.diagnosis.turn_to_turn_diagnosis import analyze_turn_to_turn_fault
    from ..services.diagnosis.insulation_diagnosis import analyze_insulation_health
    from ..services.diagnosis.bearing_diagnosis import analyze_bearing_health
    from ..services.diagnosis.eccentricity_diagnosis import analyze_eccentricity_health
    from ..services.diagnosis.broken_bar_diagnosis import analyze_broken_bar_health
    from ..utils.data_preprocessor import preprocess_motor_data
    from ..models.diagnosis_models import DiagnosisResult, InsulationDiagnosisResult, BearingDiagnosisResult, EccentricityDiagnosisResult, BrokenBarDiagnosisResult

router = APIRouter(
    prefix="/diagnosis",
    tags=["diagnosis"]
)

logger = logging.getLogger(__name__)

# 创建上传文件存储目录
UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 自定义JSON编码器处理NaN和Infinity值
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, float):
            if math.isnan(obj):
                return None
            elif math.isinf(obj):
                return "Infinity" if obj > 0 else "-Infinity"
        return super().default(obj)

# 处理结果中的特殊浮点值
def process_special_float_values(data):
    if isinstance(data, dict):
        return {k: process_special_float_values(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [process_special_float_values(v) for v in data]
    elif isinstance(data, float):
        if math.isnan(data):
            return None
        elif math.isinf(data):
            return "Infinity" if data > 0 else "-Infinity"
    return data

@router.post("/turn-to-turn", response_model=DiagnosisResult)
async def diagnose_turn_to_turn(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    save_file: bool = True
):
    """
    诊断电机匝间短路故障
    :param background_tasks: 后台任务
    :param file: 上传的CSV文件
    :param save_file: 是否保存原始文件
    :return: 诊断结果
    """
    logger.info(f"接收到文件上传请求: {file.filename}, 大小: {file.size if hasattr(file, 'size') else '未知'}")
    
    if not file.filename.endswith('.csv'):
        logger.warning(f"上传了非CSV文件: {file.filename}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只接受CSV格式的文件"
        )
    
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp:
            # 保存上传的文件
            shutil.copyfileobj(file.file, temp)
            temp_path = temp.name
            
        logger.info(f"文件已保存到临时位置: {temp_path}")
        
        # 检查文件内容
        try:
            with open(temp_path, 'r', encoding='utf-8') as f:
                first_lines = [next(f) for _ in range(5)]
            logger.info(f"文件头5行:\n{''.join(first_lines)}")
        except Exception as e:
            logger.warning(f"读取文件头时出错: {str(e)}")
        
        # 预处理数据
        try:
            processed_df = preprocess_motor_data(temp_path)
            logger.info(f"成功预处理文件: {file.filename}, 行数: {len(processed_df)}, 列: {processed_df.columns.tolist()}")
        except Exception as e:
            logger.error(f"数据预处理失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"数据预处理失败: {str(e)}"
            )
        
        # 分析匝间短路故障
        analysis_result = analyze_turn_to_turn_fault(processed_df)
        
        # 处理结果中的特殊浮点值
        analysis_result = process_special_float_values(analysis_result)
        
        # 保存原始文件（可选）
        if save_file:
            # 生成唯一文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{file.filename}"
            file_path = os.path.join(UPLOAD_DIR, filename)
            
            # 保存上传的文件
            with open(temp_path, "rb") as src, open(file_path, "wb") as dst:
                shutil.copyfileobj(src, dst)
            
            # 添加后台任务清理临时文件
            background_tasks.add_task(os.unlink, temp_path)
            
            logger.info(f"保存原始文件: {file_path}")
        
        return JSONResponse(content=analysis_result)
        
    except Exception as e:
        logger.exception("处理匝间短路诊断文件时发生错误")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理文件时发生错误: {str(e)}"
        ) 

@router.post("/insulation", response_model=InsulationDiagnosisResult)
async def diagnose_insulation(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    save_file: bool = True
):
    """
    诊断电机绝缘失效状态
    :param background_tasks: 后台任务
    :param file: 上传的CSV文件
    :param save_file: 是否保存原始文件
    :return: 诊断结果
    """
    logger.info(f"接收到绝缘失效检测请求: {file.filename}, 大小: {file.size if hasattr(file, 'size') else '未知'}")
    
    if not file.filename.endswith('.csv'):
        logger.warning(f"上传了非CSV文件: {file.filename}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只接受CSV格式的文件"
        )
    
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp:
            # 保存上传的文件
            shutil.copyfileobj(file.file, temp)
            temp_path = temp.name
            
        logger.info(f"文件已保存到临时位置: {temp_path}")
        
        # 检查文件内容
        try:
            with open(temp_path, 'r', encoding='utf-8') as f:
                first_lines = [next(f) for _ in range(5)]
            logger.info(f"文件头5行:\n{''.join(first_lines)}")
        except Exception as e:
            logger.warning(f"读取文件头时出错: {str(e)}")
        
        # 预处理数据
        try:
            processed_df = preprocess_motor_data(temp_path)
            logger.info(f"成功预处理文件: {file.filename}, 行数: {len(processed_df)}, 列: {processed_df.columns.tolist()}")
        except Exception as e:
            logger.error(f"数据预处理失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"数据预处理失败: {str(e)}"
            )
        
        # 分析绝缘健康状态
        analysis_result = analyze_insulation_health(processed_df)
        
        # 处理结果中的特殊浮点值
        analysis_result = process_special_float_values(analysis_result)
        
        # 保存原始文件（可选）
        if save_file:
            # 生成唯一文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_insulation_{file.filename}"
            file_path = os.path.join(UPLOAD_DIR, filename)
            
            # 保存上传的文件
            with open(temp_path, "rb") as src, open(file_path, "wb") as dst:
                shutil.copyfileobj(src, dst)
            
            # 添加后台任务清理临时文件
            background_tasks.add_task(os.unlink, temp_path)
            
            logger.info(f"保存原始文件: {file_path}")
        
        return JSONResponse(content=analysis_result)
        
    except Exception as e:
        logger.exception("处理绝缘失效检测文件时发生错误")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理文件时发生错误: {str(e)}"
        ) 

@router.post("/bearing", response_model=BearingDiagnosisResult)
async def diagnose_bearing(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    save_file: bool = True
):
    """
    诊断轴承故障状态
    :param background_tasks: 后台任务
    :param file: 上传的CSV文件
    :param save_file: 是否保存原始文件
    :return: 诊断结果
    """
    logger.info(f"接收到轴承故障诊断请求: {file.filename}, 大小: {file.size if hasattr(file, 'size') else '未知'}")
    
    if not file.filename.endswith('.csv'):
        logger.warning(f"上传了非CSV文件: {file.filename}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只接受CSV格式的文件"
        )
    
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp:
            # 保存上传的文件
            shutil.copyfileobj(file.file, temp)
            temp_path = temp.name
            
        logger.info(f"文件已保存到临时位置: {temp_path}")
        
        # 检查文件内容和编码
        detected_encoding = None
        first_lines = []
        for encoding in ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'latin1', 'iso-8859-1']:
            try:
                with open(temp_path, 'r', encoding=encoding) as f:
                    first_lines = [next(f) for _ in range(5) if f.readable()]
                    detected_encoding = encoding
                    logger.info(f"成功使用 {encoding} 编码读取文件头部")
                    break
            except Exception as e:
                logger.warning(f"使用 {encoding} 编码读取文件头时出错: {str(e)}")
                continue
        
        if detected_encoding:
            logger.info(f"检测到文件编码: {detected_encoding}")
            logger.info(f"文件头5行:\n{''.join(first_lines)}")
        else:
            logger.warning("无法检测文件编码，尝试作为二进制文件处理")
        
        # 预处理数据
        try:
            processed_df = preprocess_motor_data(temp_path)
            logger.info(f"成功预处理文件: {file.filename}, 行数: {len(processed_df)}, 列: {processed_df.columns.tolist()}")
        except Exception as e:
            logger.error(f"数据预处理失败: {str(e)}")
            
            # 尝试直接使用pandas读取，检查列名
            try:
                # 尝试不同的编码读取文件
                for encoding in ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'latin1', 'iso-8859-1']:
                    try:
                        raw_df = pd.read_csv(temp_path, encoding=encoding, nrows=5)
                        logger.info(f"使用 {encoding} 成功读取原始CSV，列名: {raw_df.columns.tolist()}")
                        break
                    except Exception as read_err:
                        logger.warning(f"使用 {encoding} 读取CSV失败: {str(read_err)}")
                        continue
            except Exception as pd_err:
                logger.error(f"尝试直接读取CSV失败: {str(pd_err)}")
            
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"数据预处理失败: {str(e)}"
            )
        
        # 分析轴承故障状态
        analysis_result = analyze_bearing_health(processed_df)
        
        # 处理结果中的特殊浮点值
        analysis_result = process_special_float_values(analysis_result)
        
        # 保存原始文件（可选）
        if save_file:
            # 生成唯一文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_bearing_{file.filename}"
            file_path = os.path.join(UPLOAD_DIR, filename)
            
            # 保存上传的文件
            with open(temp_path, "rb") as src, open(file_path, "wb") as dst:
                shutil.copyfileobj(src, dst)
            
            # 添加后台任务清理临时文件
            background_tasks.add_task(os.unlink, temp_path)
            
            logger.info(f"保存原始文件: {file_path}")
        
        return JSONResponse(content=analysis_result)
        
    except Exception as e:
        logger.exception("处理轴承故障诊断文件时发生错误")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理文件时发生错误: {str(e)}"
        ) 

@router.post("/eccentricity", response_model=EccentricityDiagnosisResult)
async def diagnose_eccentricity(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    save_file: bool = True
):
    """
    诊断电机偏心故障
    :param background_tasks: 后台任务
    :param file: 上传的CSV文件
    :param save_file: 是否保存原始文件
    :return: 诊断结果
    """
    logger.info(f"接收到偏心故障诊断请求: {file.filename}, 大小: {file.size if hasattr(file, 'size') else '未知'}")
    
    if not file.filename.endswith('.csv'):
        logger.warning(f"上传了非CSV文件: {file.filename}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只接受CSV格式的文件"
        )
    
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp:
            # 保存上传的文件
            shutil.copyfileobj(file.file, temp)
            temp_path = temp.name
            
        logger.info(f"文件已保存到临时位置: {temp_path}")
        
        # 检查文件内容和编码
        detected_encoding = None
        first_lines = []
        for encoding in ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'latin1', 'iso-8859-1']:
            try:
                with open(temp_path, 'r', encoding=encoding) as f:
                    first_lines = [next(f) for _ in range(5) if f.readable()]
                    detected_encoding = encoding
                    logger.info(f"成功使用 {encoding} 编码读取文件头部")
                    break
            except Exception as e:
                logger.warning(f"使用 {encoding} 编码读取文件头时出错: {str(e)}")
                continue
        
        if detected_encoding:
            logger.info(f"检测到文件编码: {detected_encoding}")
            logger.info(f"文件头5行:\n{''.join(first_lines)}")
        else:
            logger.warning("无法检测文件编码，尝试作为二进制文件处理")
        
        # 预处理数据
        try:
            processed_df = preprocess_motor_data(temp_path)
            logger.info(f"成功预处理文件: {file.filename}, 行数: {len(processed_df)}, 列: {processed_df.columns.tolist()}")
        except Exception as e:
            logger.error(f"数据预处理失败: {str(e)}")
            
            # 尝试直接使用pandas读取，检查列名
            try:
                # 尝试不同的编码读取文件
                for encoding in ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'latin1', 'iso-8859-1']:
                    try:
                        raw_df = pd.read_csv(temp_path, encoding=encoding, nrows=5)
                        logger.info(f"使用 {encoding} 成功读取原始CSV，列名: {raw_df.columns.tolist()}")
                        break
                    except Exception as read_err:
                        logger.warning(f"使用 {encoding} 读取CSV失败: {str(read_err)}")
                        continue
            except Exception as pd_err:
                logger.error(f"尝试直接读取CSV失败: {str(pd_err)}")
            
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"数据预处理失败: {str(e)}"
            )
        
        # 分析偏心故障状态
        analysis_result = analyze_eccentricity_health(processed_df)
        
        # 处理结果中的特殊浮点值
        analysis_result = process_special_float_values(analysis_result)
        
        # 保存原始文件（可选）
        if save_file:
            # 生成唯一文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_eccentricity_{file.filename}"
            file_path = os.path.join(UPLOAD_DIR, filename)
            
            # 保存上传的文件
            with open(temp_path, "rb") as src, open(file_path, "wb") as dst:
                shutil.copyfileobj(src, dst)
            
            # 添加后台任务清理临时文件
            background_tasks.add_task(os.unlink, temp_path)
            
            logger.info(f"保存原始文件: {file_path}")
        
        return JSONResponse(content=analysis_result)
        
    except Exception as e:
        logger.exception("处理偏心故障诊断文件时发生错误")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理文件时发生错误: {str(e)}"
        ) 

@router.post("/broken-bar", response_model=BrokenBarDiagnosisResult)
async def diagnose_broken_bar(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    save_file: bool = True
):
    """
    诊断电机转子断条故障
    :param background_tasks: 后台任务
    :param file: 上传的CSV文件
    :param save_file: 是否保存原始文件
    :return: 诊断结果
    """
    logger.info(f"接收到断条故障诊断请求: {file.filename}, 大小: {file.size if hasattr(file, 'size') else '未知'}")
    
    if not file.filename.endswith('.csv'):
        logger.warning(f"上传了非CSV文件: {file.filename}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只接受CSV格式的文件"
        )
    
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp:
            # 保存上传的文件
            shutil.copyfileobj(file.file, temp)
            temp_path = temp.name
            
        logger.info(f"文件已保存到临时位置: {temp_path}")
        
        # 检查文件内容和编码
        detected_encoding = None
        first_lines = []
        for encoding in ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'latin1', 'iso-8859-1']:
            try:
                with open(temp_path, 'r', encoding=encoding) as f:
                    first_lines = [next(f) for _ in range(5) if f.readable()]
                    detected_encoding = encoding
                    logger.info(f"成功使用 {encoding} 编码读取文件头部")
                    break
            except Exception as e:
                logger.warning(f"使用 {encoding} 编码读取文件头时出错: {str(e)}")
                continue
        
        if detected_encoding:
            logger.info(f"检测到文件编码: {detected_encoding}")
            logger.info(f"文件头5行:\n{''.join(first_lines)}")
        else:
            logger.warning("无法检测文件编码，尝试作为二进制文件处理")
        
        # 预处理数据
        try:
            processed_df = preprocess_motor_data(temp_path)
            logger.info(f"成功预处理文件: {file.filename}, 行数: {len(processed_df)}, 列: {processed_df.columns.tolist()}")
        except Exception as e:
            logger.error(f"数据预处理失败: {str(e)}")
            
            # 尝试直接使用pandas读取，检查列名
            try:
                # 尝试不同的编码读取文件
                for encoding in ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'latin1', 'iso-8859-1']:
                    try:
                        raw_df = pd.read_csv(temp_path, encoding=encoding, nrows=5)
                        logger.info(f"使用 {encoding} 成功读取原始CSV，列名: {raw_df.columns.tolist()}")
                        break
                    except Exception as read_err:
                        logger.warning(f"使用 {encoding} 读取CSV失败: {str(read_err)}")
                        continue
            except Exception as pd_err:
                logger.error(f"尝试直接读取CSV失败: {str(pd_err)}")
            
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"数据预处理失败: {str(e)}"
            )
        
        # 分析断条故障状态
        analysis_result = analyze_broken_bar_health(processed_df)
        
        # 处理结果中的特殊浮点值
        analysis_result = process_special_float_values(analysis_result)
        
        # 保存原始文件（可选）
        if save_file:
            # 生成唯一文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_broken_bar_{file.filename}"
            file_path = os.path.join(UPLOAD_DIR, filename)
            
            # 保存上传的文件
            with open(temp_path, "rb") as src, open(file_path, "wb") as dst:
                shutil.copyfileobj(src, dst)
            
            # 添加后台任务清理临时文件
            background_tasks.add_task(os.unlink, temp_path)
            
            logger.info(f"保存原始文件: {file_path}")
        
        return JSONResponse(content=analysis_result)
        
    except Exception as e:
        logger.exception("处理断条故障诊断文件时发生错误")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理文件时发生错误: {str(e)}"
        ) 