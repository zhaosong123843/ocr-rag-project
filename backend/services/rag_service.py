# services/rag_service.py
from __future__ import annotations
import os, asyncio, textwrap
from typing import List, Dict, Any, Tuple, AsyncGenerator
from typing_extensions import TypedDict

from dotenv import load_dotenv
load_dotenv(override=True)

from langchain_deepseek import ChatDeepSeek
from .log_service import get_logger, info, warning, error, log_exception

from collections import defaultdict
_sessions: dict[str, list[dict]] = defaultdict(list)
logger = get_logger('rag_service')

def get_history(session_id: str) -> list[dict]:
    return _sessions.get(session_id, [])

def append_history(session_id: str, role: str, content: str) -> None:
    """添加历史记录"""
    logger.info(f"添加历史记录: {session_id} - {role} - {content}")
    _sessions[session_id].append({"role": role, "content": content})

def clear_history(session_id: str) -> None:
    """清除历史记录"""
    logger.info(f"清除历史记录: {session_id}")
    _sessions.pop(session_id, None)


SYSTEM_INSTRUCTION = (
    "你是多模态 PDF 检索 RAG 聊天机器人，可以围绕多模态文档进行解析、检索和问答。\n"
    "请优先使用当前上传并已解析/索引的资料来回答问题；若未检索到相关内容，则基于通识知识作答，"
    "并**明确说明未找到匹配的课程片段**。\n"
    # "当检索到的上下文中包含与答案直接相关的图片时，请在回答中一并给出这些图片的 Markdown 引用，例如：`![参考图1](图片URL)`。如果没有合适的图片，也就是如果没有检索到图片，或者用户只是让你介绍自己的功能，勿强行添加图片路径。绝不伪造图片或路径。"
)

GRADE_PROMPT = (
    "你是一个判定器，评估检索到的上下文是否有助于回答用户问题。\n"
    "上下文片段：\n{context}\n\n问题：{question}\n"
    "如果上下文对回答该问题有帮助，返回 'yes'；否则返回 'no'。"
)

ANSWER_WITH_CONTEXT = (
    "请使用提供的上下文回答用户的问题。\n\n"
    "问题：\n{question}\n\n上下文：\n{context}\n\n"
    "要求：使用 Markdown；表达简洁但完整；如需给出代码，请使用三引号代码块（```）。\n"
    "作为一名助人为乐的助手，你需要仔细详细的感受用户的需求，并作出详细的回答。如果有图片，请在回答中给出图片的Markdown引用。"
)

ANSWER_NO_CONTEXT = (
    "当前未找到与课程资料直接相关的片段，将基于通识知识作答。\n"
    "问题：\n{question}"
)

async def _get_llm():
    
    try:
        # return init_chat_model(model=MODEL_NAME, model_provider=MODEL_PROVIDER, temperature=TEMPERATURE)
        return ChatDeepSeek(
            # api_key=os.getenv("DEEPSEEK_API_KEY"),
            model=os.getenv("CHAT_MODEL_NAME", "deepseek-chat"),
            temperature=0,
        )
    except Exception as e:
        logger.error(f"初始化语言模型失败，错误: {e}")
        # 抛出异常以便上层处理
        raise

async def answer_stream(
    question: str,
    citations: list[dict],
    context_text: str,
    branch: str,
    session_id: str | None = None
) -> AsyncGenerator[dict, None]:
    """
    以增量事件的形式产出：
      {"type":"citation", "data": {...}}
      {"type":"token", "data": "text chunk"}
      {"type":"done", "data": {"used_retrieval": bool}}
    同时：如果提供了 session_id，会把本轮问答写入内存历史。
    """
    # 先把 citations 全部发给前端（便于角标立刻出现）
    if branch == "with_context" and citations:
        for c in citations:
            yield {"type": "citation", "data": c}

    # 组装"历史 + 本轮提示"
    llm = await _get_llm()
    # 获取历史对话消息
    history_msgs = get_history(session_id) if session_id else []
    # 将检索到的内容添加到对话消息中，作为提示词
    if branch == "with_context" and context_text:
        user_prompt = ANSWER_WITH_CONTEXT.format(question=question, context=context_text)
    else:
        user_prompt = ANSWER_NO_CONTEXT.format(question=question)

    # 完整消息序列：system + 历史多轮 + 当前用户
    msgs = [{"role": "system", "content": SYSTEM_INSTRUCTION}]
    # 将历史逐条附加（保持 role: "user"/"assistant"）
    msgs.extend(history_msgs)
    # 当前用户问题
    msgs.append({"role": "user", "content": user_prompt})

    # 把最终生成的文本拼接出来用于写历史
    final_text_parts: list[str] = []

    # 优先使用流式
    try:
        async for chunk in llm.astream(msgs):
            delta = getattr(chunk, "content", None)
            if delta:
                final_text_parts.append(delta)
                yield {"type": "token", "data": delta}
    except Exception as e:
        logger.error(f"回答生成过程中出错，session_id: {session_id}, 错误: {e}")
        
        # 回退：非流式整段生成
        resp = await llm.ainvoke(msgs)
        text = resp.content or ""
        final_text_parts.append(text)
        for i in range(0, len(text), 20):
            yield {"type": "token", "data": text[i:i+20]}
            await asyncio.sleep(0.005)

    if branch == "with_context" and citations:
        imgs = []
        # 取前 2 张，避免过多（可按需改成 3）
        for c in citations[:1]:
            url = c.get("previewUrl")
            if url:
                # 生成 Markdown 图片行
                imgs.append(f"![参考页 {c.get('rank', '')}]({url})")
        if imgs:
            tail = "\n\n---\n**相关页面预览**\n\n" + "\n\n".join(imgs)
            # 作为一个额外 token 块发给前端
            yield {"type": "token", "data": tail}

    # 将本轮问答写入历史（仅在提供 session_id 时）
    if session_id:
        append_history(session_id, "user", question)
        append_history(session_id, "assistant", "".join(final_text_parts))

    yield {"type": "done", "data": {"used_retrieval": branch == "with_context"}}
