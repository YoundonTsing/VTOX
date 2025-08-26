from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
import logging
import aiohttp
import asyncio
import json
import os
from typing import List, Dict, Any, Optional
import random

# 导入RAG服务
from ..services.rag import VtoxRAGEngine, VtoxRAGConfig

router = APIRouter(
    prefix="/ai",
    tags=["ai_chat"]
)

logger = logging.getLogger(__name__)

# 初始化RAG引擎
rag_engine = None

async def get_rag_engine():
    """获取RAG引擎实例"""
    global rag_engine
    if rag_engine is None:
        # 使用独立环境配置
        rag_config = VtoxRAGConfig(isolated_rag_env=True)
        rag_engine = VtoxRAGEngine(rag_config)
        await rag_engine.initialize()
    return rag_engine

# AI 聊天请求模型
class ChatMessage(BaseModel):
    role: str  # "user" 或 "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[ChatMessage]] = []
    model_provider: Optional[str] = "huggingface"  # "huggingface", "ollama", "openai"

class ChatResponse(BaseModel):
    response: str
    model_used: str
    processing_time: float

# 配置不同的 AI 模型提供商
AI_PROVIDERS = {
    "qwen": {
        "url": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
        "headers": {
            "Authorization": f"Bearer {os.getenv('QWEN_API_KEY', '')}",
            "Content-Type": "application/json"
        }
    },
    "huggingface": {
        "url": "https://api-inference.huggingface.co/models/microsoft/DialoGPT-medium",
        "headers": {
            "Authorization": f"Bearer {os.getenv('HUGGINGFACE_API_KEY', '')}",
            "Content-Type": "application/json"
        }
    },
    "openai_compatible": {
        "url": "https://api.openai.com/v1/chat/completions",
        "headers": {
            "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY', '')}",
            "Content-Type": "application/json"
        }
    }
}

# MCSA 专业知识库
MCSA_KNOWLEDGE = {
    "轴承故障": {
        "outer_race": "外圈故障特征频率: BPFO = (N/2) * (1 - d/D * cos(φ)) * fs",
        "inner_race": "内圈故障特征频率: BPFI = (N/2) * (1 + d/D * cos(φ)) * fs", 
        "ball": "滚动体故障特征频率: BSF = (D/2d) * (1 - (d/D * cos(φ))²) * fs",
        "cage": "保持架故障特征频率: FTF = (1/2) * (1 - d/D * cos(φ)) * fs"
    },
    "偏心故障": {
        "static": "静偏心: 在电源频率处出现边频带",
        "dynamic": "动偏心: 在转子频率处出现调制"
    },
    "断条故障": {
        "frequency": "断条故障频率: fb = f * (1 ± 2*s), s为转差率"
    },
    "匝间短路": {
        "frequency": "匝间短路导致负序电流增大，出现特征频率分量"
    }
}

