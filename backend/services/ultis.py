import requests
import time
import os
from pathlib import Path
from langchain_community.embeddings import OllamaEmbeddings
from dotenv import load_dotenv
from typing import Dict, Any
import random
import string
from services.log_service import get_logger
logger = get_logger('ultis')
load_dotenv(override=True)

# 复用你已有的数据目录结构
DATA_ROOT = Path("data")

def rid(prefix: str) -> str:
    """生成随机ID"""
    # 随机对上传的文件进行目录命名
    random_name = f"{prefix}_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    logger.info(f"生成随机名称 {random_name} 用于文件 {prefix}")
    return random_name

def now_ts() -> int:
    """获取当前时间戳"""
    timestamp = int(time.time())
    logger.info(f"当前时间戳: {timestamp}")
    return timestamp

def err(code: str, message: str) -> Dict[str, Any]:
    """生成错误响应"""
    logger.error(f"生成错误响应: {code} - {message}")
    return {"error": {"code": code, "message": message}, "requestId": rid("req"), "ts": now_ts()}

def workdir(file_id: str) -> Path:
    """获取工作目录路径"""
    p = DATA_ROOT / file_id
    if not p.exists():
        p.mkdir(parents=True, exist_ok=True)
        logger.info(f"创建工作目录 {p}")
    return p

def markdown_path(file_id: str) -> Path:
    """获取Markdown文件路径"""
    p = workdir(file_id) / "output.md"
    logger.info(f"创建Markdown文件路径: {p}")
    return p

def index_dir(file_id: str) -> Path:
    """获取索引目录路径"""
    p = workdir(file_id) / "index_chroma"
    p.mkdir(parents=True, exist_ok=True)
    logger.info(f"创建索引目录路径: {p}")
    return p

def dir_original_pages(file_id: str) -> Path:
    """获取原始页面目录路径"""
    p = workdir(file_id) / "pages" / "original"
    p.mkdir(parents=True, exist_ok=True); 
    logger.info(f"获取原始页面目录 {p}")
    return p

def dir_parsed_pages(file_id: str) -> Path:
    """获取解析页面目录路径"""
    p = workdir(file_id) / "pages" / "parsed"
    p.mkdir(parents=True, exist_ok=True); 
    logger.info(f"获取解析页面目录 {p}")
    return p

def original_pdf_path(file_id: str) -> Path:
    """获取原始PDF文件路径"""
    p = workdir(file_id) / "original.pdf"
    logger.info(f"获取原始PDF路径 {p}")
    return p

def load_local_embeddings(model_name: str = "bge-m3:latest") -> OllamaEmbeddings: 
    """
    加载本地Ollama嵌入模型
    
    Returns:
        OllamaEmbeddings: 嵌入模型实例
    
    Raises:
        Exception: 当模型加载失败时抛出异常
    """
    if not model_name:
        model_name = os.getenv("EMBED_MODEL_NAME", "bge-m3:latest")
    embed_model_url = os.getenv("EMBED_MODEL_URL", "http://127.0.0.1:11434")
    
    try:
        # 检查Ollama服务是否可用
        response = requests.get(embed_model_url + "/api/tags", timeout=10)
        if response.status_code != 200:
            logger.error(f"Ollama服务返回状态码 {response.status_code}，响应内容: {response.text}")
            raise Exception("Ollama服务不可用，请确保Ollama已启动")
        
        # 正常加载bge-m3模型
        logger.info(f"正在加载嵌入模型 {model_name}，请确保模型已加载到Ollama服务中")
        return OllamaEmbeddings(model=model_name, base_url=embed_model_url)

    except Exception as e:
        logger.error(f"加载嵌入模型 {model_name} 失败: {str(e)}")
        raise Exception(f"加载嵌入模型失败: {str(e)}")