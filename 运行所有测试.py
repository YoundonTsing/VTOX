#!/usr/bin/env python3
"""
Redis Stream缓存优化方案测试运行器
协调运行所有测试程序
"""

import asyncio
import subprocess
import sys
import os
import time
from datetime import datetime

class TestRunner:
    def __init__(self):
        self.test_scripts = [
            {
                "name": "快速功能测试",
                "script": "快速测试缓存优化.py",
                "description": "快速验证API接口和基本功能",
                "estimated_time": "2分钟"
            },
            {
                "name": "性能对比测试",
                "script": "性能对比测试.py", 
                "description": "对比缓存优化前后的性能差异",
                "estimated_time": "3分钟"
            },
            {
                "name": "综合压力测试",
                "script": "测试Redis_Stream缓存优化方案.py",
                "description": "全面的功能和性能测试",
                "estimated_time": "5分钟"
            }
        ]
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 Redis Stream缓存优化方案测试套件")
        print("=" * 60)
        print(f"测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 检查必要的依赖
        if not self.check_dependencies():
            print("❌ 依赖检查失败，请安装必要的包")
            return
        
        # 显示测试计划
        self.show_test_plan()
        
        # 询问用户是否继续
        response = input("\n是否开始执行测试？(y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("测试已取消")
            return
        
        print("\n🔄 开始执行测试...")
        total_start_time = time.time()
        
        # 运行每个测试
        for i, test in enumerate(self.test_scripts, 1):
            print(f"\n{'='*60}")
            print(f"📋 测试 {i}/{len(self.test_scripts)}: {test['name']}")
            print(f"📝 描述: {test['description']}")
            print(f"⏱️ 预计耗时: {test['estimated_time']}")
            print("="*60)
            
            if not self.run_single_test(test):
                print(f"❌ {test['name']} 执行失败")
                response = input("是否继续执行后续测试？(y/N): ").strip().lower()
                if response not in ['y', 'yes']:
                    break
            else:
                print(f"✅ {test['name']} 执行完成")
            
            # 测试间隔
            if i < len(self.test_scripts):
                print("\n⏳ 等待5秒后执行下一个测试...")
                time.sleep(5)
        
        total_time = time.time() - total_start_time
        print(f"\n🎉 所有测试执行完成！总耗时: {total_time/60:.1f}分钟")
        print(f"测试结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    def check_dependencies(self) -> bool:
        """检查依赖"""
        print("🔍 检查测试依赖...")
        
        required_packages = ['aiohttp', 'asyncio']
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package)
                print(f"  ✅ {package}")
            except ImportError:
                print(f"  ❌ {package}")
                missing_packages.append(package)
        
        if missing_packages:
            print(f"\n❌ 缺少以下依赖包: {', '.join(missing_packages)}")
            print("请运行以下命令安装:")
            print(f"pip install {' '.join(missing_packages)}")
            return False
        
        print("✅ 所有依赖检查通过")
        return True
    
    def show_test_plan(self):
        """显示测试计划"""
        print("\n📋 测试执行计划:")
        total_estimated_minutes = 0
        
        for i, test in enumerate(self.test_scripts, 1):
            print(f"  {i}. {test['name']}")
            print(f"     📝 {test['description']}")
            print(f"     ⏱️ 预计耗时: {test['estimated_time']}")
            print(f"     📄 脚本: {test['script']}")
            
            # 估算总时间（简单解析）
            time_str = test['estimated_time']
            if '分钟' in time_str:
                minutes = int(time_str.split('分钟')[0])
                total_estimated_minutes += minutes
            print()
        
        print(f"📊 总预计耗时: {total_estimated_minutes}分钟")
    
    def run_single_test(self, test: dict) -> bool:
        """运行单个测试"""
        script_path = test['script']
        
        # 检查脚本文件是否存在
        if not os.path.exists(script_path):
            print(f"❌ 测试脚本不存在: {script_path}")
            return False
        
        try:
            print(f"▶️ 启动测试: {script_path}")
            start_time = time.time()
            
            # 运行测试脚本
            result = subprocess.run([
                sys.executable, script_path
            ], capture_output=True, text=True, encoding='utf-8')
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"⏱️ 实际耗时: {duration/60:.1f}分钟")
            
            # 显示输出
            if result.stdout:
                print("📤 测试输出:")
                print(result.stdout)
            
            if result.stderr:
                print("⚠️ 错误输出:")
                print(result.stderr)
            
            # 检查返回码
            if result.returncode == 0:
                print(f"✅ 测试成功完成")
                return True
            else:
                print(f"❌ 测试失败，返回码: {result.returncode}")
                return False
                
        except Exception as e:
            print(f"❌ 测试执行异常: {str(e)}")
            return False
    
    def run_quick_test_only(self):
        """只运行快速测试"""
        print("🚀 快速测试模式")
        print("=" * 40)
        
        quick_test = self.test_scripts[0]  # 快速功能测试
        self.run_single_test(quick_test)
    
    def run_performance_test_only(self):
        """只运行性能测试"""
        print("📈 性能测试模式")
        print("=" * 40)
        
        perf_test = self.test_scripts[1]  # 性能对比测试
        self.run_single_test(perf_test)

def show_menu():
    """显示菜单"""
    print("🚀 Redis Stream缓存优化测试菜单")
    print("=" * 40)
    print("1. 运行所有测试 (推荐)")
    print("2. 只运行快速功能测试")
    print("3. 只运行性能对比测试") 
    print("4. 查看测试说明")
    print("5. 退出")
    print()

def show_test_description():
    """显示测试说明"""
    print("\n📖 测试说明")
    print("=" * 50)
    print()
    print("🔧 测试前准备:")
    print("  1. 确保Redis服务正常运行")
    print("  2. 启动后端服务: python -m app.main")
    print("  3. 确保网络连接正常")
    print()
    print("📋 测试内容:")
    print("  ✅ API接口连通性测试")
    print("  ✅ 缓存优化功能测试")
    print("  ✅ 性能基准对比测试")
    print("  ✅ 高并发压力测试")
    print("  ✅ 消息处理能力测试")
    print()
    print("📊 测试输出:")
    print("  📄 HTML格式的详细报告")
    print("  📈 JSON格式的性能数据")
    print("  📝 控制台实时输出")
    print()
    print("⚠️ 注意事项:")
    print("  • 测试期间会生成一定量的测试数据")
    print("  • 性能测试会向系统发送大量消息")
    print("  • 建议在测试环境中运行")
    print("  • 测试完成后会自动恢复初始状态")

def main():
    """主函数"""
    runner = TestRunner()
    
    while True:
        show_menu()
        choice = input("请选择 (1-5): ").strip()
        
        if choice == '1':
            runner.run_all_tests()
        elif choice == '2':
            runner.run_quick_test_only()
        elif choice == '3':
            runner.run_performance_test_only()
        elif choice == '4':
            show_test_description()
        elif choice == '5':
            print("👋 再见！")
            break
        else:
            print("❌ 无效选择，请重试")
        
        if choice in ['1', '2', '3']:
            input("\n按回车键返回菜单...")

if __name__ == "__main__":
    main() 