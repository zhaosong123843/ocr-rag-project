from fastapi import FastAPI, UploadFile, File, Query, Body
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import time
import asyncio
from typing import Optional, Dict, Any
from pydantic import BaseModel
from typing import Optional

from fastapi.responses import StreamingResponse, JSONResponse
from fastapi import BackgroundTasks
from services.pdf_service import (
    save_upload,
    dir_original_pages,
    dir_parsed_pages,
    pdf_to_markdown,
    render_original_pages,
    unstructured_segments,
    render_parsed_pages_with_boxes,
    
)
from services.index_service import build_chroma_index, search_chroma
from services.rag_service import answer_stream, clear_history
from services.ultis import rid,err
from services.log_service import get_logger, info, warning, error, log_exception
# 导入数据库相关功能
from services.database_service import (
    get_db, 
    add_file_info, 
    update_file_parse_status, 
    get_all_file_names, 
    get_file_by_name,
    get_file_by_random_name,
    update_file_index_status
    )

# 初始化日志
logger = get_logger('app')
logger.info('应用启动中...')

app = FastAPI(
    title="多模态RAG系统API",
    version="1.0.0",
    description="多模态RAG系统后端API。"
)

# 允许前端本地联调
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # 课堂演示方便，生产请收紧
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"

# ---------------- 内存态存储- ---------------
current_pdf: Dict[str, Any] = {
    "fileId": None,
    "name": None,
    "pages": 0,
    "status": "idle",      # idle | parsing | ready | error
    "progress": 0
}
citations: Dict[str, Dict[str, Any]] = {}   # citationId -> { fileId, page, snippet, bbox, previewUrl }

# ---------------- Health ----------------
@app.get(f"{API_PREFIX}/health", tags=["Health"])
async def health():
    return {"ok": True, "version": "1.0.0"}

# ---------------- Chat（SSE，POST 返回 event-stream） ----------------
class ChatRequest(BaseModel):
    message: str
    sessionId: Optional[str] = None
    fileID: Optional[str] = None

@app.post(f"{API_PREFIX}/chat", tags=["Chat"])
async def chat_stream(req: ChatRequest):
    """
    SSE 事件：token | citation | done | error
    """
    async def gen():
        try:
            logger.info(f"开始处理聊天请求，message: {req.message}, sessionId: {req.sessionId}, fileID: {req.fileID}")
            time_start = time.time()
            # 获取用户问题
            question = (req.message or "").strip()
            # 当前会话ID
            session_id = (req.sessionId or "default").strip()  # 默认单会话
            # 上传的文件ID
            file_id = (req.fileID or "").strip()

            citations, context_text = [], ""
            branch = "no_context"

            # 从数据表中根据文件名获取文件ID
            if file_id:
                try:
                    # 获取检索到的内容 - 修正参数顺序并改为同步调用
                    citations, context_text = search_chroma(file_id, question)
                    branch = "with_context" if context_text else "no_context"
                except FileNotFoundError:
                    branch = "no_context"

            # 先推送引用（若有）
            if branch == "with_context" and citations:
                for c in citations:
                    yield "event: citation\n"
                    yield f"data: {c}\n\n"

            # 再推送 token 流（内部会写入历史）
            async for evt in answer_stream(
                question=question,
                citations=citations,
                context_text=context_text,
                branch=branch,
                session_id=session_id
            ):
                if evt["type"] == "token":
                    yield "event: token\n"
                    # 注意：这里确保 data 是合法 JSON 字符串
                    text = evt["data"].replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')
                    yield f'data: {{"text":"{text}"}}\n\n'
                elif evt["type"] == "citation":
                    yield "event: citation\n"
                    yield f"data: {evt['data']}\n\n"
                elif evt["type"] == "done":
                    used = "true" if evt["data"].get("used_retrieval") else "false"
                    yield "event: done\n"
                    yield f"data: {{\"used_retrieval\": {used}}}\n\n"
            time_end = time.time()
            logger.info(f"聊天请求处理完成，sessionId: {session_id}, fileID: {file_id}, 耗时: {time_end - time_start}秒")
        except Exception as e:
            logger.error(f"聊天请求处理出错，sessionId: {session_id}, fileID: {file_id}, 错误: {e}")    
            yield "event: error\n"
            esc = str(e).replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')
            yield f'data: {{"message":"{esc}"}}\n\n'

    headers = {"Cache-Control": "no-cache, no-transform", "Connection": "keep-alive"}
    return StreamingResponse(gen(), media_type="text/event-stream", headers=headers)

