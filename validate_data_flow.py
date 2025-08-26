#!/usr/bin/env python3
"""
验证数据流程序 - 现实可行的高频测试
测试目标：100-200Hz (每秒100-200次数据发送)
验证后端实时调试功能
"""

import asyncio
import aiohttp
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any
import numpy as np
import signal
import sys

# 修复Windows编码问题 - 不使用emoji
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_validation.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("data-validator")

class DataFlowValidator:
    """数据流验证器"""
    
    def __init__(self, target_frequency: int = 100):
        self.target_frequency = target_frequency  # 目标频率 Hz
        self.vehicle_id = f"VALIDATOR_{target_frequency}HZ"
        self.api_base_url = "http://localhost:8000"
        self.session = None
        self.running = False
        
        # 统计
        self.total_sent = 0
        self.total_success = 0
        self.total_errors = 0
        self.start_time = time.time()
        self.last_report_time = time.time()
        self.last_report_count = 0
        
        # API端点
        self.publish_url = f"{self.api_base_url}/api/v1/diagnosis-stream/simulator/vehicles/{self.vehicle_id}/data"
        
        logger.info(f"数据流验证器初始化")
        logger.info(f"目标频率: {target_frequency} Hz")
        logger.info(f"车辆ID: {self.vehicle_id}")
        logger.info(f"API端点: {self.publish_url}")
    
    def generate_test_data(self) -> Dict[str, Any]:
        """生成测试数据"""
        current_time = time.time()
        
        # 生成单个传感器数据点
        data_point = {
            "时间": current_time,
            "Ia": 10.0 + np.random.normal(0, 0.1),
            "Ib": 10.0 + np.random.normal(0, 0.1),
            "Ic": 10.0 + np.random.normal(0, 0.1),
            "vibration_x": np.random.normal(0, 0.1),
            "vibration_y": np.random.normal(0, 0.1),
            "insulation_resistance": 1000.0 + np.random.normal(0, 10),
            "leakage_current": 0.001 + np.random.normal(0, 0.0001),
            "temperature": 45.0 + np.random.normal(0, 1),
            "rpm": 1500,
            "load": 80
        }
        
        return {
            "sensor_data": {
                "data": [data_point],
                "sampling_rate": self.target_frequency,
                "batch_size": 1,
                "fault_type": "normal",
                "fault_severity": 0.1,
                "timestamp": datetime.now().isoformat()
            },
            "location": f"验证测试_{self.target_frequency}Hz",
            "metadata": {
                "validation_mode": True,
                "target_frequency": self.target_frequency,
                "data_index": self.total_sent,
                "generation_timestamp": datetime.now().isoformat()
            }
        }
    
    async def initialize_session(self):
        """初始化HTTP会话"""
        headers = {"Content-Type": "application/json"}
        timeout = aiohttp.ClientTimeout(total=5, connect=2)
        
        self.session = aiohttp.ClientSession(
            headers=headers,
            timeout=timeout,
            connector=aiohttp.TCPConnector(limit=50)
        )
        
        logger.info("HTTP会话初始化完成")
    
    async def send_data(self, data: Dict[str, Any]) -> bool:
        """发送数据并记录结果"""
        try:
            async with self.session.post(self.publish_url, json=data) as response:
                if response.status == 200:
                    self.total_success += 1
                    return True
                else:
                    self.total_errors += 1
                    if self.total_errors <= 5:  # 只记录前5个错误
                        error_text = await response.text()
                        logger.error(f"API错误 {response.status}: {error_text}")
                    return False
        except Exception as e:
            self.total_errors += 1
            if self.total_errors <= 5:
                logger.error(f"发送异常: {e}")
            return False
    
    def print_stats(self):
        """打印统计信息"""
        current_time = time.time()
        runtime = current_time - self.start_time
        interval = current_time - self.last_report_time
        
        # 每5秒报告一次
        if interval >= 5.0:
            self.total_sent = self.total_success + self.total_errors
            current_rate = (self.total_sent - self.last_report_count) / interval
            overall_rate = self.total_sent / runtime if runtime > 0 else 0
            success_rate = self.total_success / max(1, self.total_sent) * 100
            
            logger.info("=== 数据流验证统计 ===")
            logger.info(f"目标频率: {self.target_frequency} Hz")
            logger.info(f"实际频率: {current_rate:.1f} Hz (当前) / {overall_rate:.1f} Hz (平均)")
            logger.info(f"数据发送: 总计{self.total_sent} 成功{self.total_success} 错误{self.total_errors}")
            logger.info(f"成功率: {success_rate:.1f}%")
            logger.info(f"运行时间: {runtime:.1f}秒")
            
            # 性能评估
            if current_rate >= self.target_frequency * 0.9:
                logger.info("性能评估: 优秀 - 达到目标频率")
            elif current_rate >= self.target_frequency * 0.7:
                logger.info("性能评估: 良好 - 接近目标频率") 
            else:
                logger.info("性能评估: 需优化 - 未达到目标频率")
            
            self.last_report_time = current_time
            self.last_report_count = self.total_sent
    
    async def run_validation(self, duration: int = 30):
        """运行验证测试"""
        logger.info(f"开始数据流验证测试 - 目标{self.target_frequency}Hz，持续{duration}秒")
        
        self.running = True
        target_interval = 1.0 / self.target_frequency
        end_time = time.time() + duration
        
        while self.running and time.time() < end_time:
            start_time = time.time()
            
            # 生成并发送数据
            data = self.generate_test_data()
            await self.send_data(data)
            
            # 打印统计
            self.print_stats()
            
            # 控制发送频率
            elapsed = time.time() - start_time
            sleep_time = max(0, target_interval - elapsed)
            
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        self.running = False
    
    async def cleanup(self):
        """清理并生成最终报告"""
        if self.session:
            await self.session.close()
        
        runtime = time.time() - self.start_time
        total_sent = self.total_success + self.total_errors
        avg_frequency = total_sent / runtime if runtime > 0 else 0
        
        logger.info("=== 最终验证报告 ===")
        logger.info(f"测试时长: {runtime:.1f}秒")
        logger.info(f"目标频率: {self.target_frequency} Hz")
        logger.info(f"实际频率: {avg_frequency:.1f} Hz")
        logger.info(f"频率达成率: {avg_frequency/self.target_frequency*100:.1f}%")
        logger.info(f"数据发送总计: {total_sent}")
        logger.info(f"成功发送: {self.total_success}")
        logger.info(f"发送错误: {self.total_errors}")
        logger.info(f"成功率: {self.total_success/max(1,total_sent)*100:.1f}%")
        
        # 建议
        if avg_frequency >= self.target_frequency * 0.9 and self.total_success > 0:
            logger.info("结论: 验证成功！系统支持该频率")
        elif self.total_errors > total_sent * 0.1:
            logger.info("结论: 后端处理有问题，需要检查")
        else:
            logger.info("结论: 频率过高，建议降低到合适范围")

