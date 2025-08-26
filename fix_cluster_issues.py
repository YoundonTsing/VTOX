#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VTOX 集群问题一键修复脚本

根据诊断结果，自动修复以下问题：
1. 启动分布式诊断系统的Consumer
2. 启动数据模拟器提供数据输入
3. 验证修复效果

使用方法：
python fix_cluster_issues.py
"""

import asyncio
import aiohttp
import logging
import time
from datetime import datetime
import subprocess
import sys
import os
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("cluster-fix")

class ClusterIssuesFixer:
    def __init__(self):
        self.backend_url = "http://localhost:8000"
        self.session = None
        self.auth_token = None
        
    async def initialize(self):
        """初始化HTTP会话"""
        self.session = aiohttp.ClientSession()
        return True
    
    async def login(self, username="user1", password="password123"):
        """登录获取JWT认证"""
        logger.info("🔐 登录获取JWT认证...")
        try:
            async with self.session.post(
                f"{self.backend_url}/auth/token",
                json={"username": username, "password": password}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.auth_token = data.get("access_token")
                    if self.auth_token:
                        logger.info("✅ 登录成功")
                        return True
                    else:
                        logger.error("❌ 登录响应中没有access_token")
                        return False
                else:
                    logger.error(f"❌ 登录失败: HTTP {response.status}")
                    return False
        except Exception as e:
            logger.error(f"❌ 登录异常: {e}")
            return False
    
    def get_auth_headers(self):
        """获取认证头"""
        if self.auth_token:
            return {"Authorization": f"Bearer {self.auth_token}"}
        return {}
    
    async def fix_distributed_system(self):
        """修复分布式诊断系统 - 启动Consumer"""
        logger.info("🔧 修复1: 启动分布式诊断系统Consumer...")
        
        try:
            # 1. 先初始化系统
            logger.info("   📡 初始化分布式诊断系统...")
            async with self.session.post(
                f"{self.backend_url}/api/v1/diagnosis-stream/initialize",
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 200:
                    logger.info("   ✅ 系统初始化成功")
                else:
                    logger.warning(f"   ⚠️ 初始化状态: {response.status}")
            
            # 2. 启动分布式系统（关键步骤）
            logger.info("   🚀 启动分布式诊断系统Consumer...")
            params = {
                "consumers_per_fault": 2,  # 每种故障类型2个消费者
                "enable_aggregation": "true",  # 转换为字符串
                "enable_monitoring": "true"   # 转换为字符串
            }
            
            async with self.session.post(
                f"{self.backend_url}/api/v1/diagnosis-stream/start",
                params=params,
                headers=self.get_auth_headers()
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("   ✅ 分布式诊断系统Consumer启动成功！")
                    logger.info(f"   📊 配置: {params}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"   ❌ 启动失败: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"   ❌ 启动分布式系统异常: {e}")
            return False
    
    async def fix_data_input(self):
        """修复数据输入问题 - 启动数据模拟器"""
        logger.info("🔧 修复2: 启动数据模拟器...")
        
        try:
            # 检查模拟器文件是否存在
            project_root = Path(__file__).parent
            simulator_path = project_root / "databases" / "multi_vehicle_simulator.py"
            
            if not simulator_path.exists():
                logger.error(f"   ❌ 数据模拟器文件不存在: {simulator_path}")
                return False
            
            logger.info("   🚗 启动多车辆数据模拟器...")
            logger.info(f"   📂 模拟器路径: {simulator_path}")
            
            # 在后台启动模拟器
            simulator_cmd = [
                sys.executable, str(simulator_path),
                "--vehicles", "3",  # 启动3辆车进行测试
                "--duration", "600"  # 运行10分钟
            ]
            
            # 启动模拟器进程（后台运行）
            process = subprocess.Popen(
                simulator_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(project_root)
            )
            
            # 等待几秒检查进程是否启动成功
            await asyncio.sleep(3)
            
            if process.poll() is None:
                logger.info("   ✅ 数据模拟器启动成功！")
                logger.info("   🎯 模拟器将在后台运行，持续发送测试数据")
                return True
            else:
                stdout, stderr = process.communicate()
                logger.error(f"   ❌ 模拟器启动失败")
                if stderr:
                    logger.error(f"   错误信息: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"   ❌ 启动数据模拟器异常: {e}")
            return False
    
    async def verify_fixes(self):
        """验证修复效果"""
        logger.info("🔍 验证修复效果...")
        
        # 等待系统处理数据
        logger.info("   ⏳ 等待系统处理数据 (15秒)...")
        await asyncio.sleep(15)
        
        try:
            # 检查集群状态
            async with self.session.get(
                f"{self.backend_url}/api/v1/cluster/status"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    cluster_data = data.get("data", {})
                    
                    # 分析Worker状态
                    worker_nodes = cluster_data.get("worker_nodes", [])
                    healthy_workers = sum(1 for w in worker_nodes if w.get("status") == "healthy")
                    warning_workers = sum(1 for w in worker_nodes if w.get("status") == "warning")
                    
                    logger.info(f"   📊 Worker状态统计:")
                    logger.info(f"      健康节点: {healthy_workers}")
                    logger.info(f"      警告节点: {warning_workers}")
                    logger.info(f"      总节点数: {len(worker_nodes)}")
                    
                    # 检查是否有任务处理
                    active_tasks = sum(w.get("current_tasks", 0) for w in worker_nodes)
                    logger.info(f"      活跃任务数: {active_tasks}")
                    
                    # 分析修复效果
                    if healthy_workers > 0:
                        logger.info("   ✅ 修复成功：有Worker节点变为健康状态")
                        return True
                    elif active_tasks > 0:
                        logger.info("   ✅ 修复成功：Worker开始处理任务")
                        return True
                    else:
                        logger.warning("   ⚠️ 修复效果待观察：Worker仍在warning状态")
                        return False
                else:
                    logger.error(f"   ❌ 无法获取集群状态: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"   ❌ 验证修复效果异常: {e}")
            return False
    
    async def run_fix(self):
        """执行完整的修复流程"""
        logger.info("🚀 开始VTOX集群问题修复")
        logger.info("="*60)
        
        if not await self.initialize():
            logger.error("❌ 修复环境初始化失败")
            return False
        
        # 步骤1: 登录认证
        if not await self.login():
            logger.error("❌ 登录失败，无法继续修复")
            return False
        
        # 步骤2: 修复分布式诊断系统
        distributed_fixed = await self.fix_distributed_system()
        
        # 步骤3: 修复数据输入
        data_input_fixed = await self.fix_data_input()
        
        # 步骤4: 验证修复效果
        if distributed_fixed or data_input_fixed:
            verification_result = await self.verify_fixes()
        else:
            verification_result = False
        
        # 总结修复结果
        logger.info("\n" + "="*60)
        logger.info("🏁 修复完成 - 结果总结")
        logger.info("="*60)
        
        fixes_applied = []
        if distributed_fixed:
            fixes_applied.append("✅ 分布式诊断系统Consumer已启动")
        if data_input_fixed:
            fixes_applied.append("✅ 数据模拟器已启动")
        
        if fixes_applied:
            logger.info("📋 已应用的修复:")
            for fix in fixes_applied:
                logger.info(f"   {fix}")
        
        if verification_result:
            logger.info("\n🎉 修复成功！系统应该开始正常工作")
            logger.info("💡 建议: 等待1-2分钟后重新检查前端集群状态页面")
        else:
            logger.info("\n⚠️ 修复部分完成，建议手动检查:")
            logger.info("   1. 检查后端服务日志")
            logger.info("   2. 确认Redis服务运行正常")
            logger.info("   3. 重新运行诊断脚本确认")
        
        return len(fixes_applied) > 0
    
    async def cleanup(self):
        """清理资源"""
        if self.session:
            await self.session.close()

async def main():
    """主函数"""
    fixer = ClusterIssuesFixer()
    
    try:
        success = await fixer.run_fix()
        if success:
            print("\n🎯 下一步操作建议:")
            print("1. 打开前端集群状态页面: http://localhost:3000/monitor/cluster-status")
            print("2. 观察Worker节点状态是否改善")
            print("3. 如需更多数据，可运行: python databases/multi_vehicle_simulator.py --vehicles 10")
        else:
            print("\n📞 如需进一步帮助，请:")
            print("1. 检查后端服务是否正常运行")
            print("2. 确认Redis服务状态")
            print("3. 重新运行诊断脚本: python diagnose_cluster_health.py")
    finally:
        await fixer.cleanup()

if __name__ == "__main__":
    asyncio.run(main())