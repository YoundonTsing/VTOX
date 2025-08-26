"""
诊断相关的数据模型定义
"""
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field


class DiagnosisStatus:
    """诊断状态枚举"""
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    FAULT = "FAULT"


class InsulationStatus:
    """绝缘状态枚举"""
    HEALTHY = "HEALTHY"
    DEGRADING = "DEGRADING"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class FeatureScores(BaseModel):
    """特征评分模型"""
    I2_avg: float = Field(0.0, description="负序电流平均值评分")
    I2_I1_ratio: float = Field(0.0, description="负序/正序比值评分")
    delta_I2_avg: float = Field(0.0, description="负序电流残差平均值评分")
    unbalance_avg: float = Field(0.0, description="电流不平衡度评分")
    kurtosis_delta_iq: float = Field(0.0, description="ΔI_q峭度评分")
    delta_eta_avg: float = Field(0.0, description="效率残差平均值评分")


class InsulationFeatureScores(BaseModel):
    """绝缘特征评分模型"""
    temp_ratio: float = Field(0.0, description="绕组温度比率评分")
    temp_rise_rate: float = Field(0.0, description="温升速率评分")
    thermal_residual: float = Field(0.0, description="温度模型残差评分")
    efficiency_residual: float = Field(0.0, description="效率残差评分")
    current_residual_trend: float = Field(0.0, description="电流残差趋势评分")
    thermal_aging: float = Field(0.0, description="热老化累积评分")


class Features(BaseModel):
    """特征参数模型"""
    I2_avg: float = Field(0.0, description="负序电流平均值")
    I2_max: float = Field(0.0, description="负序电流最大值")
    I2_I1_ratio: float = Field(0.0, description="负序/正序比值")
    unbalance_avg: float = Field(0.0, description="电流不平衡度平均值")
    unbalance_max: float = Field(0.0, description="电流不平衡度最大值")
    delta_I2_avg: float = Field(0.0, description="负序电流残差平均值")
    delta_I2_std: float = Field(0.0, description="负序电流残差标准差")
    kurtosis_delta_iq: float = Field(0.0, description="ΔI_q峭度")
    delta_Iq_std: float = Field(0.0, description="ΔI_q标准差")
    delta_eta_avg: float = Field(0.0, description="效率残差平均值")
    delta_eta_std: float = Field(0.0, description="效率残差标准差")


class InsulationFeatures(BaseModel):
    """绝缘特征参数模型"""
    temp_ratio: float = Field(0.0, description="绕组温度比率")
    temp_rise_rate: float = Field(0.0, description="温升速率(°C/min)")
    thermal_residual: float = Field(0.0, description="温度模型残差(°C)")
    efficiency_residual: float = Field(0.0, description="效率残差")
    current_residual_trend: float = Field(0.0, description="电流残差趋势")
    thermal_aging: float = Field(0.0, description="热老化累积")


class DiagnosisResult(BaseModel):
    """诊断结果基础模型"""
    status: str = Field(..., description="诊断状态: normal, warning, fault")
    score: float = Field(..., description="故障评分(0-1)")
    features: Dict[str, Any] = Field(..., description="特征参数")
    time_series: Optional[Dict[str, List[float]]] = Field(None, description="时域波形数据")
    frequency_spectrum: Optional[Dict[str, List[float]]] = Field(None, description="频谱数据")
    diagnosis_conclusion: str = Field(..., description="诊断结论")
    suggestions: List[str] = Field(..., description="建议措施")

class TurnToTurnDiagnosisResult(DiagnosisResult):
    """匝间短路诊断结果模型"""
    fault_type: Optional[str] = Field(None, description="故障类型: phase_a, phase_b, phase_c, mixed")
    fault_severity: Optional[float] = Field(None, description="故障严重程度(0-1)")
    asymmetry_index: Optional[float] = Field(None, description="不对称指数")
    phases_data: Optional[Dict[str, Dict[str, List[float]]]] = Field(None, description="各相数据")

class InsulationDiagnosisResult(DiagnosisResult):
    """绝缘失效诊断结果模型"""
    insulation_index: float = Field(..., description="绝缘健康指数(0-1)")
    leakage_current: Optional[float] = Field(None, description="估计的泄漏电流(mA)")
    temperature_rise: Optional[float] = Field(None, description="估计的温升(°C)")
    remaining_life: Optional[float] = Field(None, description="估计的剩余寿命(h)")

class BearingDiagnosisResult(BaseModel):
    """轴承故障诊断结果模型"""
    status: str = Field(..., description="诊断状态: normal, warning, fault")
    score: float = Field(..., description="故障评分(0-1)")
    fault_type: Optional[str] = Field(None, description="故障类型: inner_race, outer_race, ball, cage, normal")
    fault_probabilities: Dict[str, float] = Field(..., description="各故障类型概率")
    features: Dict[str, Any] = Field(..., description="特征参数")
    time_series: Optional[Dict[str, List[float]]] = Field(None, description="时域波形数据")
    frequency_spectrum: Optional[Dict[str, List[float]]] = Field(None, description="频谱数据")
    envelope_spectrum: Optional[Dict[str, List[float]]] = Field(None, description="包络谱数据")
    diagnosis_conclusion: str = Field(..., description="诊断结论")
    suggestions: List[str] = Field(..., description="建议措施")

class EccentricityDiagnosisResult(BaseModel):
    """偏心故障诊断结果模型"""
    status: str = Field(..., description="诊断状态: normal, warning, fault")
    score: float = Field(..., description="故障评分(0-1)")
    eccentricity_type: str = Field(..., description="偏心类型: static, dynamic, mixed, normal")
    confidence: float = Field(..., description="诊断置信度(0-1)")
    features: Dict[str, Any] = Field(..., description="特征参数")
    time_series: Optional[Dict[str, List[float]]] = Field(None, description="时域波形数据")
    frequency_spectrum: Optional[Dict[str, List[float]]] = Field(None, description="频谱数据")
    envelope_spectrum: Optional[Dict[str, List[float]]] = Field(None, description="包络谱数据")
    diagnosis_conclusion: str = Field(..., description="诊断结论")
    suggestions: List[str] = Field(..., description="建议措施")

class BrokenBarDiagnosisResult(BaseModel):
    """断条故障诊断结果模型"""
    status: str = Field(..., description="诊断状态: normal, warning, fault")
    score: float = Field(..., description="故障评分(0-1)")
    broken_bar_count: Optional[int] = Field(0, description="估计断条数量")
    confidence: float = Field(..., description="诊断置信度(0-1)")
    features: Dict[str, Any] = Field(..., description="特征参数")
    time_series: Optional[Dict[str, List[float]]] = Field(None, description="时域波形数据")
    frequency_spectrum: Optional[Dict[str, List[float]]] = Field(None, description="频谱数据")
    diagnosis_conclusion: str = Field(..., description="诊断结论")
    suggestions: List[str] = Field(..., description="建议措施") 