# OCR RAG 后端服务

这是OCR RAG多模态检索增强生成系统的后端服务，基于FastAPI构建，提供PDF文档处理、OCR识别、向量索引和智能问答等核心功能。

## 项目简介

本后端服务为OCR RAG系统提供所有核心功能，包括文档上传、解析、OCR识别、向量索引构建和RAG问答等。服务采用模块化设计，确保代码的可维护性和可扩展性。

## 技术栈

- **Web框架**：FastAPI
- **Web服务器**：Uvicorn
- **文档解析**：PyMuPDF (fitz)、Unstructured
- **OCR技术**：PaddleOCR
- **向量存储**：FAISS
- **LLM集成**：LangChain、DeepSeek、Ollama
- **数据库**：SQLAlchemy、SQLite
- **异步编程**：Asyncio
- **图像处理**：Pillow、Matplotlib

## 目录结构

```
backend/
├── app.py                  # FastAPI主应用入口
├── run.py                  # 服务器启动脚本
├── requirements.txt        # Python依赖列表
├── database.py             # 数据库模型定义
├── openapi.yaml            # OpenAPI规范文件
├── services/               # 核心服务模块
│   ├── pdf_service.py      # PDF处理服务
│   ├── index_service.py    # 向量索引服务
│   ├── rag_service.py      # RAG问答服务
│   └── database_service.py # 数据库服务
└── data/                   # 数据存储目录（自动创建）
```

## 核心服务介绍

### PDF服务 (`pdf_service.py`)
- **文件上传与保存**：处理用户上传的PDF文件
- **页面渲染**：将PDF页面渲染为图像
- **内容解析**：提取文本、图像和表格内容
- **OCR识别**：识别文档中的文字内容
- **Markdown转换**：将解析后的内容转换为Markdown格式

### 索引服务 (`index_service.py`)
- **向量嵌入**：使用Ollama的bge-m3模型生成文本嵌入（需要访问本地ollama部署的embedding模型）
- **FAISS索引**：构建和管理高效的向量索引
- **相似度搜索**：执行向量相似度搜索，找出相关文档片段

### RAG服务 (`rag_service.py`)
- **会话管理**：管理用户会话和聊天历史
- **检索增强**：基于用户问题检索相关文档内容
- **答案生成**：使用DeepSeek模型生成回答
- **流式响应**：支持SSE流式传输，提供实时反馈
- **引用生成**：为回答添加引用信息，支持溯源

### 数据库服务 (`database_service.py`)
- **文件管理**：存储和管理上传的文件信息
- **状态跟踪**：跟踪文件解析和索引状态
- **数据持久化**：使用SQLite进行数据持久化

## 快速开始

### 前提条件
- **Python 3.8+**
- **Ollama**（用于本地向量嵌入，需下载bge-m3模型）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动服务

```bash
python run.py
```
服务将在 `http://localhost:8001` 启动

### API文档
启动服务后，可以访问以下地址查看自动生成的API文档：
- Swagger UI：`http://localhost:8001/docs`
- ReDoc：`http://localhost:8001/redoc`

## API接口说明

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
- **响应**：SSE事件流，包含 `token`、`citation`、`done` 和 `error` 事件

### 文件管理接口
- **文件上传**：`POST /api/v1/files/upload`
- **获取文件列表**：`GET /api/v1/files`
- **获取文件详情**：`GET /api/v1/files/{file_id}`
- **删除文件**：`DELETE /api/v1/files/{file_id}`

### 文档处理接口
- **解析文档**：`POST /api/v1/files/{file_id}/parse`
- **构建索引**：`POST /api/v1/files/{file_id}/index`
- **获取页面图像**：`GET /api/v1/files/{file_id}/pages/{page_num}`

## 配置说明

### 环境变量
在 `.env` 文件中配置以下环境变量：

```env
# 模型配置
EMBED_MODEL=bge-m3:latest
OLLAMA_BASE_URL=http://127.0.0.1:11434

# 服务配置
PORT=8001
HOST=0.0.0.0
RELOAD=True

# 数据库配置
DATABASE_URL=sqlite:///./ocr_rag.db
```

### 检索配置
在 `rag_service.py` 中可以调整以下检索参数：
- `K`：每次检索的文档片段数量
- `SCORE_TAU_TOP1`：顶级文档片段的相似度阈值
- `SCORE_TAU_MEAN3`：前三个文档片段的平均相似度阈值

## 开发指南

1. **安装开发依赖**
```bash
pip install -e "[dev]"
```

2. **代码风格检查**
```bash
black .
flake8
```

3. **运行测试**
```bash
pytest
```

## 部署说明

### 生产环境部署

1. **安装依赖**
```bash
pip install -r requirements.txt
```

2. **配置环境变量**
确保在生产环境中配置适当的环境变量，特别是关闭 `RELOAD` 选项

3. **使用Gunicorn和Uvicorn**
```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:app --bind 0.0.0.0:8001
```

### Docker部署
可以使用以下Dockerfile进行容器化部署：

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "run.py"]
```

## 注意事项

1. **Ollama服务**：确保在部署环境中运行了Ollama服务，并下载了bge-m3模型
2. **资源需求**：处理大文件时可能需要更多的内存和处理时间
3. **CORS配置**：当前CORS配置允许所有来源，生产环境请根据需要收紧此配置
4. **数据存储**：`data` 目录存储用户上传的文件和处理结果，确保有足够的磁盘空间

## License

MIT License