def get_mcsa_response(user_message: str) -> str:
    """基于 MCSA 知识库生成回复"""
    user_message_lower = user_message.lower()
    
    # 关键词匹配
    if any(keyword in user_message_lower for keyword in ["轴承", "bearing"]):
        if "外圈" in user_message_lower:
            return f"根据MCSA分析，轴承外圈故障的特征频率为：{MCSA_KNOWLEDGE['轴承故障']['outer_race']}。建议检查频谱中是否出现BPFO及其谐波成分。如发现异常，应立即安排停机检修。"
        elif "内圈" in user_message_lower:
            return f"轴承内圈故障特征：{MCSA_KNOWLEDGE['轴承故障']['inner_race']}。内圈故障通常比外圈故障更严重，需要紧急处理。"
        else:
            return "轴承故障诊断要点：1）分析BPFO、BPFI、BSF、FTF频率成分；2）观察频谱包络；3）检查振动幅值变化；4）结合温度监测数据。需要具体分析哪种轴承故障？"
    
    elif any(keyword in user_message_lower for keyword in ["偏心", "eccentricity"]):
        if "静" in user_message_lower:
            return f"静偏心故障特征：{MCSA_KNOWLEDGE['偏心故障']['static']}。需检查定子与转子之间的气隙是否均匀。"
        elif "动" in user_message_lower:
            return f"动偏心故障特征：{MCSA_KNOWLEDGE['偏心故障']['dynamic']}。可能是轴承磨损或安装不当造成。"
        else:
            return "偏心故障分为静偏心和动偏心两种。静偏心表现为电源频率处的边频带，动偏心表现为转子频率调制。请描述具体的频谱特征。"
    
    elif any(keyword in user_message_lower for keyword in ["断条", "broken", "bar"]):
        return f"转子断条故障特征：{MCSA_KNOWLEDGE['断条故障']['frequency']}。断条会导致转子电阻不平衡，产生特征频率的边频带。建议分析负载变化时的频谱演变。"
    
    elif any(keyword in user_message_lower for keyword in ["匝间", "turn", "短路"]):
        return f"匝间短路故障：{MCSA_KNOWLEDGE['匝间短路']['frequency']}。会引起三相电流不平衡，增大负序电流分量。建议进行负序阻抗测试。"
    
    elif any(keyword in user_message_lower for keyword in ["频谱", "spectrum", "fft"]):
        return "MCSA频谱分析要点：1）选择合适的采样频率；2）确保足够的频率分辨率；3）使用窗函数减少泄漏；4）分析基频、谐波和边频带。需要分析什么类型的频谱特征？"
    
    elif any(keyword in user_message_lower for keyword in ["维护", "maintenance", "修复"]):
        return "基于MCSA诊断结果的维护建议：1）轻微异常：增加监测频次；2）中等异常：计划性维护；3）严重异常：立即停机检修。具体维护方案需要结合故障类型和设备重要性制定。"
    
    else:
        responses = [
            "我是MCSA智能诊断助手，专注于电机故障分析。请描述您遇到的具体问题，比如异常频谱、振动、温度等现象。",
            "根据MCSA分析经验，请提供更多详细信息：电机类型、运行工况、故障现象等，我将为您提供专业的诊断建议。",
            "MCSA诊断可以检测轴承故障、偏心、断条、匝间短路等问题。请告诉我您需要分析哪种故障类型？"
        ]
        return random.choice(responses)