# ---------------- Chat: 清除对话 ----------------
class ClearChatRequest(BaseModel):
    sessionId: Optional[str] = None

@app.post(f"{API_PREFIX}/chat/clear", tags=["Chat"])
async def chat_clear(req: ClearChatRequest):
    sid = (req.sessionId or "default").strip()
    clear_history(sid)
    return {"ok": True, "sessionId": sid, "cleared": True}


# ---------------- PDF: 上传（仅单文件，直接替换） ----------------
# current_pdf = {"fileId": None, "name": None, "pages": 0, "status": "idle", "progress": 0}

@app.post(f"{API_PREFIX}/pdf/upload", tags=["PDF"])
async def pdf_upload(file: UploadFile = File(...), replace: Optional[bool] = True):
    """上传文档"""
    logger.info(f"开始上传文件，文件名: {file.filename}, 替换策略: {replace}")
    try:
        if not file:
            logger.error("缺少文件")
            return JSONResponse(err("NO_FILE", "缺少文件"), status_code=400)
        # 生成新的 fileId（替换策略：上传即替换）
        fid = rid("f")
        # 保存文件在data+file_id路径
        saved = save_upload(fid, await file.read(), file.filename)
    except Exception as e:
        logger.error(f"上传文件出错，文件名: {file.filename}, 错误: {e}")
        return JSONResponse(err("UPLOAD_FAILED", "上传文件失败"), status_code=500)
    # 将新的文件信息替换当前文件
    current_pdf.update({**saved, "status": "idle", "progress": 0})
    citations.clear()
    
    # 将文件信息保存到数据库（异步版本）
    async for db in get_db():
        await add_file_info(db, file.filename, fid, current_pdf["pages"])

    return saved

# ---------------- PDF: 触发解析 ----------------
@app.post(f"{API_PREFIX}/pdf/parse", tags=["PDF"])
async def pdf_parse(payload: Dict[str, Any] = Body(...), bg: BackgroundTasks = None):
    """文档解析"""
    # 获取当前需要解析的文件的file_id
    logger.info(f"解析请求参数: {payload}") 
    try:
        file_id = payload.get("fileId")
        if not file_id:
            logger.error("缺少文件ID")
            return JSONResponse(err("FILE_ID_REQUIRED", "缺少文件ID"), status_code=400)
    except Exception as e:
        logger.error(f"解析请求参数出错，错误: {e}")
        return JSONResponse(err("PARAM_ERROR", "解析请求参数错误"), status_code=400)
    try:
        # 从数据库中获取文件信息
        async for db in get_db():
            file_info = await get_file_by_random_name(db, file_id)
            # 检查文件是否上传
            if not file_info:
                logger.error(f"未找到文件ID为 {file_id} 的文件")
                return JSONResponse(err("FILE_NOT_FOUND", "未找到该文件"), status_code=400)
    except Exception as e:
        logger.error(f"查询文件信息出错，文件ID: {file_id}, 错误: {e}")
        return JSONResponse(err("DB_ERROR", "查询文件信息失败"), status_code=500)

    # 更新当前文档的处理状态为“解析”
    current_pdf["status"] = "parsing"
    current_pdf["progress"] = 5 # 进度加载5

    # 定义同步的PDF处理函数
    def process_pdf():
        try:
            time_start = time.time()
            # 20 → 60 → 100 三阶段进度示意
            current_pdf["progress"] = 20
            # 将原始页面转化为PNG格式，用于前端展示原文档
            render_original_pages(file_id)
            current_pdf["progress"] = 40
            # 使用paddleocr对文档布局进行解析
            docs = unstructured_segments(file_id)
            current_pdf["progress"] = 60
            # 添加框线图，并保存为PNG格式，用于前端展示解析后的文档
            render_parsed_pages_with_boxes(file_id, docs)
            current_pdf["progress"] = 80
            # PDF转MD
            pdf_to_markdown(file_id)
            # run_full_parse_pipeline(file_id)   # 真解析
            current_pdf["progress"] = 100
            current_pdf["status"] = "ready"
            # PDF处理完成后，通过回调函数通知主事件循环更新数据库
            logger.info(f"PDF解析完成，耗时: {time.time() - time_start} 秒")
            return True
        except Exception as e:
            current_pdf["status"] = "error"
            current_pdf["progress"] = 0
            logger.error(f"解析失败: {str(e)}", exc_info=True)
            return False
    
    # 定义异步的数据库更新函数
    async def update_database_after_processing():
        success = await asyncio.to_thread(process_pdf)
        if success:
            try:
                async for db in get_db():
                    await update_file_parse_status(db, file_id)
            except Exception as e:
                logger.error(f"数据库更新失败: {str(e)}", exc_info=True)
    
    # 在后台任务中执行PDF处理和数据库更新
    if bg is not None:
        # 直接添加异步任务到BackgroundTasks
        bg.add_task(update_database_after_processing)
    else:
        # 如果没有BackgroundTasks，直接在当前事件循环中执行
        await update_database_after_processing()

    return {"jobId": rid("j")}

