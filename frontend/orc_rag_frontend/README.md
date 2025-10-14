# OCR RAG 前端应用

这是OCR RAG多模态检索增强生成系统的前端应用，使用Vue 3 + Vite构建，提供直观的用户界面和流畅的交互体验。

## 项目简介

本前端应用为OCR RAG系统提供用户界面，支持PDF文件上传、文档查看、智能问答等功能。应用采用现代化的技术栈，确保高性能和良好的用户体验。

## 技术栈

- **框架**：Vue 3
- **构建工具**：Vite
- **状态管理**：Pinia
- **UI组件库**：Element Plus
- **路由**：Vue Router
- **HTTP客户端**：Axios
- **Markdown渲染**：Markdown-it

## 项目结构

```
orc_rag_frontend/
├── src/                    # 源代码目录
│   ├── components/         # Vue组件
│   │   ├── chat/           # 聊天相关组件
│   │   ├── pdf/            # PDF查看相关组件
│   │   └── layout/         # 布局组件
│   ├── views/              # 页面视图
│   ├── services/           # API服务和业务逻辑
│   ├── store/              # Pinia状态管理
│   ├── router/             # 路由配置
│   ├── styles/             # 全局样式
│   ├── assets/             # 静态资源
│   ├── main.js             # 应用入口
│   └── App.vue             # 根组件
├── public/                 # 静态文件目录
├── package.json            # npm依赖配置
├── vite.config.js          # Vite配置
└── README.md               # 项目说明文档
```

## 快速开始

### 前提条件
- **Node.js 16+**
- **npm 7+** 或 **yarn 1.22+** 或 **pnpm 7+**

### 安装依赖

```bash
npm install
# 或
yarn install
# 或
pnpm install
```

### 开发模式

```bash
npm run dev
# 或
vite
```
应用将在开发服务器上运行，通常是 `http://localhost:5173`

### 构建生产版本

```bash
npm run build
# 或
vite build
```
构建后的文件将位于 `dist` 目录

### 预览生产构建

```bash
npm run preview
# 或
vite preview
```

## 主要功能

1. **文件上传**：支持PDF文件的上传和管理
2. **文档查看**：可视化展示上传的文档内容
3. **智能问答**：与系统进行交互式对话，获取基于文档内容的回答
4. **引用溯源**：查看回答中引用的文档来源
5. **会话管理**：支持多会话切换和历史记录查看

## 配置说明

### 环境变量
在 `.env` 文件中配置后端API地址等环境变量

```env
VITE_API_BASE_URL=http://localhost:8001/api/v1
```

### API服务配置
前端通过 `src/services/api.js` 配置与后端的通信

## 开发指南

1. **组件开发**：在 `src/components/` 目录下创建新组件
2. **页面开发**：在 `src/views/` 目录下创建新页面
3. **状态管理**：使用Pinia进行全局状态管理
4. **API调用**：通过 `src/services/api.js` 提供的接口调用后端API

## 注意事项

1. 确保后端服务已启动并可访问
2. 开发时使用 `npm run dev` 命令启动开发服务器
3. 构建前确保所有依赖已正确安装
4. 生产环境中注意配置正确的API地址

## License

MIT License
