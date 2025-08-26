#!/usr/bin/env python3
"""
RAG API功能测试程序
用于验证vtox项目中RAG功能是否正常工作
"""

import asyncio
import aiohttp
import json
import os
from pathlib import Path

# 添加项目路径到Python路径
project_root = Path(__file__).parent
backend_path = project_root / "backend"
import sys
sys.path.insert(0, str(backend_path))

# 导入RAG相关模块
from app.services.rag import VtoxRAGEngine, VtoxRAGConfig

async def test_rag_engine():
    """测试RAG引擎功能"""
    print("🔍 测试RAG引擎功能...")
    
    try:
        # 初始化RAG引擎
        print("🔧 初始化RAG引擎...")
        rag_config = VtoxRAGConfig()
        rag_engine = VtoxRAGEngine(rag_config)
        await rag_engine.initialize()
        print("✅ RAG引擎初始化成功")
        
        # 测试知识库查询
        print("\n🔍 测试知识库查询...")
        query_text = "轴承外圈故障特征频率"
        results = await rag_engine.query(query_text, top_k=3)
        print(f"📚 查询 '{query_text}' 的结果:")
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result['title']} (得分: {result['score']})")
            print(f"     类别: {result['category']}")
            print(f"     关键词: {', '.join(result['keywords'])}")
            print(f"     内容预览: {result['content'][:100]}...")
            print()
        
        # 测试RAG增强回复生成
        print("🤖 测试RAG增强回复生成...")
        async def mock_llm_func(prompt):
            return f"基于提供的知识库内容，我分析了您的问题: {prompt[:50]}..."
        
        enhanced_response = await rag_engine.generate_rag_response(
            "如何诊断电机轴承故障？", mock_llm_func
        )
        print(f"💬 RAG增强回复: {enhanced_response[:200]}...")
        print("✅ RAG增强回复生成功能正常")
        
        return True
        
    except Exception as e:
        print(f"❌ RAG引擎测试失败: {e}")
        return False

async def test_api_endpoints():
    """测试API端点功能"""
    print("\n🌐 测试API端点功能...")
    
    base_url = "http://localhost:8000"
    
    try:
        async with aiohttp.ClientSession() as session:
            # 测试获取可用模型
            print("📋 测试获取可用模型...")
            async with session.get(f"{base_url}/ai/models") as response:
                if response.status == 200:
                    models_data = await response.json()
                    print("✅ 获取可用模型成功")
                    print(f"   可用模型数量: {len(models_data.get('models', []))}")
                else:
                    print(f"❌ 获取可用模型失败，状态码: {response.status}")
                    return False
            
            # 测试AI聊天功能
            print("\n💬 测试AI聊天功能...")
            chat_data = {
                "message": "如何诊断电机轴承外圈故障？",
                "model_provider": "local"
            }
            
            async with session.post(f"{base_url}/ai/chat", json=chat_data) as response:
                if response.status == 200:
                    chat_response = await response.json()
                    print("✅ AI聊天功能正常")
                    print(f"   使用模型: {chat_response.get('model_used')}")
                    print(f"   处理时间: {chat_response.get('processing_time')}ms")
                    print(f"   回复预览: {chat_response.get('response')[:100]}...")
                else:
                    print(f"❌ AI聊天功能测试失败，状态码: {response.status}")
                    return False
            
            return True
            
    except Exception as e:
        print(f"❌ API端点测试失败: {e}")
        return False

async def main():
    """主函数"""
    print("🔧 vtox RAG API功能测试程序")
    print("=" * 50)
    
    # 测试RAG引擎
    rag_success = await test_rag_engine()
    
    # 测试API端点
    api_success = await test_api_endpoints()
    
    # 总结
    print("\n" + "=" * 50)
    print("📊 测试结果总结:")
    print(f"   RAG引擎功能: {'✅ 通过' if rag_success else '❌ 失败'}")
    print(f"   API端点功能: {'✅ 通过' if api_success else '❌ 失败'}")
    
    if rag_success and api_success:
        print("\n🎉 所有测试通过！RAG功能正常工作。")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查相关功能。")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)