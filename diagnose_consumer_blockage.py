#!/usr/bin/env python3
"""
消费者阻塞诊断脚本
专门分析为什么消费者不处理数据
"""
import asyncio
import redis.asyncio as redis
import time
from datetime import datetime

async def diagnose_consumer_blockage():
    """诊断消费者阻塞问题"""
    print("🔍 诊断消费者阻塞问题...")
    print("=" * 70)
    
    try:
        redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
        await redis_client.ping()
        print("✅ Redis连接成功")
        
        # 重点检查的Stream和消费者组
        stream_configs = [
            {
                "stream": "motor_raw_data",
                "expected_groups": ["turn_fault_diagnosis", "insulation_diagnosis", "bearing_diagnosis", 
                                  "eccentricity_diagnosis", "broken_bar_diagnosis"],
                "description": "原始电机数据 → 故障诊断"
            },
            {
                "stream": "fault_diagnosis_results", 
                "expected_groups": ["result_aggregation", "frontend_bridge"],
                "description": "故障诊断结果 → 结果聚合"
            },
            {
                "stream": "vehicle_health_assessments",
                "expected_groups": ["frontend_bridge"],  
                "description": "健康评估结果 → 前端桥接"
            }
        ]
        
        current_time = int(time.time() * 1000)
        
        for config in stream_configs:
            stream_name = config["stream"]
            expected_groups = config["expected_groups"]
            description = config["description"]
            
            print(f"\n🔧 检查 {stream_name}")
            print(f"   功能: {description}")
            print("-" * 70)
            
            try:
                # 检查Stream基本信息
                stream_info = await redis_client.xinfo_stream(stream_name)
                length = stream_info.get('length', 0)
                print(f"   📊 Stream状态: {length}条消息")
                
                # 检查最新消息时间
                if length > 0:
                    latest_messages = await redis_client.xrevrange(stream_name, count=1)
                    if latest_messages:
                        latest_id = latest_messages[0][0]
                        timestamp_ms = int(latest_id.split('-')[0])
                        age_minutes = (current_time - timestamp_ms) / 60000
                        print(f"   ⏰ 最新消息: {age_minutes:.1f}分钟前")
                
                # 检查消费者组
                try:
                    groups = await redis_client.xinfo_groups(stream_name)
                    actual_groups = [g['name'] for g in groups]
                    print(f"   👥 消费者组: {len(groups)}个")
                    
                    # 检查预期的组是否存在
                    missing_groups = set(expected_groups) - set(actual_groups)
                    if missing_groups:
                        print(f"   ❌ 缺失的消费者组: {missing_groups}")
                    
                    # 详细检查每个组
                    for group in groups:
                        group_name = group['name']
                        pending = group['pending']
                        
                        print(f"\n      🔍 组 '{group_name}':")
                        print(f"         待处理消息: {pending}条")
                        
                        # 检查组内消费者
                        try:
                            consumers = await redis_client.xinfo_consumers(stream_name, group_name)
                            print(f"         消费者数量: {len(consumers)}个")
                            
                            if len(consumers) == 0:
                                print("         ⚠️ 警告: 没有活跃的消费者!")
                                
                            for consumer in consumers:
                                consumer_name = consumer['name']
                                idle_ms = consumer['idle']
                                pending_count = consumer['pending']
                                idle_minutes = idle_ms / 60000
                                
                                status_icon = "❌" if idle_minutes > 15 else "⚠️" if idle_minutes > 5 else "✅"
                                print(f"         {status_icon} {consumer_name}: "
                                      f"闲置{idle_minutes:.1f}分钟, 待处理{pending_count}条")
                                
                                # 诊断具体问题
                                if idle_minutes > 15:
                                    print(f"            💥 严重: 消费者可能已崩溃或卡死")
                                elif idle_minutes > 5:
                                    print(f"            ⚠️ 警告: 消费者处理缓慢")
                                elif pending_count > 100:
                                    print(f"            📈 积压: 处理速度跟不上生产速度")
                                    
                        except Exception as e:
                            print(f"         ❌ 获取消费者信息失败: {e}")
                            
                except Exception as e:
                    print(f"   ❌ 获取消费者组失败: {e}")
                    if "no such key" in str(e).lower():
                        print("   💡 可能原因: Stream存在但没有消费者组")
                        
            except Exception as e:
                print(f"   ❌ 检查Stream失败: {e}")
        
        # 数据流阻塞点分析
        print(f"\n🎯 数据流阻塞点分析")
        print("=" * 70)
        
        # 检查motor_raw_data的处理情况
        try:
            motor_info = await redis_client.xinfo_stream("motor_raw_data")
            motor_length = motor_info.get('length', 0)
            
            motor_groups = await redis_client.xinfo_groups("motor_raw_data")
            total_motor_pending = sum(g['pending'] for g in motor_groups)
            
            print(f"📊 motor_raw_data分析:")
            print(f"   总消息: {motor_length}条")
            print(f"   总待处理: {total_motor_pending}条")
            print(f"   处理率: {((motor_length - total_motor_pending) / motor_length * 100):.1f}%" if motor_length > 0 else "   处理率: 0%")
            
            if total_motor_pending > 1000:
                print("   🚨 严重积压: 故障诊断消费者处理能力不足")
            elif total_motor_pending > 100:
                print("   ⚠️ 轻微积压: 需要监控处理速度")
            else:
                print("   ✅ 处理正常: 积压在可接受范围内")
                
        except Exception as e:
            print(f"   ❌ 分析motor_raw_data失败: {e}")
        
        # 检查下游Stream的情况
        try:
            fault_info = await redis_client.xinfo_stream("fault_diagnosis_results")
            fault_length = fault_info.get('length', 0)
            
            health_info = await redis_client.xinfo_stream("vehicle_health_assessments")  
            health_length = health_info.get('length', 0)
            
            print(f"\n📊 下游Stream分析:")
            print(f"   fault_diagnosis_results: {fault_length}条")
            print(f"   vehicle_health_assessments: {health_length}条")
            
            if fault_length == 0 and health_length == 0:
                print("   🚨 关键问题: 下游Stream完全为空!")
                print("   💡 说明: 故障诊断消费者根本没有产生输出")
            
        except Exception as e:
            print(f"   ❌ 检查下游Stream失败: {e}")
            
        await redis_client.close()
        
    except Exception as e:
        print(f"❌ 诊断失败: {e}")

async def suggest_solutions():
    """建议解决方案"""
    print(f"\n🛠️ 建议的解决方案")
    print("=" * 70)
    
    print("1. 检查微服务集群状态:")
    print("   - 确认所有故障诊断服务是否在运行")
    print("   - 检查集群启动脚本是否正确执行")
    print("   - 验证Redis Stream消费者注册状态")
    
    print("\n2. 重启数据处理服务:")
    print("   - 重启微服务集群")
    print("   - 重新启动故障诊断消费者")
    print("   - 检查服务依赖关系")
    
    print("\n3. 检查消费者配置:")
    print("   - 验证消费者组名称配置")
    print("   - 检查Redis连接配置")
    print("   - 确认消费者读取模式设置")
    
    print("\n4. 临时解决方案:")
    print("   - 手动触发消费者处理")
    print("   - 清理积压的消息")
    print("   - 重置消费者组状态")

async def main():
    await diagnose_consumer_blockage()
    await suggest_solutions()

if __name__ == "__main__":
    asyncio.run(main())