# ---------------- PDF: 状态 ----------------
@app.get(f"{API_PREFIX}/pdf/status", tags=["PDF"])
async def pdf_status(fileId: str = Query(...)):
    """返回文档解析进度"""
    # 判断当前file_id是否存在
    # if not current_pdf["fileId"] or current_pdf["fileId"] != fileId:
    #     return {"status": "idle", "progress": 0}
    if not fileId:
        return JSONResponse(err("FILE_ID_REQUIRED", "缺少文件ID"), status_code=400)
    resp = {"status": current_pdf["status"], "progress": current_pdf["progress"]}
    if current_pdf["status"] == "error":
        resp["errorMsg"] = "解析失败"
    return resp

# ---------------- PDF: 页面图 ----------------
@app.get(f"{API_PREFIX}/pdf/page", tags=["PDF"])
async def pdf_page(
    fileId: str = Query(...),
    page: int = Query(..., ge=1),
    type: str = Query(..., regex="^(original|parsed)$")
):
    """返回原文档图片和解析后的图片"""
    try:
        if not current_pdf["fileId"] or current_pdf["fileId"] != fileId:
            return JSONResponse(status_code=404, content=None)
    except Exception as e:
        logger.error(f"查询文件ID出错，文件ID: {fileId}, 错误: {e}")
        return JSONResponse(err("DB_ERROR", "查询文件ID失败"), status_code=500)
    try:
        if current_pdf["status"] != "ready" and type == "parsed":
            # 未解析就请求 parsed 页，按你的契约可以给 400/403；这里保持 204 更温和
            return JSONResponse(status_code=204, content=None)
    except Exception as e:
        logger.error(f"检查文件状态出错，文件ID: {fileId}, 错误: {e}")
        return JSONResponse(err("DB_ERROR", "检查文件状态失败"), status_code=500)
    try:
        # 获取原文档PNG图片或解析后的PNG图片路径
        base = dir_original_pages(fileId) if type == "original" else dir_parsed_pages(fileId)
        img = base / f"page-{page:04d}.png"
        if not img.exists():
            return JSONResponse(err("PAGE_NOT_FOUND", "页面不存在或未渲染"), status_code=404)
    except Exception as e:
        logger.error(f"获取页面图片路径出错，文件ID: {fileId}, 页面: {page}, 类型: {type}, 错误: {e}")
        return JSONResponse(err("DB_ERROR", "获取页面图片路径失败"), status_code=500)
    return FileResponse(str(img), media_type="image/png")

