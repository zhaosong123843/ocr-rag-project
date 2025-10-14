from fastapi import FastAPI, UploadFile, File, Query, Body
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import asyncio, time, os, random, string
from typing import Optional, Dict, Any, List
from fastapi import HTTPException
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
from services.index_service import build_faiss_index, search_faiss
from services.rag_service import retrieve, answer_stream, clear_history
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

# ---------------- 内存态存储（教学Mock） ----------------
current_pdf: Dict[str, Any] = {
    "fileId": None,
    "name": None,
    "pages": 0,
    "status": "idle",      # idle | parsing | ready | error
    "progress": 0
}
citations: Dict[str, Dict[str, Any]] = {}   # citationId -> { fileId, page, snippet, bbox, previewUrl }

# ---------------- 工具函数 ----------------
def rid(prefix: str) -> str:
    # 随机对上传的文件进行目录命名
    return f"{prefix}_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8))

def now_ts() -> int:
    return int(time.time())

def err(code: str, message: str) -> Dict[str, Any]:
    return {"error": {"code": code, "message": message}, "requestId": rid("req"), "ts": now_ts()}


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
                    # 获取检索到的内容
                    citations, context_text = await retrieve(question, file_id)
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

        except Exception as e:
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
    if not file:
        return JSONResponse(err("NO_FILE", "缺少文件"), status_code=400)
    # 生成新的 fileId（替换策略：上传即替换）
    fid = rid("f")
    # 保存文件在data+file_id路径
    saved = save_upload(fid, await file.read(), file.filename)
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
    print(payload)
    file_id = payload.get("fileId")
    if not file_id:
        return JSONResponse(err("FILE_ID_REQUIRED", "缺少文件ID"), status_code=400)
    
    # 从数据库中获取文件信息
    async for db in get_db():
        file_info = await get_file_by_random_name(db, file_id)
        # 检查文件是否上传
        if not file_info:
            return JSONResponse(err("FILE_NOT_FOUND", "未找到该文件"), status_code=400)

    # 更新当前文档的处理状态为“解析”
    current_pdf["status"] = "parsing"
    current_pdf["progress"] = 5 # 进度加载5

    # 定义同步的PDF处理函数
    def process_pdf():
        try:
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
            return True
        except Exception as e:
            current_pdf["status"] = "error"
            current_pdf["progress"] = 0
            print("Parse error:", e)
            return False
    
    # 定义异步的数据库更新函数
    async def update_database_after_processing():
        success = await asyncio.to_thread(process_pdf)
        if success:
            try:
                async for db in get_db():
                    await update_file_parse_status(db, file_id)
            except Exception as e:
                print("Database update error:", e)
    
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
    if not current_pdf["fileId"] or current_pdf["fileId"] != fileId:
        return JSONResponse(status_code=404, content=None)

    if current_pdf["status"] != "ready" and type == "parsed":
        # 未解析就请求 parsed 页，按你的契约可以给 400/403；这里保持 204 更温和
        return JSONResponse(status_code=204, content=None)
    # 获取原文档PNG图片或解析后的PNG图片路径
    base = dir_original_pages(fileId) if type == "original" else dir_parsed_pages(fileId)
    img = base / f"page-{page:04d}.png"
    if not img.exists():
        return JSONResponse(err("PAGE_NOT_FOUND", "页面不存在或未渲染"), status_code=404)
    return FileResponse(str(img), media_type="image/png")

# ---------------- PDF: 获取所有文件名 ----------------
@app.get(f"{API_PREFIX}/pdf/file_names", tags=["PDF"])
async def get_pdf_files():
    """获取所有上传的文件名和对应的随机名"""
    # 获取所有文件名和随机名（异步版本）
    async for db in get_db():
        file_info_list = await get_all_file_names(db)
        # 返回包含文件名和随机名的对象数组
        return {"files": [{"file_name": file_info[0], "random_name": file_info[1]} for file_info in file_info_list]}

