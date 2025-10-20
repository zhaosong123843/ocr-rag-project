# OCR RAG 多模态检索增强生成系统

## 项目简介

这是一个基于**检索增强生成（RAG）**技术的多模态文档处理系统，支持PDF文档的上传、解析、OCR识别、向量索引和智能问答。系统采用前后端分离架构，能够提供流畅的用户体验和强大的文档理解能力。

## 功能特性

### 文档处理功能
- 📄 **PDF上传与解析**：支持上传PDF文件并提取文本、图片和表格内容
- 🔍 **OCR文本识别**：使用PaddleOCR技术识别文档中的文字内容
- 🗂️ **多模态向量索引**：利用Chroma构建高效的向量检索系统
- 📊 **结构化解析**：识别文档结构，包括标题、文本、图像和表格等元素
- 📝 **Markdown输出**：将解析后的内容转换为Markdown格式

### 智能问答功能
- 💬 **实时聊天交互**：支持流式响应，提供流畅的问答体验
- 🔗 **引用溯源**：回答中包含引用来源，支持跳转到原文对应位置(待更新)
- 🧠 **上下文理解**：基于检索到的相关文档内容生成准确回答
- 💾 **会话记忆**：支持多会话管理，保存聊天历史记录

### 技术架构
- ⚡ **前后端分离**：前端使用Vue 3，后端使用FastAPI
- 🚀 **高性能**：使用异步编程和流式传输提升用户体验
- 🔄 **模块化设计**：服务层模块化，便于扩展和维护
- 🎨 **现代化UI**：采用Element Plus组件库，提供美观直观的界面
- 📊 **完善的日志系统**：支持多级日志记录、异常追踪和文件轮转，便于问题排查和系统监控

## 技术栈

### 后端技术栈
- **框架**：FastAPI
- **Web服务器**：Uvicorn
- **文档解析**：PyMuPDF、Unstructured
- **OCR技术**：PaddleOCR
- **向量存储**：Chroma
- **LLM集成**：LangChain、DeepSeek、Ollama
- **数据库**：SQLAlchemy、SQLite
- **异步编程**：Asyncio
- **日志系统**：自定义日志服务，支持多级别日志记录和文件轮转

### 前端技术栈
- **框架**：Vue 3
- **状态管理**：Pinia
- **UI组件库**：Element Plus
- **路由**：Vue Router
- **HTTP客户端**：Axios
- **Markdown渲染**：Markdown-it
- **构建工具**：Vite

## 目录结构

```
ocr_rag_preject/
├── README.md              # 项目说明文档
├── .gitignore             # Git忽略文件配置
├── backend/               # 后端代码
│   ├── README.md          # 后端服务说明
│   ├── app.py             # FastAPI主应用
│   ├── run.py             # 服务器启动脚本
│   ├── requirements.txt   # Python依赖
│   ├── openapi.yaml       # OpenAPI规范文件
│   ├── models/            # 模型目录
│   │   └── bge-reranker-v2-m3/ # Reranker模型
│   ├── services/          # 核心服务模块
│   │   ├── pdf_service.py     # PDF处理服务
│   │   ├── index_service.py   # 向量索引服务
│   │   ├── rag_service.py     # RAG问答服务
│   │   ├── database_service.py # 数据库服务
│   │   ├── log_service.py     # 日志服务
│   │   ├── ultis.py           # 工具函数
│   │   └── create_database.py # 数据库创建脚本
│   └── data/              # 数据存储目录（自动创建）
└── frontend/              # 前端代码
    └── orc_rag_frontend/  # Vue前端项目
        ├── README.md      # 前端说明文档
        ├── .gitignore     # Git忽略文件配置
        ├── .vscode/       # VSCode配置
        ├── index.html     # HTML入口
        ├── package.json   # npm依赖配置
        ├── package-lock.json # 依赖版本锁定
        ├── vite.config.js # Vite配置
        ├── public/        # 静态资源目录
        └── src/           # 前端源代码
            ├── components/   # Vue组件
            ├── views/        # 页面视图
            ├── services/     # API服务
            ├── store/        # Pinia状态管理
            ├── router/       # 路由配置
            └── main.js       # 应用入口
```

## 快速开始

### 前提条件
- **Python 3.8+**
- **Node.js 16+**
- **Ollama**（用于本地向量嵌入）

### 后端启动步骤

1. **进入后端目录**
```bash
cd backend
```

2. **安装Python依赖**
```bash
pip install -r requirements.txt
```

3. **运行后端服务器**
```bash
python run.py
```
后端服务将在 `http://localhost:8001` 启动

### 前端启动步骤

1. **进入前端目录**
```bash
cd frontend/orc_rag_frontend
```

2. **安装npm依赖**
```bash
npm install
```

3. **启动前端开发服务器**
```bash
npm run dev
```
前端服务将在 `http://localhost:5173` 启动

## API 接口说明

### 健康检查
```
GET /api/v1/health
```
- **描述**：检查服务是否正常运行
- **响应**：`{"ok": true, "version": "1.0.0"}`

### 聊天接口
```
POST /api/v1/chat
```
- **描述**：与系统进行对话，支持流式响应
- **参数**：`message`（用户问题）、`sessionId`（会话ID，可选）、`fileID`（文件ID，可选）
- **响应**：SSE事件流，包含 `token`（文本片段）、`citation`（引用信息）、`done`（完成标志）

### 文件上传接口
- 系统支持PDF文件上传，上传后的文件会被自动解析和索引
- 上传的文件将保存在`data/{file_id}`目录下
- 解析后的内容会生成Markdown格式文件

## 使用指南

1. **上传PDF文档**：在界面中点击上传按钮，选择要处理的PDF文件
2. **等待解析完成**：系统会自动解析文档内容，生成向量索引
3. **开始问答**：在聊天界面输入问题，系统会基于文档内容生成回答
4. **查看引用**：回答中会包含引用信息，点击可以查看原文来源

## 注意事项

1. **环境变量配置**：根据需要在`.env`文件中配置API密钥等环境变量
2. **Ollama服务**：确保本地运行了Ollama服务，且已下载`bge-m3:latest`模型
3. **资源占用**：处理大文件时可能需要更多的内存和处理时间
4. **开发模式**：当前CORS配置允许所有来源，生产环境请收紧此配置

## 项目扩展

1. **支持更多文档格式**：可以扩展支持Word、Excel等其他文档格式
2. **模型优化**：可以尝试使用不同的LLM和嵌入模型提升效果
3. **界面增强**：添加更多交互功能，如文档目录导航、高亮显示等
4. **部署优化**：配置Docker容器化部署，便于在不同环境中运行

## License

MIT License

---

**OCR RAG Project** © 2024 | 多模态检索增强生成系统