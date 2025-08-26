#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis Stream 积压数据清理工具
用于清理 VTOX 系统中的 Redis Stream 积压数据
"""

import redis
import sys
from typing import List, Dict, Any
import argparse

class RedisStreamCleaner:
    """Redis Stream 数据清理器"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.client = None
        
        # VTOX 系统的主要 Stream
        self.main_streams = [
            "motor_raw_data",
            "fault_diagnosis_results", 
            "performance_metrics",
            "system_alerts",
            "vehicle_health_assessments"
        ]
        
        # 主要消费者组
        self.consumer_groups = {
            "motor_raw_data": [
                "turn_fault_diagnosis_group",
                "insulation_diagnosis_group",
                "bearing_diagnosis_group", 
                "eccentricity_diagnosis_group",
                "broken_bar_diagnosis_group",
                "result_aggregation_group"
            ]
        }
    
    def connect(self) -> bool:
        """连接到 Redis"""
        try:
            self.client = redis.from_url(self.redis_url, decode_responses=True)
            self.client.ping()
            print(f"✅ 成功连接到 Redis: {self.redis_url}")
            return True
        except Exception as e:
            print(f"❌ 连接 Redis 失败: {e}")
            return False
    
    def get_stream_info(self) -> Dict[str, Any]:
        """获取 Stream 信息"""
        if not self.client:
            return {}
        
        stream_info = {}
        try:
            # 获取所有匹配的 Stream
            all_streams = []
            for pattern in ["motor_*", "fault_*", "performance_*", "system_*", "vehicle_*"]:
                streams = self.client.keys(pattern)
                all_streams.extend(streams)
            
            # 去重
            all_streams = list(set(all_streams))
            
            for stream_name in all_streams:
                try:
                    info = self.client.xinfo_stream(stream_name)
                    stream_info[stream_name] = {
                        "length": info.get("length", 0),
                        "first_entry": info.get("first-entry"),
                        "last_entry": info.get("last-entry")
                    }
                except Exception as e:
                    print(f"⚠️ 无法获取 {stream_name} 信息: {e}")
            
            return stream_info
            
        except Exception as e:
            print(f"❌ 获取 Stream 信息失败: {e}")
            return {}
    
    def display_stream_status(self):
        """显示 Stream 状态"""
        print("\n" + "="*80)
        print("📊 Redis Stream 状态概览")
        print("="*80)
        
        stream_info = self.get_stream_info()
        
        if not stream_info:
            print("❌ 未找到任何 Stream 或无法获取信息")
            return
        
        total_messages = 0
        for stream_name, info in stream_info.items():
            length = info["length"]
            total_messages += length
            
            status = "🔴 积压严重" if length > 10000 else "🟡 有积压" if length > 1000 else "🟢 正常"
            print(f"{status} {stream_name}: {length:,} 条消息")
        
        print(f"\n📈 总积压消息数: {total_messages:,} 条")
        
        if total_messages > 50000:
            print("⚠️  警告: 积压消息过多，建议立即清理")
        elif total_messages > 10000:
            print("💡 建议: 适量积压，可考虑清理")
        else:
            print("✅ 积压量正常")
    
    def clear_all_streams(self, confirm: bool = False):
        """清空所有 Stream"""
        if not self.client:
            print("❌ 未连接到 Redis")
            return False
        
        if not confirm:
            print("⚠️  此操作将删除所有 Stream 数据，无法恢复！")
            response = input("确认删除所有数据？输入 'yes' 确认: ")
            if response.lower() != 'yes':
                print("❌ 操作已取消")
                return False
        
        try:
            # 获取所有 Stream
            stream_info = self.get_stream_info()
            deleted_count = 0
            
            for stream_name in stream_info.keys():
                try:
                    self.client.delete(stream_name)
                    deleted_count += 1
                    print(f"✅ 已删除: {stream_name}")
                except Exception as e:
                    print(f"❌ 删除失败 {stream_name}: {e}")
            
            print(f"\n🎉 清理完成！删除了 {deleted_count} 个 Stream")
            return True
            
        except Exception as e:
            print(f"❌ 清理过程出错: {e}")
            return False
    
    def clear_specific_stream(self, stream_name: str, keep_count: int = 0):
        """清理特定 Stream"""
        if not self.client:
            print("❌ 未连接到 Redis")
            return False
        
        try:
            # 检查 Stream 是否存在
            if not self.client.exists(stream_name):
                print(f"⚠️  Stream {stream_name} 不存在")
                return False
            
            if keep_count == 0:
                # 完全删除
                self.client.delete(stream_name)
                print(f"✅ 已完全删除 Stream: {stream_name}")
            else:
                # 截断保留最新 N 条
                self.client.xtrim(stream_name, maxlen=keep_count)
                print(f"✅ 已截断 Stream {stream_name}，保留最新 {keep_count} 条消息")
            
            return True
            
        except Exception as e:
            print(f"❌ 清理 {stream_name} 失败: {e}")
            return False
    
    def reset_consumer_groups(self):
        """重置消费者组"""
        if not self.client:
            print("❌ 未连接到 Redis")
            return False
        
        try:
            reset_count = 0
            
            for stream_name, groups in self.consumer_groups.items():
                if not self.client.exists(stream_name):
                    continue
                
                for group_name in groups:
                    try:
                        # 删除消费者组
                        self.client.xgroup_destroy(stream_name, group_name)
                        print(f"✅ 已重置消费者组: {stream_name} -> {group_name}")
                        reset_count += 1
                    except Exception as e:
                        # 消费者组可能不存在，这是正常的
                        if "NOGROUP" not in str(e):
                            print(f"⚠️  重置消费者组失败 {group_name}: {e}")
            
            print(f"\n🎉 重置完成！处理了 {reset_count} 个消费者组")
            return True
            
        except Exception as e:
            print(f"❌ 重置消费者组过程出错: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description='Redis Stream 积压数据清理工具')
    parser.add_argument('--redis-url', default='redis://localhost:6379', 
                       help='Redis 连接地址')
    parser.add_argument('--action', choices=['status', 'clear-all', 'clear-stream', 'reset-groups'], 
                       default='status', help='执行的操作')
    parser.add_argument('--stream-name', help='要清理的特定 Stream 名称')
    parser.add_argument('--keep-count', type=int, default=0, 
                       help='保留的消息数量（0表示完全删除）')
    parser.add_argument('--force', action='store_true', 
                       help='强制执行，跳过确认')
    
    args = parser.parse_args()
    
    # 创建清理器
    cleaner = RedisStreamCleaner(args.redis_url)
    
    if not cleaner.connect():
        sys.exit(1)
    
    # 执行操作
    if args.action == 'status':
        cleaner.display_stream_status()
    
    elif args.action == 'clear-all':
        cleaner.clear_all_streams(confirm=args.force)
    
    elif args.action == 'clear-stream':
        if not args.stream_name:
            print("❌ 请指定 --stream-name")
            sys.exit(1)
        cleaner.clear_specific_stream(args.stream_name, args.keep_count)
    
    elif args.action == 'reset-groups':
        cleaner.reset_consumer_groups()


if __name__ == "__main__":
    print("🧹 Redis Stream 积压数据清理工具")
    print("=" * 50)
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ 用户中断操作")
    except Exception as e:
        print(f"\n❌ 程序异常: {e}")
