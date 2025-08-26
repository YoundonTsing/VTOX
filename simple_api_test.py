#!/usr/bin/env python3
"""
简单的API测试，检查修复效果
"""
import requests
import json

def test_single_api_call():
    """测试单次API调用"""
    print("🔍 测试单次API调用...")
    print("=" * 50)
    
    try:
        response = requests.get(
            'http://localhost:8000/api/v1/cluster/status',
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"HTTP状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('status') == 'success':
                print("✅ API调用成功")
                
                # 详细输出数据结构
                cluster_data = data['data']
                
                print(f"\n📊 集群基本信息:")
                print(f"  集群健康度: {cluster_data.get('cluster_health')}%")
                print(f"  集群状态: {cluster_data.get('cluster_status')}")
                
                print(f"\n🎯 性能指标:")
                perf = cluster_data.get('performance_metrics', {})
                print(f"  吞吐量: {perf.get('throughput')} msg/s")
                print(f"  延迟: {perf.get('latency')}ms")
                print(f"  队列长度: {perf.get('queue_length')}")
                
                print(f"\n👥 消费者信息:")
                debug = cluster_data.get('debug_info', {})
                print(f"  总消费者: {debug.get('total_consumers')}")
                print(f"  健康消费者: {debug.get('healthy_workers')}")
                print(f"  警告消费者: {debug.get('warning_workers')}")
                
                # 检查worker详细信息
                workers = cluster_data.get('worker_nodes', [])
                print(f"\n🔧 前5个Worker详细信息:")
                for i, worker in enumerate(workers[:5]):
                    idle_minutes = worker.get('idle_ms', 0) / 60000
                    print(f"  {i+1}. {worker.get('id')}: {worker.get('status')} (闲置: {idle_minutes:.1f}分钟)")
                
                # 计算实际应该的状态
                print(f"\n🧮 状态验证计算:")
                print(f"  当前阈值: 10分钟 (600秒)")
                
                healthy_count_10min = 0
                for worker in workers:
                    idle_ms = worker.get('idle_ms', 0)
                    if idle_ms < 600000:  # 10分钟
                        healthy_count_10min += 1
                
                print(f"  按10分钟阈值计算的健康消费者: {healthy_count_10min}")
                print(f"  API返回的健康消费者: {debug.get('healthy_workers')}")
                
                if healthy_count_10min != debug.get('healthy_workers'):
                    print("  ❌ 不一致！可能是代码未生效或缓存问题")
                else:
                    print("  ✅ 一致，修复可能已生效")
                
                # 显示原始JSON（简化版）
                print(f"\n📄 API响应摘要:")
                print(f"  timestamp: {cluster_data.get('timestamp')}")
                
            else:
                print(f"❌ API返回错误: {data.get('message')}")
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            print(f"响应内容: {response.text[:200]}...")
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")

if __name__ == "__main__":
    test_single_api_call()