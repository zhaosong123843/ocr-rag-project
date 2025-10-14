# services/pdf_service.py
from __future__ import annotations
import os, io, math, json
from pathlib import Path
from typing import Dict, Any, List
import fitz
from PIL import Image
import matplotlib
matplotlib.use("Agg")  # 服务器无头
import matplotlib.pyplot as plt
import matplotlib.patches as patches

from langchain_unstructured import UnstructuredLoader
from unstructured.partition.pdf import partition_pdf
from html2text import html2text

# 统一的根目录：每个 fileId 一个子目录
DATA_ROOT = Path("data")

def workdir(file_id: str) -> Path:
    # 文件保存路径
    d = DATA_ROOT / file_id
    d.mkdir(parents=True, exist_ok=True)
    return d

def dir_original_pages(file_id: str) -> Path:
    p = workdir(file_id) / "pages" / "original"
    p.mkdir(parents=True, exist_ok=True); return p

def dir_parsed_pages(file_id: str) -> Path:
    p = workdir(file_id) / "pages" / "parsed"
    p.mkdir(parents=True, exist_ok=True); return p

def original_pdf_path(file_id: str) -> Path:
    # 保存源文件
    return workdir(file_id) / "original.pdf"

def markdown_output(file_id: str) -> Path:
    return workdir(file_id) / "output.md"

def images_dir(file_id: str) -> Path:
    # 文件中图片的保存路径
    p = workdir(file_id) / "images"
    p.mkdir(parents=True, exist_ok=True); return p

def save_upload(file_id: str, upload_bytes: bytes, filename: str) -> Dict[str, Any]:
    """保存上传的 PDF，并返回页数"""
    # 根据文件的id保存
    pdf_path = original_pdf_path(file_id)
    # 将文件的二进制写入到文件中，实现保存
    pdf_path.write_bytes(upload_bytes)
    # 获取文件的页数
    with fitz.open(pdf_path) as doc:
        pages = doc.page_count
    return {"fileId": file_id, "name": filename, "pages": pages}

def render_original_pages(file_id: str, dpi: int = 144):
    """把原始 PDF 渲染为 PNG，存到 pages/original/"""
    # 获取原文档路径
    pdf_path = original_pdf_path(file_id)
    # 创建PNG的输出路径
    out_dir = dir_original_pages(file_id)
    # 读取原文档并进行遍历
    with fitz.open(pdf_path) as doc:
        for idx, page in enumerate(doc, start=1):
            # 比例缩放
            mat = fitz.Matrix(dpi/72, dpi/72)
            # 使用指定的变换矩阵将 PDF 页面渲染为像素图
            pix = page.get_pixmap(matrix=mat)
            # 保存图片
            (out_dir / f"page-{idx:04d}.png").write_bytes(pix.tobytes("png"))

def _plot_boxes_to_ax(ax, pix, segments):
    # 根据不容的标题等级设置不同的框线
    category_to_color = {
        "Title": "orchid",
        "Image": "forestgreen",
        "Table": "tomato",
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
        color = category_to_color.get(seg.get("category"), "deepskyblue")
        categories.add(seg.get("category", "Text"))
        # 绘制多边形边界框
        poly = patches.Polygon(scaled, linewidth=1, edgecolor=color, facecolor="none")
        ax.add_patch(poly)

    # 始终包含默认的 "Text" 类别，创建图例
    legend_handles = [patches.Patch(color="deepskyblue", label="Text")]
    for cat, color in category_to_color.items():
        if cat in categories:
            legend_handles.append(patches.Patch(color=color, label=cat))
    ax.legend(handles=legend_handles, loc="upper right")

def render_parsed_pages_with_boxes(file_id: str, docs_local: List[Dict[str, Any]], dpi: int = 144):
    """
    根据 UnstructuredLoader 的 metadata（含坐标）在原图上叠框，输出到 pages/parsed/
    """
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
            page = doc.load_page(page_number - 1)
            # 原文档缩放
            mat = fitz.Matrix(dpi/72, dpi/72)
            pix = page.get_pixmap(matrix=mat)
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

def unstructured_segments(file_id: str) -> List[Any]:
    """用 UnstructuredLoader 产生高分辨率布局段"""
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
    return out

def pdf_to_markdown(file_id: str):
    """将PDF文档转为MD"""
    # 获取源文件路径
    pdf_path = str(original_pdf_path(file_id))
    # MD文件输出路径
    out_md = markdown_output(file_id)
    # 文件中图片的保存路径
    img_dir = images_dir(file_id)
    # 使用paddleocr内置方法进行转化
    elements = partition_pdf(
        filename=pdf_path,
        infer_table_structure=True,
        strategy="hi_res",
        ocr_languages="chi_sim+eng",
        ocr_engine="paddleocr"  # 同上
    )

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
                # 如果颜色空间复杂（pix.n >= 5）则转换为 RGB
                if pix.n < 5:
                    pix.save(str(img_path))
                else:
                    # 压缩图片RGB
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                    # 保存图片
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
    return {"markdown": out_md.name, "images_dir": "images"}

def run_full_parse_pipeline(file_id: str) -> Dict[str, Any]:
    """
    完整流程：原始页图渲染 → Unstructured 布局段 → 叠框图 → 输出 Markdown
    返回用于 /status 的统计或元信息
    """
    # 将原始页面转化为PNG格式，用于前端展示原文档
    render_original_pages(file_id)
    # 使用paddleocr对文档布局进行解析
    docs = unstructured_segments(file_id)
    # 添加框线图，并保存为PNG格式，用于前端展示解析后的文档
    render_parsed_pages_with_boxes(file_id, docs)
    # PDF转MD
    md_info = pdf_to_markdown(file_id)
    return {"md": md_info["markdown"]}
