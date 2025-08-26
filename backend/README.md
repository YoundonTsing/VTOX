# 匝间短路故障诊断系统 - 后端

## 项目结构

```
backend/
├── app/                    # 应用程序主目录
│   ├── analysis/           # 分析模块
│   │   ├── __init__.py
│   │   ├── fault_scorer.py    # 故障评分计算
│   │   └── feature_calculator.py  # 特征计算
│   ├── core/               # 核心模块
│   │   ├── __init__.py
│   │   └── config.py       # 配置管理
│   ├── models/             # 数据模型
│   │   ├── __init__.py
│   │   └── diagnosis_models.py  # 诊断相关模型
│   ├── routers/            # API路由
│   │   ├── __init__.py
│   │   ├── diagnosis.py    # 诊断相关路由
│   │   └── samples.py      # 样本相关路由
│   ├── services/           # 服务层
│   │   ├── __init__.py
│   │   └── turn_to_turn_diagnosis.py  # 匝间短路诊断服务
│   ├── utils/              # 工具函数
│   │   ├── __init__.py
│   │   ├── data_preprocessor.py  # 数据预处理
│   │   └── file_parser.py  # 文件解析
│   ├── __init__.py
│   └── main.py             # 应用入口
├── data/                   # 数据目录
│   ├── samples/            # 样本数据
│   └── uploads/            # 上传文件
└── logs/                   # 日志目录
```

## 模块说明

### 1. 分析模块 (analysis)
包含特征计算和故障评分的核心算法。

- `feature_calculator.py`: 从电机数据中提取特征参数
- `fault_scorer.py`: 基于特征参数计算故障评分

### 2. 核心模块 (core)
包含应用程序的核心配置和通用功能。

- `config.py`: 集中管理系统配置参数

### 3. 数据模型 (models)
定义数据结构和验证规则。

- `diagnosis_models.py`: 诊断相关的数据模型定义

### 4. API路由 (routers)
处理HTTP请求和响应。

- `diagnosis.py`: 诊断相关的API端点
- `samples.py`: 样本数据相关的API端点

### 5. 服务层 (services)
实现业务逻辑。

- `turn_to_turn_diagnosis.py`: 匝间短路故障诊断服务

### 6. 工具函数 (utils)
提供通用功能和辅助函数。

- `data_preprocessor.py`: 数据预处理功能
- `file_parser.py`: 文件解析功能

## 启动应用

```bash
# 进入后端目录
cd backend

# 安装依赖
pip install -r requirements.txt

# 启动应用
uvicorn app.main:app --reload
```

## API文档

启动应用后，可以通过以下URL访问API文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc 