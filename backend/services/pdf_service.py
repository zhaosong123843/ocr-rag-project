# services/pdf_service.py
from __future__ import annotations
import os, io, math, json
from pathlib import Path
from typing import Dict, Any, List
import fitz
import time
from PIL import Image
import matplotlib
matplotlib.use("Agg")  # 服务器无头
import matplotlib.pyplot as plt
import matplotlib.patches as patches

from langchain_unstructured import UnstructuredLoader
from unstructured.partition.pdf import partition_pdf
from html2text import html2text
from .log_service import get_logger, info, warning, error, log_exception
from .ultis import workdir, dir_original_pages, original_pdf_path,markdown_path,dir_parsed_pages
# 初始化logger
logger = get_logger('pdf_service')

# 统一的根目录：每个 fileId 一个子目录
DATA_ROOT = Path("data")

def images_dir(file_id: str) -> Path:
    # 文件中图片的保存路径
    p = workdir(file_id) / "images"
    p.mkdir(parents=True, exist_ok=True); 
    logger.info(f"创建图片目录 {p}")
    return p

def save_upload(file_id: str, upload_bytes: bytes, filename: str) -> Dict[str, Any]:
    """保存上传的 PDF，并返回页数"""
    try:
        logger.info(f"保存上传的PDF文件: {filename}, file_id: {file_id}")
        # 根据文件的id保存
        pdf_path = original_pdf_path(file_id)
        # 将文件的二进制写入到文件中，实现保存
        pdf_path.write_bytes(upload_bytes)
        # 获取文件的页数
        with fitz.open(pdf_path) as doc:
            pages = doc.page_count
    except Exception as e:
        logger.error(f"保存上传的PDF文件失败: {filename}, file_id: {file_id}, 错误: {e}")
        raise e
    logger.info(f"PDF保存成功，页数: {pages}")
    return {"fileId": file_id, "name": filename, "pages": pages}

def render_original_pages(file_id: str, dpi: int = 144):
    """把原始 PDF 渲染为 PNG，存到 pages/original/"""
    logger.info(f"开始渲染原始PDF页面，file_id: {file_id}, dpi: {dpi}")
    try:
        # 获取原文档路径
        pdf_path = original_pdf_path(file_id)
        # 创建PNG的输出路径
        out_dir = dir_original_pages(file_id)
        # 读取原文档并进行遍历
        with fitz.open(pdf_path) as doc:
            for idx, page in enumerate(doc, start=1):
                try:
                    # 比例缩放
                    mat = fitz.Matrix(dpi/72, dpi/72)
                    # 使用指定的变换矩阵将 PDF 页面渲染为像素图
                    pix = page.get_pixmap(matrix=mat)
                    
                    # 处理颜色空间
                    if pix.alpha and pix.n > 3:
                        # 如果有alpha通道，先移除
                        pix = fitz.Pixmap(pix, 0)
                    # 确保转换为RGB
                    if pix.colorspace.n != fitz.csRGB.n:
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    
                    # 保存图片
                    (out_dir / f"page-{idx:04d}.png").write_bytes(pix.tobytes("png"))
                except Exception as e:
                    logger.warning(f"渲染页面 {idx} 失败: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"渲染原始PDF页面失败: {file_id}, 错误: {e}")
        raise e
    logger.info(f"原始PDF页面渲染完成，file_id: {file_id}")

def _plot_boxes_to_ax(ax, pix, segments):
    """
    在 matplotlib 轴上绘制解析后的文本区域边界框
    """
    try:
        # 根据不同的元素类型设置不同的框线颜色
        category_to_color = {
            "Title": "orchid",
            "Image": "forestgreen",
            "Table": "tomato",
            # "List": "gold",
            # "Header": "purple",
            # "Footer": "blue",
            # "Caption": "orange"
        }
        # 遍历所有文本区域并绘制边界框
        categories = set()
        for seg in segments:
            # 原始坐标点
            points = seg["coordinates"]["points"]
            # 原始布局的宽度和高度
            lw = seg["coordinates"]["layout_width"]
            lh = seg["coordinates"]["layout_height"]
            # 转换公式：x_image = x_original * (pix.width / layout_width)
            scaled = [(x * pix.width / lw, y * pix.height / lh) for x, y in points]
            # 获取颜色
            category = seg.get("category", "Text")
            color = category_to_color.get(category, "deepskyblue")
            categories.add(category)
            # 绘制多边形边界框
            poly = patches.Polygon(scaled, linewidth=1, edgecolor=color, facecolor="none")
            ax.add_patch(poly)
            # 添加文本标签
            ax.text(
                scaled[0][0], scaled[0][1], category,
                fontsize=8, color=color, transform=ax.transData
            )
    except Exception as e:
        logger.error(f"绘制解析页面边界框失败，错误: {e}")
        raise
    # 创建图例，显示所有检测到的类别
    legend_handles = []
    # 先添加默认的 "Text" 类别（如果有）
    if "Text" in categories:
        legend_handles.append(patches.Patch(color="deepskyblue", label="Text"))
    # 然后添加其他自定义类别的图例
    for cat, color in category_to_color.items():
        if cat in categories:
            legend_handles.append(patches.Patch(color=color, label=cat))
    # 只有当有图例时才添加
    if legend_handles:
        ax.legend(handles=legend_handles, loc="upper right", fontsize=8)

def render_parsed_pages_with_boxes(file_id: str, docs_local: List[Dict[str, Any]], dpi: int = 144):
    """
    根据 UnstructuredLoader 的 metadata（含坐标）在原图上叠框，输出到 pages/parsed/
    """
    logger.info(f"开始渲染解析页面边界框，file_id: {file_id}, dpi: {dpi}")
    try:
        # 获取原档路径
        pdf_path = original_pdf_path(file_id)
        # 叠框PDF输出路径
        out_dir = dir_parsed_pages(file_id)
        # 加载原文档
        with fitz.open(pdf_path) as doc:
            # 预聚合：按 page_number 分组 segments，按页码分组元数据
            segments_by_page: Dict[int, List[Dict[str, Any]]] = {}
            for d in docs_local:
                meta = d.metadata if hasattr(d, "metadata") else d["metadata"]
                pno = meta.get("page_number")
                if pno is None: continue
                segments_by_page.setdefault(pno, []).append(meta)

            for page_number in range(1, doc.page_count + 1):
                try:
                    page = doc.load_page(page_number - 1)
                    # 原文档缩放
                    mat = fitz.Matrix(dpi/72, dpi/72)
                    pix = page.get_pixmap(matrix=mat)
                    
                    # 处理颜色空间
                    if pix.alpha and pix.n > 3:
                        # 如果有alpha通道，先移除
                        pix = fitz.Pixmap(pix, 0)
                    # 确保转换为RGB
                    if pix.colorspace.n != fitz.csRGB.n:
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    
                    # 转换为 PIL Image 对象用于 matplotlib 显示
                    pil = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    # 创建 matplotlib 图形并显示原始图像
                    fig, ax = plt.subplots(1, figsize=(10, 10))
                    ax.imshow(pil)
                    ax.axis("off")
                    # 绘制文本区域框
                    _plot_boxes_to_ax(ax, pix, segments_by_page.get(page_number, []))
                    fig.tight_layout()
                    # 保存并清理fig
                    fig.savefig(out_dir / f"page-{page_number:04d}.png", bbox_inches="tight", pad_inches=0)
                    plt.close(fig)
                    logger.info(f"解析页面 {page_number} 完成，file_id: {file_id}")
                except Exception as e:
                    logger.warning(f"渲染解析页面 {page_number} 失败: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"渲染解析页面整体失败，file_id: {file_id}, 错误: {e}")
        raise e

def unstructured_segments(file_id: str) -> List[Any]:
    """用 UnstructuredLoader 产生高分辨率布局段"""
    try:
        logger.info(f"开始使用UnstructuredLoader解析PDF，file_id: {file_id}")
        # 获取原文档路径
        pdf_path = str(original_pdf_path(file_id))
        # 使用paddleocr进行解析
        loader = UnstructuredLoader(
            file_path=pdf_path,
            strategy="hi_res",
            infer_table_structure=True,
            ocr_languages="chi_sim+eng",    
        ocr_engine="paddleocr",  # 如果装不上可换成 'auto' 或注释掉
        )
        out = []

        for d in loader.lazy_load():
            out.append(d)
        logger.info(f"UnstructuredLoader解析完成，file_id: {file_id}, 生成段数: {len(out)}")
    except Exception as e:
        logger.error(f"UnstructuredLoader解析失败，file_id: {file_id}, 错误: {e}")
        raise
    return out

def pdf_to_markdown(file_id: str):
    """将PDF文档转为MD"""
    logger.info(f"开始PDF转Markdown，file_id: {file_id}")
    # 获取源文件路径
    pdf_path = str(original_pdf_path(file_id))
    # MD文件输出路径
    out_md = markdown_path(file_id)
    # 文件中图片的保存路径
    img_dir = images_dir(file_id)
    # 使用paddleocr内置方法进行转化
    try:
        elements = partition_pdf(
            filename=pdf_path,
            infer_table_structure=True,
            strategy="hi_res",
            ocr_languages="chi_sim+eng",
            ocr_engine="paddleocr"  # 同上
        )
        logger.info(f"PDF解析完成，file_id: {file_id}, 元素数量: {len(elements)}")

        # 提取图片
        image_map = {}
        # 加载原文档
        with fitz.open(pdf_path) as doc:
            # 遍历每一页
            for page_num, page in enumerate(doc, start=1):
                image_map[page_num] = []
                # 遍历当前页的所有图片
                for img_index, img in enumerate(page.get_images(full=True), start=1):
                    xref = img[0]
                    pix = fitz.Pixmap(doc, xref)
                    img_path = img_dir / f"page{page_num}_img{img_index}.png"
                    # 确保转换为支持的RGB颜色空间
                    try:
                        # 尝试直接保存
                        pix.save(str(img_path))
                    except ValueError:
                        # 如果颜色空间不支持，则转换为RGB
                        if pix.alpha and pix.n > 3:
                            # 如果有alpha通道，先移除
                            pix = fitz.Pixmap(pix, 0)
                        # 转换为RGB
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                        # 再次尝试保存
                        pix.save(str(img_path))
                    image_map[page_num].append(img_path.name)  # 只保存文件名

        # 构建 Markdown 内容
        md_lines: List[str] = []
        inserted_images = set()
        for el in elements:
            cat = getattr(el, "category", None)
            text = (getattr(el, "text", "") or "").strip()
            meta = getattr(el, "metadata", None)
            page_num = getattr(meta, "page_number", None) if meta else None

            if not text and cat != "Image":
                continue

            # 标题：转换为 # 标题
            if cat == "Title" and text.startswith("- "):
                md_lines.append(text + "\n")
            elif cat == "Title":
                md_lines.append(f"# {text}\n")
            # 头部：转换为 ## 子标题
            elif cat in ["Header", "Subheader"]:
                md_lines.append(f"## {text}\n")
            # 表格：优先使用 HTML 表格，转换为 Markdown 表格
            elif cat == "Table":
                html = getattr(meta, "text_as_html", None) if meta else None
                if html:
                    md_lines.append(html2text(html) + "\n")
                else:
                    md_lines.append((text or "") + "\n")
            # 图片：插入 Markdown 图片链接 ![Image](./images/filename.png)
            elif cat == "Image" and page_num:
                for name in image_map.get(page_num, []):
                    if (page_num, name) not in inserted_images:
                        md_lines.append(f"![Image](./images/{name})\n")
                        inserted_images.add((page_num, name))
            else:
                # 普通文本：直接添加
                md_lines.append(text + "\n")

        # 保存MD文件
        out_md.write_text("\n".join(md_lines), encoding="utf-8")
        logger.info(f"Markdown文件保存成功，file_id: {file_id}, 路径: {out_md}")
        return {"markdown": out_md.name, "images_dir": "images"}
    except Exception as e:
        logger.error(f"PDF转Markdown失败，file_id: {file_id}, 错误: {e}", exc_info=True)
        raise

# def run_full_parse_pipeline(file_id: str) -> Dict[str, Any]:
#     """
#     完整流程：原始页图渲染 → Unstructured 布局段 → 叠框图 → 输出 Markdown
#     返回用于 /status 的统计或元信息
#     """
#     logger.info(f"开始完整解析流程，file_id: {file_id}")
#     try:
#         # 将原始页面转化为PNG格式，用于前端展示原文档
#         render_original_pages(file_id)
#         # 使用paddleocr对文档布局进行解析
#         docs = unstructured_segments(file_id)
#         # 添加框线图，并保存为PNG格式，用于前端展示解析后的文档
#         render_parsed_pages_with_boxes(file_id, docs)
#         # PDF转MD
#         md_info = pdf_to_markdown(file_id)
#         logger.info(f"完整解析流程完成，file_id: {file_id}")
#         return {"md": md_info["markdown"]}
#     except Exception as e:
#         error('pdf_service', f"完整解析流程失败", e)
#         raise
