# services/index_service.py
from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Tuple
import os
import requests
import numpy as np
import torch
import time

from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain.docstore.document import Document
from langchain_community.retrievers import BM25Retriever
from langchain_community.vectorstores import Chroma
from services.ultis import load_local_embeddings,markdown_path,index_dir
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from .log_service import get_logger

from dotenv import load_dotenv
load_dotenv(override=True)

logger = get_logger('index_service')

# 复用你已有的数据目录结构
DATA_ROOT = Path("data")

class BGEReranker:
    """BGE重排序器实现，支持从本地路径加载模型"""
    def __init__(self, model_path: str = None, device: str = "cpu"):
        # 默认使用本地路径，如果未提供则使用Hugging Face模型名称
        self.model_path = model_path or os.getenv("RERANKER_PATH", "BAAI/bge-reranker-v2-m3")
        self.device = device
        self.model = None
        self.tokenizer = None
        
    def load_model(self):
        """加载BGE重排序模型（支持本地路径或Hugging Face模型）"""
        try:
            logger.info(f"正在从路径加载重排序模型: {self.model_path}")
            # 尝试从本地路径或Hugging Face加载模型
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_path)
            self.model.to(self.device)
            self.model.eval()
            logger.info("重排序模型加载成功")
            return True
        except Exception as e:
            logger.error(f"加载BGE重排序模型失败: {e}", exc_info=True)
            return False
    
    def rerank(self, query: str, docs: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """对检索结果进行重排序"""
        if self.model is None or self.tokenizer is None:
            if not self.load_model():
                # 如果无法加载模型，返回原始排序结果
                logger.warning("无法加载重排序模型，返回原始排序结果")
                return docs[:top_k]
        
        try:
            # 准备模型输入
            pairs = [[query, doc["text"]] for doc in docs]
            inputs = self.tokenizer(pairs, padding=True, truncation=True, return_tensors='pt', max_length=512)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # 获取模型输出
            with torch.no_grad():
                outputs = self.model(**inputs)
                scores = outputs.logits.squeeze().tolist()
            
            # 为文档添加重排序分数
            for i, doc in enumerate(docs):
                doc["rerank_score"] = scores[i] if isinstance(scores, list) else scores
            
            # 按重排序分数降序排序
            reranked_docs = sorted(docs, key=lambda x: x.get("rerank_score", 0), reverse=True)
            logger.info(f"重排序完成，返回前 {top_k} 个文档，总文档数: {len(docs)}")
            return reranked_docs[:top_k]
        except Exception as e:
            logger.error(f"重排序失败: {e}", exc_info=True)
            return docs[:top_k]

def split_markdown(md_text: str) -> List[Document]:
    # 拆分细节
    try:
        logger.info("开始拆分MD文档")
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
        logger.info(f"MD文档拆分完成，共拆分出 {len(cleaned)} 个段落")
        return cleaned
    except Exception as e:
        logger.error(f"MD文档拆分失败: {e}", exc_info=True)
        return []

def build_chroma_index(file_id: str) -> Dict[str, Any]:
    """构建Chroma向量索引知识库"""
    logger = get_logger('index_service')
    time_start = time.time()
    try:
        # 获取MD文档路径
        md_file = markdown_path(file_id)
        if not md_file.exists():
            logger.error(f"错误：文件不存在 - {md_file}")
            return {"ok": False, "error": "MARKDOWN_NOT_FOUND"}
        md_text = md_file.read_text(encoding="utf-8")
        
        # 拆分MD
        docs = split_markdown(md_text)
        if not docs:
            return {"ok": False, "error": "EMPTY_MD"}
        
        # 导入embedding模型
        embeddings = load_local_embeddings()
        
        # 创建并保存Chroma向量数据库
        chroma_db = Chroma.from_documents(
            documents=docs,
            embedding=embeddings,
            persist_directory=str(index_dir(file_id))
        )
        chroma_db.persist()
        time_end = time.time()
        logger.info(f"成功构建Chroma索引，文件ID: {file_id}，文档数: {len(docs)}，耗时: {time_end - time_start}秒")
        return {"ok": True, "chunks": len(docs)}
    except Exception as e:
        logger.error(f"构建Chroma索引失败，文件ID: {file_id}", e)
        return {"ok": False, "error": f"构建索引失败: {str(e)}"}

def calculate_rrf_scores(vector_results: List[Tuple[Document, float]], 
                         bm25_results: List[Tuple[Document, float]], 
                         k: int = int(os.getenv("RRF_K", 30))) -> List[Dict[str, Any]]:
    """计算向量检索和BM25检索的RRF融合得分"""
    logger = get_logger('index_service')
    logger.info(f"开始计算RRF融合得分，k: {k}，向量检索结果数: {len(vector_results)}，BM25检索结果数: {len(bm25_results)}")
    try:

        # 创建排名映射
        vector_rank_map = {}
        for rank, (doc, score) in enumerate(vector_results):
            vector_rank_map[doc.page_content] = (rank + 1, score)
        
        bm25_rank_map = {}
        for rank, (doc, score) in enumerate(bm25_results):
            bm25_rank_map[doc.page_content] = (rank + 1, score)
        
        # 合并所有文档
        all_docs = {}
        for doc, score in vector_results:
            all_docs[doc.page_content] = doc
        
        for doc, score in bm25_results:
            all_docs[doc.page_content] = doc
        
        # 计算RRF得分
        rrf_scores = []
        for content, doc in all_docs.items():
            vector_rank, vector_score = vector_rank_map.get(content, (k + 1, 0))
            bm25_rank, bm25_score = bm25_rank_map.get(content, (k + 1, 0))
            
            # RRF公式: 1/(k + rank)
            rrf_score = 1.0 / (k + vector_rank) + 1.0 / (k + bm25_rank)
            
            rrf_scores.append({
                "doc": doc,
                "rrf_score": rrf_score,
                "vector_score": vector_score,
                "bm25_score": bm25_score,
                "retrieval_type": "hybrid"
            })
        
        # 按RRF得分降序排序
        rrf_scores.sort(key=lambda x: x["rrf_score"], reverse=True)
        logger.info(f"RRF融合得分计算完成，共 {len(rrf_scores)} 个文档")
        return rrf_scores
    except Exception as e:
        logger.error(f"计算RRF融合得分失败，k: {k}，向量检索结果数: {len(vector_results)}，BM25检索结果数: {len(bm25_results)}", e)
        return []

def search_chroma(file_id: str, query: str, k: int = 5) -> Tuple[List[Dict[str, Any]], str]:
    """
    基于Chroma的混合检索（向量相似度 + BM25）并支持BGE重排序
    
    Args:
        file_id: 文件ID
        query: 查询文本
        k: 返回结果数量
        
    Returns:
        Tuple[List[Dict], str]: (citations, context_text)
        citations: [{citation_id, fileId, rank, page, snippet, score, previewUrl}]
        context_text: 供LLM使用的拼接上下文
    """
    logger = get_logger('index_service')
    try:
        time_start = time.time()
        # 1. 检查索引文件是否存在
        idx = index_dir(file_id)
        if not os.path.exists(idx) or not os.listdir(idx):  # 检查目录是否存在且非空
            logger.warning(f"索引目录不存在或为空: {idx}")
            return [], "(no hits)"
        
        # 2. 加载Chroma向量库和嵌入模型
        embeddings = load_local_embeddings()
        try:
            chroma_db = Chroma(
                persist_directory=str(idx),
                embedding_function=embeddings
            )
            logger.info(f"成功加载Chroma索引，文件ID: {file_id}，文档数: {len(chroma_db.get()['documents'])}")
        except Exception as e:
            logger.error(f"加载Chroma索引失败，文件ID: {file_id}", e)
            return [], "(no hits)"
        
        # 3. 获取向量检索结果
        vector_results = chroma_db.similarity_search_with_score(query, k=k*3)
        logger.info(f"向量检索完成，文件ID: {file_id}，返回 {len(vector_results)} 个文档")
        
        # 4. 混合检索：添加BM25关键词检索
        # 获取所有文档用于构建BM25检索器
        all_docs = chroma_db.get()
        if not all_docs["documents"]:
            return [], "(no hits)"
        
        # 重建Document对象列表
        docs_for_bm25 = []
        for i, content in enumerate(all_docs["documents"]):
            metadata = all_docs["metadatas"][i] if i < len(all_docs["metadatas"]) else {}
            docs_for_bm25.append(Document(page_content=content, metadata=metadata))
        
        # 创建BM25检索器
        bm25_retriever = BM25Retriever.from_documents(docs_for_bm25)
        bm25_retriever.k = k * 3  # 获取更多结果用于融合
        
        # 执行BM25检索
        # 使用invoke方法替代已弃用的get_relevant_documents
        bm25_docs = bm25_retriever.invoke(query)
        # 为BM25结果添加默认分数（BM25不直接提供分数）
        bm25_results = [(doc, 1.0 - (i / len(bm25_docs))) for i, doc in enumerate(bm25_docs)]
        
        # 5. 使用RRF融合向量和BM25结果
        hybrid_results = calculate_rrf_scores(vector_results, bm25_results)
        
        # 6. 准备结果格式
        results = []
        for i, result in enumerate(hybrid_results[:k*2]):  # 获取更多结果用于重排序
            results.append({
                "text": result["doc"].page_content,
                "score": float(result["rrf_score"]),
                "metadata": result["doc"].metadata,
                "retrieval_type": "hybrid",
                "vector_score": float(result["vector_score"]),
                "bm25_score": float(result["bm25_score"])
            })
        
        # 7. 应用BGE重排序
        try:
            # 从环境变量获取设备类型，默认使用CPU
            device = os.getenv("RERANKER_DEVICE", "cpu")
            # 从环境变量获取模型路径（如果有）
            model_path = os.getenv("RERANKER_PATH")
            reranker = BGEReranker(model_path=model_path, device=device)
            results = reranker.rerank(query, results, top_k=k)
            logger.info(f"成功应用重排序，返回前{k}个结果")
        except Exception as e:
            logger.warning(f"重排序失败，但继续使用混合检索结果: {e}")
        
        # 8. 转换为citations和context_text格式
        citations = []
        ctx_snippets = []
        
        for i, result in enumerate(results, start=1):
            doc_content = result["text"]
            snippet_short = doc_content.strip()
            
            # 截断过长的文本片段（500字符限制）
            if len(snippet_short) > 500:
                snippet_short = snippet_short[:500] + "..."
            
            # 获取页码信息
            page = result["metadata"].get("page") or result["metadata"].get("page_number")
            
            # 构建citation
            citations.append({
                "citation_id": f"{file_id}-c{i}",
                "fileId": file_id,
                "rank": i,
                "page": page,
                "snippet": doc_content[:4000],  # 限制最大长度
                "score": result["score"],  # 使用混合检索的最终分数
                "previewUrl": f"/api/v1/pdf/page?fileId={file_id}&page={(page or 1)}&type=original"
            })
            
            # 构建上下文片段
            ctx_snippets.append(f"[{i}] {snippet_short}")
        
        # 生成context_text
        context_text = "\n\n".join(ctx_snippets) if ctx_snippets else "(no hits)"
        time_end = time.time()
        logger.debug(f"生成上下文文本: {context_text[:10]}...，耗时: {time_end - time_start}秒")  # 打印前50个字符
        return citations, context_text
    
    except Exception as e:
        logger.error(f"检索失败，文件ID: {file_id}", e)
        return [], "(no hits)"


if __name__ == "__main__":
    # 示例：测试新的混合检索和重排序功能
    file_id = 'f_strpjlh0'
    # query = '电梯振动舒适度评估标准'
    # build_chroma_index(file_id)
    # 构建索引示例（实际使用时需要有对应的markdown文件）
    # build_result = build_chroma_index(file_id)
    # print("构建索引结果:", build_result)
    
    # try:
    #     # 执行检索示例
    #     citations, context_text = search_chroma(
    #         file_id=file_id, 
    #         query=query, 
    #         k=5
    #     )
        
    #     print(f"\n检索到 {len(citations)} 个相关文档:")
    #     for i, citation in enumerate(citations, 1):
    #         print(f"\n引用 {i}:")
    #         print(f"  Citation ID: {citation['citation_id']}")
    #         print(f"  文件ID: {citation['fileId']}")
    #         print(f"  排名: {citation['rank']}")
    #         print(f"  页码: {citation['page']}")
    #         print(f"  分数: {citation['score']:.4f}")
    #         print(f"  预览URL: {citation['previewUrl']}")
    #         print(f"  内容摘要: {citation['snippet'][:100]}...")
        
    #     print(f"\n上下文文本:\n{context_text}")
    # except Exception as e:
    #     print(f"测试失败: {str(e)}")