# ---------------- PDF: 获取所有文件名 ----------------
@app.get(f"{API_PREFIX}/pdf/file_names", tags=["PDF"])
async def get_pdf_files():
    """获取所有上传的文件名和对应的随机名"""
    try:
        async for db in get_db():
            file_info_list = await get_all_file_names(db)
            # 返回包含文件名和随机名的对象数组
            return {"files": [{"file_name": file_info[0], "random_name": file_info[1]} for file_info in file_info_list]}
    except Exception as e:
        logger.error(f"获取所有文件名出错，错误: {e}")
        return JSONResponse(err("DB_ERROR", "获取所有文件名失败"), status_code=500)


# ---------------- PDF: 根据文件名获取文件页面 ----------------
@app.post(f"{API_PREFIX}/pdf/file-by-name", tags=["PDF"])
async def pdf_file_by_name(
    file_id: str = Body(..., embed=True),
    page: int = Query(..., ge=1),
    type: str = Query(..., regex="^(original|parsed)$")
):

    """根据文件id获取对应的文件页面"""
    try:
        # 检查文件是否在current_pdf中
        if not file_id:
            return JSONResponse(status_code=404, content=None)
    except Exception as e:
        logger.error(f"检查文件ID出错，文件ID: {file_id}, 错误: {e}")
        return JSONResponse(err("DB_ERROR", "检查文件ID失败"), status_code=500)
    
    current_pdf["fileId"] = file_id
    current_pdf["status"] = "idle"
    current_pdf["progress"] = 0
    try:
        # 获取原文档PNG图片或解析后的PNG图片路径
        base = dir_original_pages(file_id) if type == "original" else dir_parsed_pages(file_id)
        img = base / f"page-{page:04d}.png"
        if not img.exists():
            return JSONResponse(err("PAGE_NOT_FOUND", "页面不存在或未渲染"), status_code=404)
    except Exception as e:
        logger.error(f"获取页面图片路径出错，文件ID: {file_id}, 页面: {page}, 类型: {type}, 错误: {e}")
        return JSONResponse(err("DB_ERROR", "获取页面图片路径失败"), status_code=500)
    try:
        return FileResponse(str(img), media_type="image/png")
    except Exception as e:
        logger.error(f"返回页面图片出错，文件ID: {file_id}, 页面: {page}, 类型: {type}, 错误: {e}")
        return JSONResponse(err("DB_ERROR", "返回页面图片失败"), status_code=500)

# ---------------- PDF: 获取总页数 ----------------
@app.get(f"{API_PREFIX}/pdf/pages", tags=["PDF"])
async def pdf_pages(fileId: str = Query(...)):
    """获取PDF总页数"""
    try:
        if not fileId:
            return JSONResponse(err("FILE_ID_REQUIRED", "缺少文件ID"), status_code=400)
    except Exception as e:
        logger.error(f"检查文件ID出错，文件ID: {fileId}, 错误: {e}")
        return JSONResponse(err("DB_ERROR", "检查文件ID失败"), status_code=500)
    try:
        async for db in get_db():
            file_info = await get_file_by_random_name(db, fileId)
            if not file_info.file_name:
                return JSONResponse(err("FILE_NOT_FOUND", "文件不存在"), status_code=404)
            return {"pages": file_info.pages}
    except Exception as e:
        logger.error(f"获取文件信息出错，文件ID: {fileId}, 错误: {e}")
        return JSONResponse(err("DB_ERROR", "获取文件信息失败"), status_code=500)

# ---------------- PDF: 引用片段 ----------------
@app.get(f"{API_PREFIX}/pdf/chunk", tags=["PDF"])
async def pdf_chunk(citationId: str = Query(...)):
    """根据引用ID获取引用片段"""
    try:
        if not citationId:
            return JSONResponse(err("CITATION_ID_REQUIRED", "缺少引用ID"), status_code=400)
    except Exception as e:
        logger.error(f"检查引用ID出错，引用ID: {citationId}, 错误: {e}")
        return JSONResponse(err("DB_ERROR", "检查引用ID失败"), status_code=500)
    try:
        ref = citations.get(citationId)
        if not ref:
            return JSONResponse(err("NOT_FOUND", "无该引用"), status_code=404)
        return ref
    except Exception as e:
        logger.error(f"获取引用片段出错，引用ID: {citationId}, 错误: {e}")
        return JSONResponse(err("DB_ERROR", "获取引用片段失败"), status_code=500)