# ---------------- PDF: 图片文件 ----------------
# @app.get(f"{API_PREFIX}/pdf/images", tags=["PDF"])
# async def pdf_images(
#     fileId: str = Query(...),
#     imagePath: str = Query(...)
# ):
#     """获取PDF解析后的图片文件"""
#     if not current_pdf["fileId"] or current_pdf["fileId"] != fileId:
#         return JSONResponse(status_code=404, content=None)

#     # 构建图片文件的完整路径
#     from services.pdf_service import images_dir
#     image_file = images_dir(fileId) / imagePath
    
#     if not image_file.exists():
#         return JSONResponse(err("IMAGE_NOT_FOUND", "图片文件不存在"), status_code=404)
    
#     # 检查文件是否在images目录内（安全考虑）
#     try:
#         image_file.resolve().relative_to(images_dir(fileId).resolve())
#     except ValueError:
#         return JSONResponse(err("INVALID_PATH", "无效的图片路径"), status_code=400)
    
#     return FileResponse(str(image_file), media_type="image/png")

# ---------------- PDF: 根据文件名获取文件页面 ----------------
@app.post(f"{API_PREFIX}/pdf/file-by-name", tags=["PDF"])
async def pdf_file_by_name(
    file_id: str = Body(..., embed=True),
    page: int = Query(..., ge=1),
    type: str = Query(..., regex="^(original|parsed)$")
):

    """根据文件id获取对应的文件页面"""

    # 检查文件是否在current_pdf中
    if not file_id:
        return JSONResponse(status_code=404, content=None)
    
    current_pdf["fileId"] = file_id
    current_pdf["status"] = "idle"
    current_pdf["progress"] = 0

    # 获取原文档PNG图片或解析后的PNG图片路径
    base = dir_original_pages(file_id) if type == "original" else dir_parsed_pages(file_id)
    img = base / f"page-{page:04d}.png"
    if not img.exists():
        return JSONResponse(err("PAGE_NOT_FOUND", "页面不存在或未渲染"), status_code=404)
    
    return FileResponse(str(img), media_type="image/png")

# ---------------- PDF: 获取总页数 ----------------
@app.get(f"{API_PREFIX}/pdf/pages", tags=["PDF"])
async def pdf_pages(fileId: str = Query(...)):
    """获取PDF总页数"""
    if not fileId:
        return JSONResponse(err("FILE_ID_REQUIRED", "缺少文件ID"), status_code=400)
    async for db in get_db():
        file_info = await get_file_by_random_name(db, fileId)
        if not file_info.file_name:
            return JSONResponse(err("FILE_NOT_FOUND", "文件不存在"), status_code=404)
        return {"pages": file_info.pages}

# ---------------- PDF: 引用片段 ----------------
@app.get(f"{API_PREFIX}/pdf/chunk", tags=["PDF"])
async def pdf_chunk(citationId: str = Query(...)):
    ref = citations.get(citationId)
    if not ref:
        return JSONResponse(err("NOT_FOUND", "无该引用"), status_code=404)
    return ref

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
    async for db in get_db():
        file_info = await get_file_by_random_name(db, req.fileId)
        if not file_info.file_name:
            return JSONResponse(err("FILE_NOT_FOUND", "文件不存在"), status_code=404)
        if file_info.is_parsed != True:
            return JSONResponse(err("NEED_PARSE_FIRST", "文件未解析"), status_code=409)

    out = build_faiss_index(req.fileId)
    if not out.get("ok"):
        return JSONResponse(err(out.get("error", "INDEX_BUILD_ERROR"), "索引构建失败"), status_code=500)
        # 更新数据库
    async for db in get_db():
        await update_file_index_status(db, req.fileId)
    return {"ok": True, "chunks": out["chunks"]}

@app.post(f"{API_PREFIX}/index/search", tags=["Index"])
async def index_search(req: SearchRequest):
    """向量数据库查询"""
    out = search_faiss(req.fileId, req.query, req.k or 5)
    if not out.get("ok"):
        code = out.get("error", "INDEX_NOT_FOUND")
        return JSONResponse(err(code, "请先构建索引"), status_code=400)
    return out