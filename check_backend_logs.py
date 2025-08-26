#!/usr/bin/env python3
"""
触发API调用并提示查看后端日志
"""
import requests
import time

def trigger_api_call():
    """触发API调用以生成日志"""
    print("🔍 触发集群状态API调用...")
    print("📋 请注意观察后端终端中的以下日志信息:")
    print()
    print("=" * 60)
    print("后端日志应该显示类似以下内容:")
    print("=" * 60)
    print("📊 [方法1] performance_metrics数据检查:")
    print("  - 最新数据时间: X.X分钟前")
    print("  - 数据条数: X")
    print("  - 平均延迟: X.XXXms")
    print("  - 基础吞吐量: X msg/min")
    print("  - 新鲜度因子: 0.XX")
    print("  - 最终吞吐量: XX.X msg/min")
    print()
    print("🔍 fault_diagnosis_results 最新5条消息:")
    print("    1. ID: XXXXXXXXX-X, 时间: X.X秒前")
    print("    2. ID: XXXXXXXXX-X, 时间: X.X秒前")
    print("    ...")
    print()
    print("📊 vehicle_health_assessments: 最近10分钟 X 条消息")
    print("📊 [方法2] 基于Stream活跃度计算: X条/10分钟 = X.X msg/min")
    print()
    print("📊 [API DEBUG] 最终统计数据:")
    print("  - 消费者数量: 13")
    print("  - 健康worker: 13, 警告worker: 0") 
    print("  - 吞吐量: XX.X msg/s (数据来源: Stream活跃度 或 估算)")
    print("  - 平均延迟: X.Xms")
    print("=" * 60)
    print()
    
    try:
        response = requests.get(
            'http://localhost:8000/api/v1/cluster/status',
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            perf = data['data'].get('performance_metrics', {})
            print(f"✅ API调用成功 - 返回吞吐量: {perf.get('throughput', 'N/A')} msg/s")
        else:
            print(f"❌ API调用失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")
    
    print()
    print("🔍 请查看上方后端终端的详细日志输出！")
    print("📝 日志会告诉您系统使用了哪种计算方法:")
    print("   - 方法1: performance_metrics流 + 新鲜度调整")
    print("   - 方法2: Stream活跃度计算")  
    print("   - 方法3: 动态估算或固定估算")

if __name__ == "__main__":
    print("📋 后端日志查看助手")
    print("=" * 30)
    print()
    trigger_api_call()