#!/usr/bin/env python3
"""
🚀 自适应消费者扩展系统启动脚本
演示如何启动和配置实时自适应扩展功能
"""

import asyncio
import aiohttp
import logging
import json
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("adaptive-starter")

class AdaptiveSystemStarter:
    def __init__(self):
        self.api_base_url = "http://localhost:8000"
        self.session = None
        self.auth_token = None

    async def initialize(self):
        """初始化HTTP会话和认证"""
        self.session = aiohttp.ClientSession()
        
        # 登录获取token
        try:
            async with self.session.post(
                f"{self.api_base_url}/auth/token",
                json={"username": "user1", "password": "password123"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    self.auth_token = result.get("access_token")
                    logger.info("✅ API认证成功")
                    return True
                else:
                    logger.error("❌ API认证失败")
                    return False
        except Exception as e:
            logger.error(f"❌ 连接API失败: {e}")
            return False

    def get_headers(self):
        """获取认证头"""
        return {"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}

    async def start_adaptive_system(self):
        """启动自适应系统"""
        try:
            logger.info("🧠 启动实时自适应消费者管理系统...")
            
            async with self.session.post(
                f"{self.api_base_url}/api/v1/diagnosis-stream/adaptive/start",
                headers=self.get_headers()
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info("✅ 自适应系统启动成功")
                    logger.info(f"📋 功能特性: {', '.join(result.get('features', []))}")
                    
                    config = result.get('config', {})
                    logger.info("⚙️ 系统配置:")
                    logger.info(f"   监控间隔: {config.get('monitoring_interval', 'N/A')}秒")
                    logger.info(f"   最大消费者数: {config.get('max_consumers_per_fault', 'N/A')}/故障类型")
                    logger.info(f"   CPU安全阈值: {config.get('cpu_safe_threshold', 'N/A')}%")
                    logger.info(f"   内存安全阈值: {config.get('memory_safe_threshold', 'N/A')}%")
                    
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"❌ 启动失败: {error_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ 启动异常: {e}")
            return False

    async def check_system_status(self):
        """检查系统状态"""
        try:
            async with self.session.get(
                f"{self.api_base_url}/api/v1/diagnosis-stream/adaptive/stats",
                headers=self.get_headers()
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    data = result.get('data', {})
                    
                    logger.info("📊 系统状态报告:")
                    logger.info(f"   运行状态: {data.get('status', 'unknown')}")
                    logger.info(f"   运行时间: {data.get('uptime_seconds', 0):.0f}秒")
                    
                    stats = data.get('statistics', {})
                    logger.info(f"   总扩展操作: {stats.get('total_scaling_operations', 0)}")
                    logger.info(f"   成功扩展: {stats.get('successful_scale_ups', 0)}")
                    logger.info(f"   成功缩减: {stats.get('successful_scale_downs', 0)}")
                    logger.info(f"   预防操作: {stats.get('prevented_operations', 0)}")
                    
                    metrics = data.get('recent_metrics', {})
                    logger.info(f"   CPU使用率: {metrics.get('latest_cpu_usage', 0):.1f}%")
                    logger.info(f"   内存使用率: {metrics.get('latest_memory_usage', 0):.1f}%")
                    logger.info(f"   系统吞吐量: {metrics.get('latest_throughput', 0):.1f} msg/s")
                    
                    return True
                else:
                    logger.error("❌ 获取状态失败")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ 检查状态异常: {e}")
            return False

    async def optimize_config_for_demo(self):
        """为演示优化配置"""
        try:
            logger.info("⚙️ 优化配置以适合演示环境...")
            
            demo_config = {
                "monitoring_interval": 10,      # 更频繁的监控
                "high_load_threshold": 0.7,     # 更敏感的扩展触发
                "low_load_threshold": 0.25,     # 更敏感的缩减触发
                "cpu_safe_threshold": 75.0,     # 稍微放宽CPU限制
                "scale_step_size": 1,           # 更平滑的扩展
                "cooldown_period_minutes": 5    # 更短的冷却期
            }
            
            async with self.session.put(
                f"{self.api_base_url}/api/v1/diagnosis-stream/adaptive/config",
                headers=self.get_headers(),
                json=demo_config
            ) as response:
                if response.status == 200:
                    logger.info("✅ 演示配置已应用")
                    logger.info("   🎯 监控间隔: 10秒 (更快响应)")
                    logger.info("   🎯 负载阈值: 70%/25% (更敏感)")
                    logger.info("   🎯 扩展步长: 1个消费者 (更平滑)")
                    logger.info("   🎯 冷却期: 5分钟 (更快调整)")
                    return True
                else:
                    logger.warning("⚠️ 配置优化失败，使用默认配置")
                    return False
                    
        except Exception as e:
            logger.warning(f"⚠️ 配置优化异常: {e}")
            return False

    async def simulate_load_scenarios(self):
        """模拟不同负载场景"""
        logger.info("🧪 模拟不同负载场景...")
        
        scenarios = [
            {
                "name": "正常负载",
                "fault_type": "bearing",
                "pending_messages": 100,
                "cpu_usage": 45.0,
                "memory_usage": 55.0
            },
            {
                "name": "高负载场景",
                "fault_type": "bearing", 
                "pending_messages": 5000,
                "cpu_usage": 60.0,
                "memory_usage": 65.0
            },
            {
                "name": "极高负载",
                "fault_type": "turn_fault",
                "pending_messages": 15000,
                "cpu_usage": 55.0,
                "memory_usage": 70.0
            },
            {
                "name": "低负载场景",
                "fault_type": "insulation",
                "pending_messages": 10,
                "cpu_usage": 25.0,
                "memory_usage": 35.0
            }
        ]
        
        for scenario in scenarios:
            try:
                logger.info(f"🔬 测试场景: {scenario['name']}")
                
                params = {
                    "fault_type": scenario["fault_type"],
                    "pending_messages": scenario["pending_messages"],
                    "cpu_usage": scenario["cpu_usage"],
                    "memory_usage": scenario["memory_usage"]
                }
                
                async with self.session.post(
                    f"{self.api_base_url}/api/v1/diagnosis-stream/adaptive/simulate",
                    headers=self.get_headers(),
                    params=params
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        decision = result.get('data', {}).get('decision', {})
                        
                        action = decision.get('action', 'unknown')
                        confidence = decision.get('confidence', 0)
                        reasoning = decision.get('reasoning', [])
                        
                        logger.info(f"   决策: {action}")
                        logger.info(f"   置信度: {confidence:.2f}")
                        logger.info(f"   原因: {', '.join(reasoning)}")
                        
                        if action != 'maintain':
                            current = decision.get('current_count', 0)
                            target = decision.get('target_count', 0)
                            logger.info(f"   调整: {current} → {target} 个消费者")
                    else:
                        logger.warning(f"   ⚠️ 模拟失败")
                        
            except Exception as e:
                logger.error(f"   ❌ 模拟异常: {e}")
            
            await asyncio.sleep(1)  # 短暂间隔

    async def monitor_for_demo(self, duration_minutes=5):
        """监控系统运行（演示用）"""
        logger.info(f"👀 开始监控系统运行 ({duration_minutes}分钟)...")
        
        end_time = datetime.now().timestamp() + duration_minutes * 60
        check_interval = 30  # 30秒检查一次
        
        while datetime.now().timestamp() < end_time:
            try:
                await self.check_system_status()
                logger.info(f"⏰ 继续监控中... (剩余 {(end_time - datetime.now().timestamp())/60:.1f} 分钟)")
                await asyncio.sleep(check_interval)
                
            except KeyboardInterrupt:
                logger.info("👋 用户中断监控")
                break
            except Exception as e:
                logger.error(f"❌ 监控异常: {e}")
                await asyncio.sleep(10)

    async def cleanup(self):
        """清理资源"""
        if self.session:
            await self.session.close()

    async def run_demo(self):
        """运行完整演示"""
        try:
            print("""
🧠 实时自适应消费者扩展系统演示
=====================================

本演示将：
1. 启动自适应管理系统
2. 优化配置适合演示环境  
3. 模拟不同负载场景
4. 监控系统运行状态
5. 展示智能决策过程

请确保：
✅ Redis服务正在运行
✅ 后端API服务已启动
✅ 有足够的系统资源
            """)
            
            # 初始化
            if not await self.initialize():
                return
            
            # 启动自适应系统
            if not await self.start_adaptive_system():
                return
            
            await asyncio.sleep(2)
            
            # 优化配置
            await self.optimize_config_for_demo()
            await asyncio.sleep(2)
            
            # 模拟场景
            await self.simulate_load_scenarios()
            await asyncio.sleep(5)
            
            # 检查状态
            await self.check_system_status()
            
            print("""
🎉 演示设置完成！

自适应系统现在正在运行，它会：
• 每10秒监控一次系统状态
• 根据负载自动调整消费者数量
• 在安全范围内进行智能扩展
• 记录所有决策和操作

你可以：
1. 通过API查看实时状态
2. 调整配置参数
3. 查看决策历史
4. 模拟不同负载场景

监控将持续5分钟，按Ctrl+C可提前结束。
            """)
            
            # 监控运行
            await self.monitor_for_demo(5)
            
            logger.info("🎊 演示完成！自适应系统将继续在后台运行。")
            
        except Exception as e:
            logger.error(f"❌ 演示异常: {e}")
        finally:
            await self.cleanup()

async def main():
    """主函数"""
    starter = AdaptiveSystemStarter()
    await starter.run_demo()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 演示已中断")
    except Exception as e:
        print(f"\n❌ 运行失败: {e}") 