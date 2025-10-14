# services/index_service.py
from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Tuple
import os
import faiss
import requests
import numpy as np

from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain.docstore.document import Document
from langchain_community.vectorstores import FAISS

from dotenv import load_dotenv
load_dotenv(override=True)

# 复用你已有的数据目录结构
DATA_ROOT = Path("data")

class IVFIndex:
    """基于FAISS倒排索引的检索实现"""
    def __init__(self, vectors: np.ndarray = None, nlist: int = 100):
        self.vectors = vectors
        self.nlist = nlist
        self.index = None
        self.dimension = None
        
        if vectors is not None:
            self.dimension = vectors.shape[1]
            # 创建倒排索引
            quantizer = faiss.IndexFlatL2(self.dimension)
            self.index = faiss.IndexIVFFlat(quantizer, self.dimension, nlist)
            
            # 训练索引
            self.index.train(vectors)
            # 添加向量到索引
            self.index.add(vectors)
    
    def search(self, query_vector: np.ndarray, top_k: int = 10) -> List[Tuple[int, float]]:
        """倒排索引搜索"""
        if self.index is None:
            return []
        
        # 确保query_vector是正确形状
        if len(query_vector.shape) == 1:
            query_vector = query_vector.reshape(1, -1)
        
        # 搜索
        scores, indices = self.index.search(query_vector, top_k)
        
        # 转换结果为(文档ID, 相似度得分)格式
        # FAISS返回的是距离，我们需要转换为相似度得分
        results = []
        for i, (doc_id, distance) in enumerate(zip(indices[0], scores[0])):
            if doc_id != -1:  # 排除无效结果
                # 将距离转换为相似度得分（距离越小，相似度越高）
                similarity_score = 1.0 / (1.0 + distance) if distance > 0 else 1.0
                results.append((int(doc_id), float(similarity_score)))
        
        return results
    
    def search_with_docs(self, query_vector: np.ndarray, faiss_hits: List[Tuple[Document, float]], top_k: int = 10) -> List[Dict[str, Any]]:
        """IVF索引检索并返回文档内容"""
        if self.index is None:
            return []
        
        # 执行IVF检索
        ivf_scores = self.search(query_vector, top_k)
        
        # 获取IVF检索到的文档内容
        ivf_results = []
        for doc_id, ivf_score in ivf_scores:
            if doc_id < len(faiss_hits):
                doc, _ = faiss_hits[doc_id]
                ivf_results.append({
                    "doc": doc,
                    "ivf_score": ivf_score,
                    "doc_id": doc_id
                })
        
        return ivf_results
    
    def save(self, file_path: Path):
        """保存索引到文件"""
        if self.index is not None:
            faiss.write_index(self.index, str(file_path))
    
    @classmethod
    def load(cls, file_path: Path) -> 'IVFIndex':
        """从文件加载索引"""
        index = cls()
        if file_path.exists():
            index.index = faiss.read_index(str(file_path))
            index.dimension = index.index.d
        return index

def workdir(file_id: str) -> Path:
    """获取工作目录路径"""
    p = DATA_ROOT / file_id
    p.mkdir(parents=True, exist_ok=True)
    return p

def markdown_path(file_id: str) -> Path:
    """获取Markdown文件路径"""
    return workdir(file_id) / "output.md"

def index_dir(file_id: str) -> Path:
    """获取索引目录路径"""
    p = workdir(file_id) / "index_faiss"
    p.mkdir(parents=True, exist_ok=True)
    return p

def ivf_index_path(file_id: str) -> Path:
    """获取IVF索引文件路径"""
    return index_dir(file_id) / "ivf_index.faiss"


def load_local_embeddings() -> OllamaEmbeddings: 
    """
    加载本地Ollama嵌入模型
    
    Returns:
        OllamaEmbeddings: 嵌入模型实例
    
    Raises:
        Exception: 当模型加载失败时抛出异常
    """
    try:
        # 检查Ollama服务是否可用
        response = requests.get("http://127.0.0.1:11434/api/tags", timeout=10)
        if response.status_code != 200:
            raise Exception("Ollama服务不可用，请确保Ollama已启动")
        
        # 正常加载bge-m3模型
        return OllamaEmbeddings(model="bge-m3:latest", base_url="http://127.0.0.1:11434")

    except Exception as e:
        raise Exception(f"加载嵌入模型失败: {str(e)}")


def split_markdown(md_text: str) -> List[Document]:
    # 拆分细节
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        # 需要更细可以加 ("###", "Header 3")
    ]
    # 创建拆分器
    splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    docs = splitter.split_text(md_text)
    # 可加一点清洗
    cleaned: List[Document] = []
    for d in docs:
        txt = (d.page_content or "").strip()
        if not txt:
            continue
        # 限制太长的段落，避免向量化出错
        if len(txt) > 8000:
            txt = txt[:8000]
        cleaned.append(Document(page_content=txt, metadata=d.metadata))
    return cleaned

def build_faiss_index(file_id: str) -> Dict[str, Any]:
    """构建索引向量知识库"""
    # 获取MD文档路径
    md_file = markdown_path(file_id)
    if not md_file.exists():
        return {"ok": False, "error": "MARKDOWN_NOT_FOUND"}
    md_text = md_file.read_text(encoding="utf-8")
    # 拆分MD
    docs = split_markdown(md_text)
    if not docs:
        return {"ok": False, "error": "EMPTY_MD"}
    
    # 导入embedding模型
    embeddings = load_local_embeddings()
    # 存入faiss向量数据
    vs = FAISS.from_documents(docs, embedding=embeddings)
    vs.save_local(str(index_dir(file_id)))
    
    # 构建IVF索引
    # 获取所有文档的向量表示
    embeddings_list = []
    for doc in docs:
        # 使用embedding模型获取文档向量
        doc_vector = embeddings.embed_query(doc.page_content)
        embeddings_list.append(doc_vector)
    
    # 转换为numpy数组
    embeddings_array = np.array(embeddings_list)
    
    # 创建IVF索引
    ivf_index = IVFIndex(embeddings_array, nlist=min(100, len(docs)))
    
    # 保存IVF索引
    ivf_index.save(ivf_index_path(file_id))

    return {"ok": True, "chunks": len(docs)}