async def call_huggingface_api(messages: List[Dict], api_key: Optional[str]) -> str:
    """调用 Hugging Face API"""
    if not api_key:
        # 如果没有 API key，使用本地知识库
        last_message = messages[-1]["content"] if messages else ""
        return get_mcsa_response(last_message)
    
    try:
        async with aiohttp.ClientSession() as session:
            # 构建对话上下文
            conversation_text = ""
            for msg in messages[-5:]:  # 只取最近5轮对话
                role = "User" if msg["role"] == "user" else "Assistant"
                conversation_text += f"{role}: {msg['content']}\n"
            
            payload = {
                "inputs": conversation_text,
                "parameters": {
                    "max_length": 200,
                    "temperature": 0.7,
                    "return_full_text": False
                }
            }
            
            headers = AI_PROVIDERS["huggingface"]["headers"].copy()
            headers["Authorization"] = f"Bearer {api_key}"
            
            async with session.post(
                AI_PROVIDERS["huggingface"]["url"],
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if isinstance(result, list) and len(result) > 0:
                        generated_text = result[0].get("generated_text", "")
                        # 结合 MCSA 知识进行回复
                        mcsa_response = get_mcsa_response(messages[-1]["content"])
                        return f"{mcsa_response}\n\n补充信息：{generated_text}" if generated_text else mcsa_response
                    else:
                        return get_mcsa_response(messages[-1]["content"])
                else:
                    logger.warning(f"Hugging Face API error: {response.status}")
                    return get_mcsa_response(messages[-1]["content"])
                    
    except Exception as e:
        logger.error(f"Error calling Hugging Face API: {str(e)}")
        return get_mcsa_response(messages[-1]["content"])

async def call_qwen_api_stream(messages: List[Dict], api_key: Optional[str]):
    """调用阿里云通义千问 API - 流式响应版本"""
    if not api_key:
        # 返回本地MCSA知识库回复的生成器
        response = get_mcsa_response(messages[-1]["content"] if messages else "")
        for char in response:
            yield f"data: {json.dumps({'content': char}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.03)  # 模拟打字效果
        yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"
        return
    
    try:
        async with aiohttp.ClientSession() as session:
            # 添加系统提示
            system_message = {
                "role": "system",
                "content": "你是一个专业的电机故障诊断专家，专注于MCSA（电机电流信号分析）技术。请基于专业知识为用户提供准确的故障诊断和维护建议。回复使用Markdown格式，包含适当的标题、列表、表格和代码块。"
            }
            
            api_messages = [system_message] + messages[-10:]  # 最近10轮对话
            
            payload = {
                "model": "qwen-plus",
                "input": {
                    "messages": api_messages
                },
                "parameters": {
                    "result_format": "message",
                    "temperature": 0.7,
                    "max_tokens": 2000,
                    "incremental_output": True  # 启用增量输出（流式）
                }
            }
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
                "Cache-Control": "no-cache"
            }
            
            async with session.post(
                "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 200:
                    # 处理流式响应
                    buffer = ""
                    async for chunk in response.content.iter_chunked(1024):
                        if chunk:
                            buffer += chunk.decode('utf-8')
                            lines = buffer.split('\n')
                            buffer = lines[-1]  # 保留未完成的行
                            
                            for line in lines[:-1]:
                                if line.strip().startswith('data:'):
                                    try:
                                        json_data = line.strip()[5:].strip()
                                        if json_data and json_data != '[DONE]':
                                            data = json.loads(json_data)
                                            if "output" in data and "choices" in data["output"]:
                                                content = data["output"]["choices"][0]["message"]["content"]
                                                yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"
                                    except json.JSONDecodeError:
                                        continue
                    
                    yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"
                else:
                    # API调用失败，返回本地回复
                    response_text = get_mcsa_response(messages[-1]["content"] if messages else "")
                    for char in response_text:
                        yield f"data: {json.dumps({'content': char}, ensure_ascii=False)}\n\n"
                        await asyncio.sleep(0.03)
                    yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"
                    
    except Exception as e:
        logger.error(f"Error calling 通义千问 API: {str(e)}")
        # 返回本地回复
        response_text = get_mcsa_response(messages[-1]["content"] if messages else "")
        for char in response_text:
            yield f"data: {json.dumps({'content': char}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.03)
        yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"

async def call_qwen_api(messages: List[Dict], api_key: Optional[str]) -> str:
    """调用阿里云通义千问 API - 集成RAG功能"""
    if not api_key:
        last_message = messages[-1]["content"] if messages else ""
        return get_mcsa_response(last_message)
    
    try:
        # 尝试使用RAG增强回复
        try:
            rag_engine = await get_rag_engine()
            last_message = messages[-1]["content"] if messages else ""
            
            # 使用RAG生成增强回复
            async def llm_func(prompt):
                async with aiohttp.ClientSession() as session:
                    system_message = {
                        "role": "system",
                        "content": "你是一个专业的电机故障诊断专家，专注于MCSA（电机电流信号分析）技术。请基于专业知识为用户提供准确的故障诊断和维护建议。"
                    }
                    
                    api_messages = [system_message, {"role": "user", "content": prompt}]
                    
                    payload = {
                        "model": "qwen-plus",
                        "input": {
                            "messages": api_messages
                        },
                        "parameters": {
                            "result_format": "message",
                            "temperature": 0.7,
                            "max_tokens": 1500
                        }
                    }
                    
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    }
                    
                    async with session.post(
                        "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            if "output" in result and "choices" in result["output"]:
                                return result["output"]["choices"][0]["message"]["content"]
                        return "无法生成回复"
            
            # 使用RAG增强回复
            rag_response = await rag_engine.generate_rag_response(last_message, llm_func)
            return rag_response
            
        except Exception as e:
            logger.warning(f"RAG功能不可用，降级到标准API调用: {e}")
    
        # 标准API调用（降级方案）
        async with aiohttp.ClientSession() as session:
            # 添加系统提示
            system_message = {
                "role": "system",
                "content": "你是一个专业的电机故障诊断专家，专注于MCSA（电机电流信号分析）技术。请基于专业知识为用户提供准确的故障诊断和维护建议。"
            }
            
            api_messages = [system_message] + messages[-10:]  # 最近10轮对话
            
            payload = {
                "model": "qwen-plus",
                "input": {
                    "messages": api_messages
                },
                "parameters": {
                    "result_format": "message",
                    "temperature": 0.7,
                    "max_tokens": 1500
                }
            }
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            async with session.post(
                "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if "output" in result and "choices" in result["output"]:
                        return result["output"]["choices"][0]["message"]["content"]
                    else:
                        return get_mcsa_response(messages[-1]["content"])
                else:
                    logger.warning(f"通义千问 API error: {response.status}")
                    return get_mcsa_response(messages[-1]["content"])
                    
    except Exception as e:
        logger.error(f"Error calling 通义千问 API: {str(e)}")
        return get_mcsa_response(messages[-1]["content"])

async def call_openai_api(messages: List[Dict], api_key: Optional[str]) -> str:
    """调用 OpenAI API"""
    if not api_key:
        last_message = messages[-1]["content"] if messages else ""
        return get_mcsa_response(last_message)
    
    try:
        async with aiohttp.ClientSession() as session:
            # 添加系统提示
            system_message = {
                "role": "system",
                "content": "你是一个专业的电机故障诊断专家，专注于MCSA（电机电流信号分析）技术。请基于专业知识为用户提供准确的故障诊断和维护建议。"
            }
            
            api_messages = [system_message] + messages[-10:]  # 最近10轮对话
            
            payload = {
                "model": "gpt-3.5-turbo",
                "messages": api_messages,
                "max_tokens": 300,
                "temperature": 0.7
            }
            
            headers = AI_PROVIDERS["openai_compatible"]["headers"].copy()
            headers["Authorization"] = f"Bearer {api_key}"
            
            async with session.post(
                AI_PROVIDERS["openai_compatible"]["url"],
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    logger.warning(f"OpenAI API error: {response.status}")
                    return get_mcsa_response(messages[-1]["content"])
                    
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {str(e)}")
        return get_mcsa_response(messages[-1]["content"])

@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(request: ChatRequest):
    """AI 聊天接口"""
    start_time = asyncio.get_event_loop().time()
    
    try:
        # 构建消息历史
        messages = []
        # 检查conversation_history是否为None
        if request.conversation_history:
            for msg in request.conversation_history:
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        # 添加当前用户消息
        messages.append({
            "role": "user", 
            "content": request.message
        })
        
        # 根据提供商选择 API
        provider = (request.model_provider or "local").lower()
        response_text = ""
        
        if provider == "qwen":
            api_key = os.getenv('QWEN_API_KEY') or ""
            response_text = await call_qwen_api(messages, api_key)
            model_used = "自研技工大模型LLM"
        elif provider == "openai":
            api_key = os.getenv('OPENAI_API_KEY') or ""
            response_text = await call_openai_api(messages, api_key)
            model_used = "OpenAI GPT-3.5"
        elif provider == "huggingface":
            api_key = os.getenv('HUGGINGFACE_API_KEY') or ""
            response_text = await call_huggingface_api(messages, api_key)
            model_used = "Hugging Face DialoGPT"
        else:
            # 默认使用本地 MCSA 知识库
            response_text = get_mcsa_response(request.message)
            model_used = "本地 MCSA 知识库"
        
        processing_time = asyncio.get_event_loop().time() - start_time
        
        return ChatResponse(
            response=response_text,
            model_used=model_used,
            processing_time=round(processing_time * 1000, 2)  # 转换为毫秒
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"聊天服务暂时不可用: {str(e)}"
        )

@router.post("/chat/stream", summary="流式AI聊天")
async def chat_stream(request: ChatRequest):
    """
    流式AI聊天接口
    支持Server-Sent Events (SSE)流式响应
    """
    try:
        # 构建消息历史
        messages = []
        # 检查conversation_history是否为None
        if request.conversation_history:
            for msg in request.conversation_history:
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        # 添加当前用户消息
        messages.append({
            "role": "user", 
            "content": request.message
        })
        
        # 根据提供商选择流式API
        provider = (request.model_provider or "local").lower()
        
        if provider == "qwen":
            api_key = os.getenv('QWEN_API_KEY') or ""
            return StreamingResponse(
                call_qwen_api_stream(messages, api_key),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "*",
                }
            )
        else:
            # 对于其他提供商，暂时返回本地回复的流式版本
            async def stream_local_response():
                response_text = get_mcsa_response(request.message)
                for char in response_text:
                    yield f"data: {json.dumps({'content': char}, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.03)
                yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"
            
            return StreamingResponse(
                stream_local_response(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "*",
                }
            )
    
    except Exception as e:
        logger.error(f"Error in stream chat endpoint: {str(e)}")
        
        # 错误时返回流式错误回复
        async def stream_error_response():
            error_msg = f"抱歉，AI服务暂时不可用。错误信息：{str(e)}。\n\n作为备选，我可以基于MCSA知识库为您提供基础的诊断建议。"
            for char in error_msg:
                yield f"data: {json.dumps({'content': char}, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.03)
            yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            stream_error_response(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            }
        )

@router.get("/models")
async def get_available_models():
    """获取可用的 AI 模型列表"""
    models = [
        {
            "id": "local",
            "name": "本地 MCSA 知识库",
            "description": "基于专业 MCSA 知识的本地模型，完全免费",
            "status": "available",
            "free": True
        }
    ]
    
    # 检查各种 API key 是否配置
    if os.getenv('QWEN_API_KEY'):
        models.append({
            "id": "qwen",
            "name": "Jigong LLM",
            "description": "专为中文优化的大语言模型，每月100万tokens免费",
            "status": "available",
            "free": True
        })
    
    if os.getenv('HUGGINGFACE_API_KEY'):
        models.append({
            "id": "huggingface",
            "name": "Hugging Face DialoGPT",
            "description": "免费的对话模型，适合日常交流",
            "status": "available",
            "free": True
        })
    
    if os.getenv('OPENAI_API_KEY'):
        models.append({
            "id": "openai",
            "name": "OpenAI GPT-3.5",
            "description": "强大的大语言模型，有免费额度",
            "status": "available", 
            "free": False
        })
    
    return {"models": models}

@router.get("/health")
async def health_check():
    """AI 服务健康检查"""
    return {
        "status": "healthy",
        "service": "MCSA AI Chat Service",
        "timestamp": asyncio.get_event_loop().time()
    }

@router.post("/rag/query")
async def rag_query(request: ChatRequest):
    """
    RAG知识检索接口
    直接使用RAG引擎进行知识检索，不调用大模型
    """
    try:
        rag_engine = await get_rag_engine()
        
        # 检索相关知识
        relevant_docs = await rag_engine.query(request.message)
        
        if not relevant_docs:
            return {
                "response": "未找到相关的MCSA知识库内容。请尝试使用更具体的关键词。",
                "knowledge_sources": [],
                "model_used": "RAG知识检索"
            }
        
        # 构建知识源回复
        response_parts = []
        knowledge_sources = []
        
        for doc in relevant_docs:
            response_parts.append(f"**{doc['title']}**\n{doc['content'][:300]}...")
            knowledge_sources.append({
                "title": doc['title'],
                "category": doc.get('category', ''),
                "score": doc.get('score', 0),
                "keywords": doc.get('keywords', [])
            })
        
        response_text = "\n\n".join(response_parts)
        response_text += "\n\n📚 以上内容来源于MCSA专业知识库"
        
        return {
            "response": response_text,
            "knowledge_sources": knowledge_sources,
            "model_used": "RAG知识检索"
        }
        
    except Exception as e:
        logger.error(f"RAG查询失败: {str(e)}")
        return {
            "response": f"RAG知识检索服务暂时不可用: {str(e)}",
            "knowledge_sources": [],
            "model_used": "RAG知识检索"
        }

@router.get("/rag/status")
async def rag_status():
    """获取RAG系统状态"""
    try:
        rag_engine = await get_rag_engine()
        return {
            "status": "active" if rag_engine.initialized else "initializing",
            "knowledge_count": len(rag_engine.knowledge_cache),
            "config": {
                "working_dir": rag_engine.config.working_dir,
                "top_k": rag_engine.config.top_k,
                "similarity_threshold": rag_engine.config.similarity_threshold
            },
            "knowledge_categories": list(set(
                knowledge.get('category', '通用') 
                for knowledge in rag_engine.knowledge_cache.values()
            ))
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        } 