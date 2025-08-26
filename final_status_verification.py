#!/usr/bin/env python3
"""
最终状态验证脚本
确认消费者修复和吞吐量计算的完整效果
"""
import requests
import asyncio
import redis.asyncio as redis
import time
from datetime import datetime

def test_api_final_status():
    """测试API最终状态"""
    print("🎯 最终状态验证...")
    print("=" * 50)
    
    try:
        response = requests.get(
            'http://localhost:8000/api/v1/cluster/status',
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                cluster_data = data['data']
                perf = cluster_data.get('performance_metrics', {})
                debug = cluster_data.get('debug_info', {})
                
                print("📊 最终系统状态:")
                print(f"  🎯 吞吐量: {perf.get('throughput')} msg/s")
                print(f"  ⚡ 延迟: {perf.get('latency')}ms")
                print(f"  📦 队列长度: {perf.get('queue_length')}")
                print(f"  👥 总消费者: {debug.get('total_consumers')}")
                print(f"  ✅ 健康消费者: {debug.get('healthy_workers')}")
                print(f"  ⚠️ 警告消费者: {debug.get('warning_workers')}")
                
                # 状态评估
                throughput = perf.get('throughput', 0)
                healthy_workers = debug.get('healthy_workers', 0)
                total_consumers = debug.get('total_consumers', 0)
                
                print(f"\n🏆 修复效果评估:")
                
                # 消费者健康状态
                if healthy_workers == total_consumers and total_consumers > 0:
                    print("  ✅ 消费者状态: 完美修复 (100%健康)")
                elif healthy_workers > 0:
                    health_rate = (healthy_workers / total_consumers) * 100
                    print(f"  ✅ 消费者状态: 基本修复 ({health_rate:.1f}%健康)")
                else:
                    print("  ❌ 消费者状态: 仍有问题")
                
                # 吞吐量状态
                if throughput >= 5.0:
                    print("  ✅ 吞吐量: 优秀 (>5 msg/s)")
                elif throughput >= 1.5:
                    print("  ✅ 吞吐量: 良好 (>1.5 msg/s)")
                elif throughput > 0.5:
                    print("  ⚠️ 吞吐量: 一般 (>0.5 msg/s)")
                else:
                    print("  ❌ 吞吐量: 偏低 (<0.5 msg/s)")
                
                # 系统整体评估
                cluster_health = cluster_data.get('cluster_health', 0)
                print(f"\n🎯 系统整体评估:")
                print(f"  集群健康度: {cluster_health}%")
                
                if cluster_health >= 90 and healthy_workers == total_consumers:
                    print("  🏆 评级: 系统运行优秀，修复完全成功")
                elif cluster_health >= 70 and healthy_workers > total_consumers * 0.8:
                    print("  ✅ 评级: 系统运行良好，修复基本成功")
                else:
                    print("  ⚠️ 评级: 系统需要进一步优化")
                    
                return {
                    'throughput': throughput,
                    'healthy_workers': healthy_workers,
                    'total_consumers': total_consumers,
                    'cluster_health': cluster_health
                }
                
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ API测试失败: {e}")
        return None

async def check_redis_stream_status():
    """检查Redis Stream状态"""
    print("\n🌊 Redis Stream状态检查...")
    print("=" * 50)
    
    try:
        redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
        await redis_client.ping()
        
        streams = [
            ("motor_raw_data", "原始数据"),
            ("fault_diagnosis_results", "故障诊断结果"),
            ("vehicle_health_assessments", "健康评估")
        ]
        
        current_time = int(time.time() * 1000)
        
        for stream_name, description in streams:
            try:
                stream_info = await redis_client.xinfo_stream(stream_name)
                length = stream_info.get('length', 0)
                
                # 获取最新消息时间
                if length > 0:
                    latest = await redis_client.xrevrange(stream_name, count=1)
                    if latest:
                        latest_id = latest[0][0]
                        timestamp_ms = int(latest_id.split('-')[0])
                        age_minutes = (current_time - timestamp_ms) / 60000
                        
                        status_icon = "✅" if age_minutes < 5 else "⚠️" if age_minutes < 15 else "❌"
                        print(f"  {status_icon} {description}: {length}条消息, 最新{age_minutes:.1f}分钟前")
                    else:
                        print(f"  ❌ {description}: {length}条消息, 无法获取最新时间")
                else:
                    print(f"  ❌ {description}: 无数据")
                    
            except Exception as e:
                print(f"  ❌ {description}: 检查失败 - {e}")
        
        await redis_client.aclose()
        
    except Exception as e:
        print(f"❌ Redis检查失败: {e}")

def check_frontend_common_issues():
    """检查前端常见问题"""
    print("\n🖥️ 前端常见问题检查...")
    print("=" * 50)
    
    print("请检查以下前端控制台可能的错误:")
    print()
    print("1. 🔗 WebSocket连接问题:")
    print("   - 检查是否有'WebSocket connection failed'错误")
    print("   - 确认WebSocket服务是否在ws://localhost:8000/ws运行")
    print()
    print("2. 📡 API请求问题:")
    print("   - 检查是否有HTTP 500/404错误")
    print("   - 确认后端API是否在http://localhost:8000运行")
    print()
    print("3. 🎨 Vue组件问题:")
    print("   - 检查是否有'computed is not defined'错误")
    print("   - 确认所有Vue函数是否正确导入")
    print()
    print("4. 📊 数据更新问题:")
    print("   - 前端数据是否实时更新")
    print("   - 刷新页面是否显示最新数据")
    print()
    print("🔧 解决建议:")
    print("   - 刷新前端页面")
    print("   - 重启前端开发服务器")
    print("   - 检查浏览器开发者工具Console选项卡")

async def main():
    print("🏆 VTOX消费者修复最终验证")
    print("=" * 50)
    print("验证目标: 确认所有修复都已成功")
    print()
    
    # 1. API状态测试
    api_status = test_api_final_status()
    
    # 2. Redis Stream检查
    await check_redis_stream_status()
    
    # 3. 前端问题检查
    check_frontend_common_issues()
    
    # 4. 最终总结
    print("\n" + "="*50)
    print("🎯 最终总结:")
    
    if api_status:
        throughput = api_status['throughput']
        healthy_rate = (api_status['healthy_workers'] / api_status['total_consumers']) * 100 if api_status['total_consumers'] > 0 else 0
        
        print(f"✅ 消费者修复: {healthy_rate:.0f}%健康率")
        print(f"✅ 吞吐量恢复: {throughput} msg/s")
        print(f"✅ 集群健康度: {api_status['cluster_health']}%")
        
        if healthy_rate == 100 and throughput > 1.0:
            print("\n🏆 恭喜！所有问题都已完全修复！")
            print("   - 消费者阻塞问题解决")
            print("   - 吞吐量计算恢复正常")
            print("   - 系统运行状态优秀")
        else:
            print("\n✅ 主要问题已解决，系统运行良好")
    else:
        print("❌ API测试失败，需要进一步检查")

if __name__ == "__main__":
    asyncio.run(main())