def calculate_rrf_scores(faiss_results: List[Tuple[Document, float]], 
                         ivf_results: List[Dict[str, Any]], 
                         k: int = 60) -> List[Tuple[Document, float]]:
    """计算RRF融合得分"""
    # 创建排名映射
    faiss_rank_map = {}
    for rank, (doc, _) in enumerate(faiss_results):
        faiss_rank_map[doc.page_content] = rank + 1
    
    ivf_rank_map = {}
    for rank, result in enumerate(ivf_results):
        ivf_rank_map[result["doc"].page_content] = rank + 1
    
    # 合并所有文档
    all_docs = {}
    for doc, faiss_score in faiss_results:
        all_docs[doc.page_content] = doc
    
    for result in ivf_results:
        doc = result["doc"]
        all_docs[doc.page_content] = doc
    
    # 计算RRF得分
    rrf_scores = []
    for content, doc in all_docs.items():
        faiss_rank = faiss_rank_map.get(content, k + 1)
        ivf_rank = ivf_rank_map.get(content, k + 1)
        
        # RRF公式: 1/(k + rank)
        rrf_score = 1.0 / (k + faiss_rank) + 1.0 / (k + ivf_rank)
        rrf_scores.append((doc, rrf_score))
    
    # 按RRF得分降序排序
    rrf_scores.sort(key=lambda x: x[1], reverse=True)
    
    return rrf_scores




def search_faiss(file_id: str, query: str, k: int = 5, use_hybrid: bool = True) -> Dict[str, Any]:
    """
    基于FAISS的混合检索
    
    Args:
        file_id: 文件ID
        query: 查询文本
        k: 返回结果数量
        use_hybrid: 是否使用混合检索（FAISS + IVF）
    
    Returns:
        检索结果字典
    """
    try:
        # 1. 检查索引文件是否存在
        idx = index_dir(file_id)
        if not (idx / "index.faiss").exists():
            return {"ok": False, "error": "INDEX_NOT_FOUND"}
        
        # 2. 加载FAISS向量库
        embeddings = load_local_embeddings()
        vs = FAISS.load_local(str(idx), embeddings, allow_dangerous_deserialization=True)
        
        # 3. 获取FAISS检索结果
        faiss_hits = vs.similarity_search_with_score(query, k=k*3)
        
        # 如果不需要混合检索，直接返回FAISS结果
        if not use_hybrid:
            # 返回FAISS结果
            results = []
            for i, (doc, score) in enumerate(faiss_hits[:k]):
                results.append({
                    "text": doc.page_content,
                    "score": float(score),
                    "metadata": doc.metadata,
                    "retrieval_type": "FAISS"
                })
            
            return {"ok": True, "results": results}
        
        # 4. IVF索引检索（混合检索模式）
        ivf_results = []
        if ivf_index_path(file_id).exists():
            try:
                ivf_index = IVFIndex.load(ivf_index_path(file_id))
                # 检查索引是否成功加载
                if ivf_index.index is None:
                    print("IVF索引加载失败：索引为空")
                    ivf_results = []
                else:
                    # 获取查询向量
                    query_vector = embeddings.embed_query(query)
                    query_vector_np = np.array(query_vector).astype('float32')
                    
                    # 使用IVFIndex类的search_with_docs方法进行检索
                    ivf_results = ivf_index.search_with_docs(query_vector_np, faiss_hits, k*3)
                    print(f"IVF检索到 {len(ivf_results)} 个结果")
            except Exception as e:
                ivf_results = []
        
        # 5. 使用独立的RRF计算函数
        rrf_scores = calculate_rrf_scores(faiss_hits, ivf_results, k)
        print(f"RRF:{ivf_results}")
        # 返回RRF融合结果
        results = []
        for i, (doc, rrf_score) in enumerate(rrf_scores[:k]):
            results.append({
                "text": doc.page_content,
                "score": float(rrf_score),
                "metadata": doc.metadata,
                "retrieval_type": "FAISS + IVF"
            })
        
        return {"ok": True, "results": results}
    
    except Exception as e:
        print(f"检索失败: {e}")
        return {"ok": False, "error": f"检索失败: {str(e)}"}

if __name__ == "__main__":

    from pathlib import Path

    path = Path(r"D:\LEARN\pythonFile\ocr_rag\data\f_6a4t8zka\index_faiss")
    print("📁 目录内容:", os.listdir(path))
    print("📄 目标文件:", path / "index.faiss")

    file_id = 'f_6a4t8zka'
    query = '电梯振动舒适度评估标准'
    
    if not (path / "index.faiss").exists():
        print({"ok": False, "error": "INDEX_NOT_FOUND"})
    else:
        print("✅ index.faiss 文件存在")

    # 获取embedding模型
    embeddings = load_local_embeddings()
    vs = FAISS.load_local(str(path), embeddings, allow_dangerous_deserialization=True)
    # 相似度得分计算
    hits = vs.similarity_search_with_score(query, k=5)
    results = []
    # 返回相关文档
    for doc, score in hits:
        results.append({
            "text": doc.page_content,
            "score": float(score),
            "metadata": doc.metadata,
        })

    print(results)
