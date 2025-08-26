# 匝间短路诊断系统前端

本项目是电机匝间短路诊断系统的前端部分，基于Vue3 + Vite实现。

## 功能特点

- 电机数据CSV文件上传
- 匝间短路故障诊断结果可视化
- 特征参数详情展示
- 诊断报告导出

## 技术栈

- Vue3: 前端框架
- Vite: 构建工具
- Element Plus: UI组件库
- Axios: HTTP客户端
- ECharts: 数据可视化

## 安装

```bash
# 安装依赖
npm install
```

## 开发

```bash
# 启动开发服务器
npm run dev
```

服务将在 http://localhost:3000 上运行

## 构建

```bash
# 构建生产版本
npm run build
```

## 目录结构

```
src/
├── api/          # API接口
├── assets/       # 静态资源
├── components/   # 组件
├── router/       # 路由配置
├── styles/       # 样式文件
├── utils/        # 工具函数
├── views/        # 页面视图
├── App.vue       # 根组件
└── main.js       # 入口文件
```

## 页面说明

- 首页：上传CSV文件并显示分析结果
- 关于页面：系统介绍和使用说明

## 后端API

前端默认连接到 `http://localhost:8000` 的后端API，可以通过修改 `vite.config.js` 中的代理设置更改。 