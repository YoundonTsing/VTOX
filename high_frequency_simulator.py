#!/usr/bin/env python3
"""
⚡ 3000Hz 高频数据模拟器
专为高频数据传输设计，每秒发送3000次
"""

import asyncio
import aiohttp
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, List
import numpy as np
import signal
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('high_freq_simulator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("high-freq-simulator")

class HighFrequencyDataGenerator:
    """高频数据生成器"""
    
    def __init__(self, vehicle_id: str):
        self.vehicle_id = vehicle_id
        self.sampling_rate = 3000  # 3000Hz
        self.fundamental_freq = 50.0
        self.rpm = 1500
        self.current_index = 0
        self.batch_size = 1  # 每次只发送1个数据点，减少延迟
        
        # 故障配置（可变化）
        self.fault_types = ["normal", "turn_fault", "broken_bar", "bearing"]
        self.current_fault_index = 0
        self.fault_change_counter = 0
        
        logger.info(f"🔧 高频生成器初始化: {vehicle_id}")
        logger.info(f"   采样率: {self.sampling_rate} Hz")
        logger.info(f"   批次大小: {self.batch_size}")
    
    def generate_high_freq_data(self) -> Dict[str, Any]:
        """生成单个高频数据点"""
        t = self.current_index / self.sampling_rate
        self.current_index += 1
        
        # 动态切换故障类型（每1000个数据点切换一次）
        self.fault_change_counter += 1
        if self.fault_change_counter >= 1000:
            self.current_fault_index = (self.current_fault_index + 1) % len(self.fault_types)
            self.fault_change_counter = 0
            logger.info(f"🔄 {self.vehicle_id} 切换故障类型: {self.fault_types[self.current_fault_index]}")
        
        current_fault = self.fault_types[self.current_fault_index]
        severity = 0.2 if current_fault != "normal" else 0.0
        
        # 基础三相电流
        amplitude = 10.0
        phase_shift = 2 * np.pi / 3
        
        ia = amplitude * np.sin(2 * np.pi * self.fundamental_freq * t)
        ib = amplitude * np.sin(2 * np.pi * self.fundamental_freq * t + phase_shift)
        ic = amplitude * np.sin(2 * np.pi * self.fundamental_freq * t + 2 * phase_shift)
        
        # 根据故障类型添加特征
        if current_fault == "turn_fault" and severity > 0:
            ia *= (1 + 0.5 * severity)
            ib *= (1 - 0.2 * severity)
        elif current_fault == "broken_bar" and severity > 0:
            slip = 0.02
            sideband_freq = self.fundamental_freq * (1 - 2 * slip)
            ia += 0.15 * severity * amplitude * np.sin(2 * np.pi * sideband_freq * t)
        elif current_fault == "bearing" and severity > 0:
            bearing_freq = 120.5
            ia += 0.3 * severity * np.sin(2 * np.pi * bearing_freq * t)
        
        # 添加噪声
        noise_level = 0.02
        ia += np.random.normal(0, noise_level)
        ib += np.random.normal(0, noise_level)
        ic += np.random.normal(0, noise_level)
        
        # 构建单个数据点
        data_point = {
            "时间": float(t),
            "Ia": float(ia),
            "Ib": float(ib),
            "Ic": float(ic),
            "vibration_x": float(np.random.normal(0, 0.1)),
            "vibration_y": float(np.random.normal(0, 0.1)),
            "insulation_resistance": float(1000.0 + np.random.normal(0, 10)),
            "leakage_current": float(0.001 + np.random.normal(0, 0.0001)),
            "temperature": float(45.0 + np.random.normal(0, 1)),
            "rpm": self.rpm,
            "load": 80 + 10 * severity
        }
        
        return {
            "sensor_data": {
                "data": [data_point],  # 只包含1个数据点
                "sampling_rate": self.sampling_rate,
                "batch_size": self.batch_size,
                "fault_type": current_fault,
                "fault_severity": severity,
                "timestamp": datetime.now().isoformat()
            },
            "location": f"高频测试_{self.vehicle_id}",
            "metadata": {
                "high_frequency_mode": True,
                "vehicle_id": self.vehicle_id,
                "data_index": self.current_index,
                "generation_timestamp": datetime.now().isoformat()
            }
        }

class HighFrequencySimulator:
    """3000Hz高频模拟器"""
    
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url
        self.vehicle_id = "HIGH_FREQ_VEHICLE_001"
        self.generator = HighFrequencyDataGenerator(self.vehicle_id)
        self.session: aiohttp.ClientSession = None
        self.running = False
        
        # 性能统计
        self.total_sent = 0
        self.total_errors = 0
        self.start_time = time.time()
        self.last_report_time = time.time()
        self.last_report_count = 0
        
        # API端点
        self.publish_url = f"{api_base_url}/api/v1/diagnosis-stream/simulator/vehicles/{self.vehicle_id}/data"
        
        logger.info(f"⚡ 高频模拟器初始化")
        logger.info(f"   目标频率: 3000 Hz")
        logger.info(f"   API端点: {self.publish_url}")
    
    async def initialize_session(self):
        """初始化HTTP会话"""
        headers = {"Content-Type": "application/json"}
        timeout = aiohttp.ClientTimeout(total=10, connect=5)
        
        self.session = aiohttp.ClientSession(
            headers=headers,
            timeout=timeout,
            connector=aiohttp.TCPConnector(limit=100, limit_per_host=100)
        )
        
        logger.info("🔗 高频模拟器HTTP会话初始化完成")
    
    async def send_data(self, data: Dict[str, Any]) -> bool:
        """发送单个数据包"""
        try:
            async with self.session.post(self.publish_url, json=data) as response:
                if response.status == 200:
                    self.total_sent += 1
                    return True
                else:
                    self.total_errors += 1
                    if self.total_errors % 100 == 1:  # 每100个错误打印一次
                        error_text = await response.text()
                        logger.error(f"❌ API错误 {response.status}: {error_text}")
                    return False
        except Exception as e:
            self.total_errors += 1
            if self.total_errors % 100 == 1:  # 每100个错误打印一次
                logger.error(f"❌ 发送异常: {e}")
            return False
    
    def print_performance_stats(self):
        """打印性能统计"""
        current_time = time.time()
        runtime = current_time - self.start_time
        interval = current_time - self.last_report_time
        
        if interval >= 5.0:  # 每5秒报告一次
            current_rate = (self.total_sent - self.last_report_count) / interval
            overall_rate = self.total_sent / runtime
            success_rate = self.total_sent / max(1, self.total_sent + self.total_errors) * 100
            
            logger.info(f"📊 性能统计:")
            logger.info(f"   当前频率: {current_rate:.1f} Hz")
            logger.info(f"   平均频率: {overall_rate:.1f} Hz") 
            logger.info(f"   总发送数: {self.total_sent}")
            logger.info(f"   成功率: {success_rate:.1f}%")
            logger.info(f"   运行时间: {runtime:.1f}s")
            
            self.last_report_time = current_time
            self.last_report_count = self.total_sent
    
    async def run_high_frequency_simulation(self):
        """运行3000Hz高频模拟"""
        logger.info("🚀 开始3000Hz高频数据模拟")
        
        self.running = True
        target_interval = 1.0 / 3000  # 目标间隔：1/3000 秒 ≈ 0.33毫秒
        
        while self.running:
            start_time = time.time()
            
            # 生成并发送数据
            data = self.generator.generate_high_freq_data()
            await self.send_data(data)
            
            # 打印性能统计
            self.print_performance_stats()
            
            # 计算实际延迟并调整
            elapsed = time.time() - start_time
            sleep_time = max(0, target_interval - elapsed)
            
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
            elif elapsed > target_interval * 2:  # 如果处理时间过长，警告
                if self.total_sent % 1000 == 0:
                    logger.warning(f"⚠️ 处理时间过长: {elapsed*1000:.2f}ms > {target_interval*1000:.2f}ms")
    
    async def cleanup(self):
        """清理资源"""
        self.running = False
        if self.session:
            await self.session.close()
        
        # 最终统计
        runtime = time.time() - self.start_time
        avg_frequency = self.total_sent / runtime if runtime > 0 else 0
        
        logger.info("🏁 高频模拟器停止")
        logger.info(f"📊 最终统计:")
        logger.info(f"   运行时间: {runtime:.1f}s")
        logger.info(f"   总发送数: {self.total_sent}")
        logger.info(f"   总错误数: {self.total_errors}")
        logger.info(f"   平均频率: {avg_frequency:.1f} Hz")
        logger.info(f"   成功率: {self.total_sent / max(1, self.total_sent + self.total_errors) * 100:.1f}%")

async def main():
    """主函数"""
    print("""
    ⚡ 3000Hz 高频数据模拟器
    
    特性：
    - 目标频率: 3000 Hz (每秒3000次)
    - 单点数据: 每次发送1个数据点
    - 动态故障: 自动切换故障类型
    - 实时统计: 每5秒报告性能
    - 按 Ctrl+C 停止
    """)
    
    simulator = HighFrequencySimulator()
    
    # 信号处理
    def signal_handler(signum, frame):
        logger.info("🛑 收到停止信号，正在关闭...")
        simulator.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await simulator.initialize_session()
        await simulator.run_high_frequency_simulation()
    except KeyboardInterrupt:
        logger.info("👋 用户中断")
    except Exception as e:
        logger.error(f"❌ 运行异常: {e}")
    finally:
        await simulator.cleanup()

if __name__ == "__main__":
    asyncio.run(main()) 