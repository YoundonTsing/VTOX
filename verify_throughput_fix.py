#!/usr/bin/env python3
"""
验证吞吐量计算修复效果
测试方法3的改进逻辑
"""
import requests
import time
import asyncio

def test_api_multiple_times():
    """连续测试API多次，观察吞吐量变化"""
    print("🧪 连续测试API吞吐量计算...")
    print("=" * 60)
    
    results = []
    
    for i in range(5):
        try:
            response = requests.get(
                'http://localhost:8000/api/v1/cluster/status',
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    perf = data['data'].get('performance_metrics', {})
                    debug = data['data'].get('debug_info', {})
                    
                    throughput = perf.get('throughput', 0)
                    latency = perf.get('latency', 0)
                    queue_length = perf.get('queue_length', 0)
                    
                    total_consumers = debug.get('total_consumers', 0)
                    healthy_workers = debug.get('healthy_workers', 0)
                    warning_workers = debug.get('warning_workers', 0)
                    
                    result = {
                        'test_num': i + 1,
                        'throughput': throughput,
                        'latency': latency,
                        'queue_length': queue_length,
                        'total_consumers': total_consumers,
                        'healthy_workers': healthy_workers,
                        'warning_workers': warning_workers,
                        'timestamp': time.time()
                    }
                    
                    results.append(result)
                    
                    print(f"📊 测试 {i+1}:")
                    print(f"  吞吐量: {throughput} msg/s")
                    print(f"  延迟: {latency}ms")
                    print(f"  队列长度: {queue_length}")
                    print(f"  消费者: {total_consumers} (健康: {healthy_workers}, 警告: {warning_workers})")
                    print()
                    
                else:
                    print(f"❌ 测试 {i+1}: API返回错误 - {data.get('message')}")
            else:
                print(f"❌ 测试 {i+1}: HTTP错误 {response.status_code}")
                
        except Exception as e:
            print(f"❌ 测试 {i+1}: 请求失败 - {e}")
        
        if i < 4:  # 不是最后一次测试
            time.sleep(3)  # 等待3秒
    
    return results

def analyze_results(results):
    """分析测试结果"""
    if not results:
        print("❌ 没有有效的测试结果")
        return
    
    print("\n📈 结果分析:")
    print("=" * 60)
    
    throughputs = [r['throughput'] for r in results]
    
    # 基础统计
    avg_throughput = sum(throughputs) / len(throughputs)
    min_throughput = min(throughputs)
    max_throughput = max(throughputs)
    
    print(f"📊 吞吐量统计:")
    print(f"  平均值: {avg_throughput:.1f} msg/s")
    print(f"  最小值: {min_throughput:.1f} msg/s")
    print(f"  最大值: {max_throughput:.1f} msg/s")
    print(f"  变化范围: {max_throughput - min_throughput:.1f} msg/s")
    
    # 期望值分析
    latest_result = results[-1]
    total_consumers = latest_result['total_consumers']
    healthy_workers = latest_result['healthy_workers']
    queue_length = latest_result['queue_length']
    
    print(f"\n🎯 期望值分析 (基于修复后的方法3):")
    print(f"  总消费者: {total_consumers}")
    print(f"  健康消费者: {healthy_workers}")
    print(f"  队列长度: {queue_length}")
    
    # 模拟方法3计算
    if total_consumers > 0:
        # 假设所有消费者都是5分钟内活跃（修复后的逻辑）
        active_consumers = healthy_workers
        stream_activity_factor = min(2.0, queue_length / 100.0)
        
        base_rate = 5.0 + (stream_activity_factor * 3.0)
        queue_factor = min(2.0, queue_length / 200.0)
        adjusted_rate = base_rate * (1.0 + queue_factor)
        expected_throughput = min(active_consumers * adjusted_rate, 100.0)
        
        print(f"  活跃消费者: {active_consumers} (假设5分钟内活跃)")
        print(f"  流活跃因子: {stream_activity_factor:.2f}")
        print(f"  基础速率: {base_rate:.1f} msg/s")
        print(f"  队列因子: {queue_factor:.2f}")
        print(f"  调整后速率: {adjusted_rate:.1f} msg/s")
        print(f"  期望吞吐量: {expected_throughput:.1f} msg/s")
        
        # 比较实际值和期望值
        actual_throughput = latest_result['throughput']
        difference = abs(actual_throughput - expected_throughput)
        
        print(f"\n🔍 对比分析:")
        print(f"  实际吞吐量: {actual_throughput:.1f} msg/s")
        print(f"  期望吞吐量: {expected_throughput:.1f} msg/s")
        print(f"  差异: {difference:.1f} msg/s")
        
        if difference <= 2.0:
            print("  ✅ 修复成功！实际值与期望值接近")
        else:
            print("  ⚠️ 仍有偏差，可能需要进一步调整")
    
    # 问题诊断
    print(f"\n🩺 问题诊断:")
    
    if avg_throughput < 5.0:
        print("  ⚠️ 吞吐量过低，可能原因:")
        print("    - 消费者闲置时间超过5分钟，被判定为不活跃")
        print("    - 方法1和方法2数据不足，降级到方法3固定估算")
        print("    - 需要检查后端日志确认使用的计算方法")
    
    if max_throughput - min_throughput > 5.0:
        print("  ⚠️ 吞吐量波动较大，可能原因:")
        print("    - 不同测试使用了不同的计算方法")
        print("    - performance_metrics数据的新鲜度在变化")
    
    if avg_throughput > 50.0:
        print("  ✅ 吞吐量恢复正常，修复可能成功")

def check_backend_logs():
    """提示检查后端日志"""
    print("\n📋 后端日志检查指南:")
    print("=" * 60)
    print("请在后端控制台查看以下日志信息:")
    print()
    print("🔍 方法3消费者活跃度分析:")
    print("  - 总消费者: X")
    print("  - 健康消费者: X")
    print("  - 活跃消费者(5分钟内): X  <-- 这个应该>0")
    print("  - 流活跃因子: X.XX")
    print()
    print("📊 [方法3] 动态估算 或 固定估算:")
    print("  应该看到消费者数量 × 调整后速率 = 最终吞吐量")
    print()
    print("💡 如果看到'固定估算'，说明消费者仍被判定为不活跃")
    print("   需要进一步调整活跃度判断逻辑")

def main():
    print("🔧 吞吐量计算修复验证")
    print("=" * 60)
    print("测试目标: 验证方法3修复后吞吐量不再是2 msg/s")
    print()
    
    # 1. 连续测试API
    results = test_api_multiple_times()
    
    # 2. 分析结果
    analyze_results(results)
    
    # 3. 检查指南
    check_backend_logs()
    
    print("\n🎯 总结:")
    print("如果修复成功，吞吐量应该显著提高(>10 msg/s)")
    print("如果仍显示低值，请检查后端日志定位具体问题")

if __name__ == "__main__":
    main()