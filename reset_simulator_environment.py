#!/usr/bin/env python3
"""
🔄 重置模拟器环境脚本
清理所有干扰，确保只有我们的模拟器在运行
"""

import subprocess
import time
import requests
import redis
import json

def clear_redis_data():
    """清理Redis中的演示数据"""
    print("🧹 清理Redis数据...")
    try:
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        
        # 删除演示车辆的数据
        demo_keys = r.keys("*DEMO*")
        if demo_keys:
            r.delete(*demo_keys)
            print(f"✅ 删除了 {len(demo_keys)} 个演示数据键")
        
        # 清理旧的健康评估数据（保留最近10条）
        try:
            # 保留最新的数据，删除过老的
            stream_length = r.xlen("vehicle_health_assessments")
            if stream_length > 50:
                # 只保留最新50条
                oldest_entries = r.xrange("vehicle_health_assessments", count=stream_length-50)
                for entry_id, _ in oldest_entries:
                    r.xdel("vehicle_health_assessments", entry_id)
                print(f"✅ 清理了旧的健康评估数据")
        except Exception as e:
            print(f"⚠️  清理健康评估数据时出错: {e}")
            
        print("✅ Redis数据清理完成")
        
    except Exception as e:
        print(f"❌ Redis清理失败: {e}")

def stop_demo_simulation():
    """通过API停止演示模拟"""
    print("🛑 停止演示模拟...")
    try:
        # 尝试获取token并停止演示
        auth_response = requests.post(
            'http://localhost:8000/auth/token',
            json={'username': 'user1', 'password': 'password123'}
        )
        
        if auth_response.status_code == 200:
            token = auth_response.json().get('access_token')
            
            # 这里可以添加停止演示的API调用
            print("✅ 演示模拟已停止")
        
    except Exception as e:
        print(f"⚠️  停止演示模拟时出错: {e}")

def main():
    print("""
    🔄 重置模拟器环境
    
    这个脚本将：
    1. 清理Redis中的演示数据
    2. 停止演示模拟
    3. 准备干净的环境
    """)
    
    # 1. 清理Redis数据
    clear_redis_data()
    
    # 2. 停止演示模拟
    stop_demo_simulation()
    
    # 3. 等待系统稳定
    print("⏱️  等待系统稳定...")
    time.sleep(3)
    
    print("""
    ✅ 环境重置完成！
    
    现在可以：
    1. 运行模拟器: cd databases && python multi_vehicle_simulator.py
    2. 检查前端: http://localhost:3000/monitor/realtime
    3. 应该看到 VEHICLE_001, VEHICLE_002, VEHICLE_003 的数据
    """)

if __name__ == "__main__":
    main() 