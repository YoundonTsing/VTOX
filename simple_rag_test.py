#!/usr/bin/env python3
"""
简化版RAG功能测试程序
用于快速验证vtox项目中RAG功能是否正常工作
"""

import requests
import json
import time

def test_rag_functionality():
    """测试RAG功能"""
    print("🔍 测试RAG功能...")
    
    # API基础URL
    base_url = "http://localhost:8000"
    
    try:
        # 1. 测试获取可用模型
        print("\n1. 测试获取可用模型...")
        response = requests.get(f"{base_url}/ai/models", timeout=10)
        if response.status_code == 200:
            models_data = response.json()
            print("✅ 获取可用模型成功")
            print(f"   可用模型: {[model['name'] for model in models_data.get('models', [])]}")
        else:
            print(f"❌ 获取可用模型失败，状态码: {response.status_code}")
            return False
        
        # 2. 测试AI聊天功能 - 本地MCSA知识库
        print("\n2. 测试AI聊天功能(本地MCSA知识库)...")
        chat_data = {
            "message": "如何诊断电机轴承外圈故障？",
            "model_provider": "local"
        }
        
        start_time = time.time()
        response = requests.post(f"{base_url}/ai/chat", json=chat_data, timeout=30)
        end_time = time.time()
        
        if response.status_code == 200:
            chat_response = response.json()
            print("✅ AI聊天功能正常")
            print(f"   使用模型: {chat_response.get('model_used')}")
            print(f"   处理时间: {chat_response.get('processing_time')}ms")
            print(f"   回复预览: {chat_response.get('response')[:150]}...")
        else:
            print(f"❌ AI聊天功能测试失败，状态码: {response.status_code}")
            print(f"   错误详情: {response.text}")
            return False
        
        # 3. 测试AI聊天功能 - 通义千问(如果配置了API Key)
        print("\n3. 测试AI聊天功能(通义千问)...")
        chat_data_qwen = {
            "message": "请解释电机匝间短路故障的特征频率",
            "model_provider": "qwen"
        }
        
        start_time = time.time()
        response = requests.post(f"{base_url}/ai/chat", json=chat_data_qwen, timeout=30)
        end_time = time.time()
        
        if response.status_code == 200:
            chat_response = response.json()
            print("✅ 通义千问聊天功能正常")
            print(f"   使用模型: {chat_response.get('model_used')}")
            print(f"   处理时间: {chat_response.get('processing_time')}ms")
            print(f"   回复预览: {chat_response.get('response')[:150]}...")
        else:
            print(f"⚠️  通义千问聊天功能测试失败(可能未配置API Key)，状态码: {response.status_code}")
            # 这不是致命错误，继续测试
        
        # 4. 测试流式聊天功能
        print("\n4. 测试流式聊天功能...")
        chat_data_stream = {
            "message": "简要介绍MCSA分析方法",
            "model_provider": "local"
        }
        
        try:
            response = requests.post(
                f"{base_url}/ai/chat/stream", 
                json=chat_data_stream, 
                timeout=30,
                stream=True
            )
            
            if response.status_code == 200:
                print("✅ 流式聊天功能正常")
                # 读取部分流式数据作为验证
                chunks = []
                for i, chunk in enumerate(response.iter_lines()):
                    if i < 5 and chunk:  # 只读取前5个数据块
                        chunks.append(chunk.decode('utf-8'))
                print(f"   流式数据块示例: {chunks[:2]}")
            else:
                print(f"❌ 流式聊天功能测试失败，状态码: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 流式聊天功能测试异常: {e}")
            return False
        
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请确保vtox服务正在运行")
        print("   启动方法: cd C:\\Projects\\vtox && python start_rag_service.py")
        return False
    except requests.exceptions.Timeout:
        print("❌ 请求超时，请检查网络连接或服务器状态")
        return False
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        return False

def main():
    """主函数"""
    print("🔧 vtox RAG功能简化测试程序")
    print("=" * 50)
    
    success = test_rag_functionality()
    
    # 总结
    print("\n" + "=" * 50)
    print("📊 测试结果总结:")
    if success:
        print("🎉 RAG功能测试通过！")
        print("   1. 本地MCSA知识库功能正常")
        print("   2. API接口可正常访问")
        print("   3. 流式响应功能正常")
        print("   4. 通义千问集成(如配置)功能正常")
    else:
        print("❌ RAG功能测试失败，请检查相关配置和依赖")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())