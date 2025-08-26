# 通义千问 API 配置指南

## 🎯 为什么选择通义千问？

通义千问是阿里云开发的大语言模型，特别适合中文应用场景：

✅ **每月100万tokens免费** - 个人和小团队完全够用
✅ **中文能力优秀** - 专门为中文优化，理解更准确
✅ **国内访问稳定** - 无需科学上网，响应速度快
✅ **专业技术能力** - 在工程和技术领域表现出色

## 📝 注册和获取 API Key

### 1. 注册阿里云账号
- 访问：https://dashscope.aliyun.com/
- 使用手机号或邮箱注册

### 2. 开通 DashScope 服务
- 登录后点击**立即开通**
- 完成实名认证（必需）
- 开通后自动获得每月100万tokens免费额度

### 3. 创建 API Key
1. 前往 [API-KEY管理页面](https://dashscope.console.aliyun.com/apiKey)
2. 点击**创建API Key**
3. 选择**默认工作空间**
4. 点击**确认创建**
5. 复制你的API Key（格式：`sk-xxxxxxxxxx`）

## ⚙️ 配置环境变量

### Windows 配置

#### 方法一：通过系统属性（推荐）
1. 按 `Win + R`，输入 `sysdm.cpl`
2. 点击**环境变量**
3. 在用户变量中点击**新建**
4. 变量名：`QWEN_API_KEY`
5. 变量值：`sk-你的API密钥`
6. 确定并重启命令行

#### 方法二：通过命令行（临时）
```cmd
# CMD
set QWEN_API_KEY=sk-你的API密钥

# PowerShell
$env:QWEN_API_KEY="sk-你的API密钥"
```

### Linux/macOS 配置

#### 永久配置
```bash
# 添加到 ~/.bashrc 或 ~/.zshrc
echo 'export QWEN_API_KEY="sk-你的API密钥"' >> ~/.bashrc
source ~/.bashrc
```

#### 临时配置
```bash
export QWEN_API_KEY="sk-你的API密钥"
```

### 验证配置
```bash
# Windows CMD
echo %QWEN_API_KEY%

# Windows PowerShell
echo $env:QWEN_API_KEY

# Linux/macOS
echo $QWEN_API_KEY
```

## 🚀 启动服务

### 1. 安装依赖
```bash
cd backend
pip install aiohttp==3.8.5
```

### 2. 启动后端
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 测试API
```bash
curl -X POST http://localhost:8000/ai/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "电机轴承外圈故障如何诊断？",
    "model_provider": "qwen"
  }'
```

## 🎨 前端使用

访问 http://localhost:3000/agent 即可看到：

- **模型选择器**显示"阿里云通义千问"
- **智能对话**支持专业的MCSA诊断咨询
- **自动降级**API失败时使用本地知识库

## 📊 费用说明

### 免费额度
- **每月100万tokens** - 约50万汉字
- **有效期**：开通后180天内使用完
- **续费**：用完后自动按量计费

### 付费价格（如果超出免费额度）
- **qwen-plus**：¥0.008/1K tokens（约0.004元/500汉字）
- **qwen-turbo**：¥0.003/1K tokens（更便宜，速度更快）

### 成本估算
假设每天100次对话，每次200汉字回复：
- 每月约 **6万tokens**
- **完全在免费额度内** 🎉

## 🔧 高级配置

### 1. 模型切换
在前端可以选择不同模型：
- `qwen-plus` - 能力最强（默认）
- `qwen-turbo` - 速度最快
- `qwen-max` - 最新最强

### 2. 参数调优
可以在后端代码中调整：
```python
payload = {
    "model": "qwen-plus",
    "parameters": {
        "temperature": 0.7,    # 创造性 0-1
        "max_tokens": 1500,    # 最大回复长度
        "top_p": 0.8          # 多样性控制
    }
}
```

### 3. 系统提示优化
针对MCSA诊断优化系统提示：
```python
system_message = {
    "role": "system",
    "content": """你是专业的电机故障诊断专家，精通MCSA技术。
    请基于以下专业知识回答：
    1. 轴承故障特征频率分析
    2. 偏心故障诊断方法  
    3. 断条故障识别技术
    4. 匝间短路检测原理
    
    回答要准确、实用，提供具体的诊断步骤和维护建议。"""
}
```

## ❗ 常见问题

### Q: API调用失败怎么办？
A: 系统会自动降级到本地MCSA知识库，确保服务可用性

### Q: 如何监控API使用量？
A: 登录 [DashScope控制台](https://dashscope.console.aliyun.com/) 查看用量统计

### Q: 支持流式输出吗？
A: 当前版本暂不支持，返回完整回复内容

### Q: 可以自定义模型吗？
A: 支持，可以使用阿里云的模型微调服务

## 🎉 完成！

现在你的MCSA诊断系统已经接入了强大的通义千问AI！

享受专业的中文AI对话体验吧！🚀 