class BuildIndexRequest(BaseModel):
    fileId: str

class SearchRequest(BaseModel):
    fileId: str
    query: str
    k: Optional[int] = 5

@app.post(f"{API_PREFIX}/index/build", tags=["Index"])
async def index_build(req: BuildIndexRequest):
    """构建索引"""
    # 可校验：current_pdf["status"] 应为 ready
    # if not current_pdf["fileId"] or current_pdf["fileId"] != req.fileId:
    #     raise HTTPException(status_code=400, detail="FILE_NOT_FOUND_OR_NOT_CURRENT")
    # if current_pdf["status"] != "ready":
    #     raise HTTPException(status_code=409, detail="NEED_PARSE_FIRST")
    # 根据file_id检查文件是否存在并且是否已经解析
    try:
        if not req.fileId:
            return JSONResponse(err("FILE_ID_REQUIRED", "缺少文件ID"), status_code=400)
    except Exception as e:
        logger.error(f"检查文件ID出错，文件ID: {req.fileId}, 错误: {e}")
        return JSONResponse(err("DB_ERROR", "检查文件ID失败"), status_code=500)
    try:
        async for db in get_db():
            file_info = await get_file_by_random_name(db, req.fileId)
            if not file_info.file_name:
                return JSONResponse(err("FILE_NOT_FOUND", "文件不存在"), status_code=404)
            if file_info.is_parsed != True:
                return JSONResponse(err("NEED_PARSE_FIRST", "文件未解析"), status_code=409)
    except Exception as e:
        logger.error(f"获取文件信息出错，文件ID: {req.fileId}, 错误: {e}")
        return JSONResponse(err("DB_ERROR", "获取文件信息失败"), status_code=500)

    try:
        async for db in get_db():
            file_info = await get_file_by_random_name(db, req.fileId)
            if not file_info.file_name:
                return JSONResponse(err("FILE_NOT_FOUND", "文件不存在"), status_code=404)
            if file_info.is_parsed != True:
                return JSONResponse(err("NEED_PARSE_FIRST", "文件未解析"), status_code=409)
    except Exception as e:
        logger.error(f"检查文件状态出错，文件ID: {req.fileId}, 错误: {e}")
        return JSONResponse(err("DB_ERROR", "检查文件状态失败"), status_code=500)

    try:
        out = build_chroma_index(req.fileId)
    except Exception as e:
        logger.error(f"构建索引出错，文件ID: {req.fileId}, 错误: {e}")
        return JSONResponse(err("INDEX_BUILD_ERROR", "索引构建失败"), status_code=500)
    if not out.get("ok"):
        return JSONResponse(err(out.get("error", "INDEX_BUILD_ERROR"), "索引构建失败"), status_code=500)
        # 更新数据库
    async for db in get_db():
        await update_file_index_status(db, req.fileId)
    return {"ok": True, "chunks": out["chunks"]}

@app.post(f"{API_PREFIX}/index/search", tags=["Index"])
async def index_search(req: SearchRequest):
    """向量数据库查询"""
    try:
        if not req.fileId:
            return JSONResponse(err("FILE_ID_REQUIRED", "缺少文件ID"), status_code=400)
        if not req.query:
            return JSONResponse(err("QUERY_REQUIRED", "缺少查询"), status_code=400)
    except Exception as e:
        logger.error(f"检查查询参数出错，文件ID: {req.fileId}, 查询: {req.query}, 错误: {e}")
        return JSONResponse(err("DB_ERROR", "检查查询参数失败"), status_code=500)
    try:
        citations, context_text = search_chroma(req.fileId, req.query, req.k or 5)
    except Exception as e:
        logger.error(f"查询索引出错，文件ID: {req.fileId}, 查询: {req.query}, 错误: {e}")
        return JSONResponse(err("INDEX_SEARCH_ERROR", "索引查询失败"), status_code=500)

    citations, context_text = search_chroma(req.fileId, req.query, req.k or 5)
    if not citations:
        return JSONResponse(err("INDEX_NOT_FOUND", "请先构建索引"), status_code=400)
    return {"citations": citations, "context_text": context_text}