async def test_multiple_frequencies():
    """测试多个频率"""
    frequencies = [50, 100, 150, 200]  # 测试频率范围
    
    logger.info("开始多频率验证测试")
    
    for freq in frequencies:
        logger.info(f"\n{'='*50}")
        logger.info(f"测试频率: {freq} Hz")
        logger.info(f"{'='*50}")
        
        validator = DataFlowValidator(target_frequency=freq)
        
        try:
            await validator.initialize_session()
            await validator.run_validation(duration=15)  # 每个频率测试15秒
        except Exception as e:
            logger.error(f"频率{freq}Hz测试失败: {e}")
        finally:
            await validator.cleanup()
        
        # 测试间隔
        logger.info("等待5秒后进行下一个频率测试...")
        await asyncio.sleep(5)

async def main():
    """主函数"""
    print("""
    数据流验证程序
    
    功能：
    - 测试现实可行的数据发送频率
    - 验证后端实时调试功能
    - 评估系统性能上限
    - 生成详细测试报告
    """)
    
    # 信号处理
    def signal_handler(signum, frame):
        logger.info("收到停止信号，正在关闭...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await test_multiple_frequencies()
    except KeyboardInterrupt:
        logger.info("用户中断测试")
    except Exception as e:
        logger.error(f"测试运行异常: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 