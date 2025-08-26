#!/usr/bin/env python3
"""
初始化Redis Stream系统的脚本
"""

import requests
import json

def init_stream_system():
    print('🔧 初始化Redis Stream系统')
    
    # 尝试不同的用户凭据
    credentials = [
        ('admin', 'admin'),
        ('user1', 'password123'),
        ('test', 'test'),
        ('admin', 'password')
    ]
    
    token = None
    
    # 尝试获取认证token
    for username, password in credentials:
        try:
            response = requests.post(
                'http://localhost:8000/auth/token',
                json={'username': username, 'password': password}
            )
            print(f'🔑 尝试 {username}:{password} -> {response.status_code}')
            
            if response.status_code == 200:
                token = response.json().get('access_token')
                print(f'✅ 认证成功! 用户: {username}')
                break
            else:
                error = response.json().get('detail', 'Unknown error')
                print(f'   错误: {error}')
        except Exception as e:
            print(f'   异常: {e}')
    
    if not token:
        print('❌ 无法获取有效的认证token')
        return False
    
    # 初始化Redis Stream
    try:
        init_response = requests.post(
            'http://localhost:8000/api/v1/diagnosis-stream/initialize',
            json={'redis_url': 'redis://localhost:6379'},
            headers={'Authorization': f'Bearer {token}'}
        )
        
        print(f'🔧 初始化状态: {init_response.status_code}')
        
        if init_response.status_code == 200:
            print('✅ Redis Stream初始化成功')
            result = init_response.json()
            print(f'响应: {result}')
            
            # 启动Redis Stream系统
            start_response = requests.post(
                'http://localhost:8000/api/v1/diagnosis-stream/start',
                params={
                    'consumers_per_fault': 2, 
                    'enable_aggregation': True, 
                    'enable_monitoring': True
                },
                headers={'Authorization': f'Bearer {token}'}
            )
            
            print(f'🚀 启动状态: {start_response.status_code}')
            
            if start_response.status_code == 200:
                print('✅ Redis Stream系统启动成功')
                start_result = start_response.json()
                print(f'响应: {start_result}')
                return True
            else:
                print(f'❌ 启动失败: {start_response.text}')
                return False
        else:
            print(f'❌ 初始化失败: {init_response.text}')
            return False
            
    except Exception as e:
        print(f'❌ 初始化过程异常: {e}')
        return False

if __name__ == "__main__":
    success = init_stream_system()
    if success:
        print('\n🎉 Redis Stream系统已成功初始化并启动!')
        print('现在可以运行模拟器了...')
    else:
        print('\n❌ 初始化失败，请检查后端服务和用户凭据') 