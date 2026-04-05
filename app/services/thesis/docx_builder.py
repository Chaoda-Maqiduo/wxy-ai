import re
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, Cm
from docx.oxml.ns import qn

FIGURE_BLOCK_PATTERN = r"<<FIGURE>>\s*.*?\s*<</FIGURE>>"

# ---------- Markdown 表格解析工具 ----------


def _is_table_separator(line: str) -> bool:
    """判断是否为 Markdown 表格的分隔行（如 |---|---|）。"""
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    return all(re.match(r"^[-:]+$", c) for c in cells) if cells else False


def _parse_table_line(line: str) -> list[str]:
    """解析单行表格，返回各列文本。"""
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _collect_table_lines(lines: list[str], start: int) -> tuple[list[list[str]], int]:
    """
    从 start 开始收集连续的 Markdown 表格行。

    返回 (二维数据, 下一个非表格行的索引)。
    分隔行会被跳过，不计入数据。
    """
    rows: list[list[str]] = []
    i = start
    while i < len(lines) and "|" in lines[i]:
        if _is_table_separator(lines[i]):
            i += 1
            continue
        rows.append(_parse_table_line(lines[i]))
        i += 1
    return rows, i


def _add_table(document: Document, rows: list[list[str]]) -> None:
    """将二维数据写入 Word 表格，首行作为表头加粗。"""
    if not rows:
        return

    num_cols = max(len(r) for r in rows)
    table = document.add_table(rows=len(rows), cols=num_cols, style="Table Grid")

    for i, row_data in enumerate(rows):
        for j, cell_text in enumerate(row_data):
            if j >= num_cols:
                continue
            cell = table.rows[i].cells[j]
            cell.text = cell_text
            # 设置单元格内段落字体。
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.name = "宋体"
                    run.font.size = Pt(10.5)  # 五号字
                    run._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
                    if i == 0:
                        run.bold = True


# ---------- 文档样式初始化 ----------


def _init_styles(document: Document) -> None:
    """设置文档默认样式和标题样式。"""
    # 正文样式：宋体 12pt，1.5 倍行距。
    normal_style = document.styles["Normal"]
    normal_style.font.name = "宋体"
    normal_style.font.size = Pt(12)
    normal_style.paragraph_format.line_spacing = 1.5
    # 确保中文字体生效。
    normal_style.element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")

    # 标题样式：黑体，各级字号递减。
    heading_config = [
        (1, 18, True),   # Heading 1: 小二号、加粗
        (2, 16, True),   # Heading 2: 三号、加粗
        (3, 14, True),   # Heading 3: 四号、加粗
    ]
    for level, size, bold in heading_config:
        style = document.styles[f"Heading {level}"]
        style.font.name = "黑体"
        style.font.size = Pt(size)
        style.font.bold = bold
        style.font.color.rgb = None  # 清除默认蓝色，使用黑色
        style.element.rPr.rFonts.set(qn("w:eastAsia"), "黑体")
        # 段前段后间距。
        style.paragraph_format.space_before = Pt(12)
        style.paragraph_format.space_after = Pt(6)


# ---------- 页面设置 ----------


def _setup_page(document: Document) -> None:
    """设置 A4 页面、页边距。"""
    section = document.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(3)
    section.right_margin = Cm(2.5)


# ---------- 主构建函数 ----------


def build_word_document(
    full_text: str,
    placeholders: list[dict],
    image_paths: dict[int, str | None],
    output_path: str = "app/output/thesis.docx",
) -> str:
    """将全文文本与图片合成为 Word 文档。"""

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    document = Document()

    _setup_page(document)
    _init_styles(document)

    segments = re.split(FIGURE_BLOCK_PATTERN, full_text, flags=re.DOTALL)
    placeholder_idx = 0

    for segment in segments:
        lines = [line.strip() for line in segment.strip().split("\n")]
        i = 0
        while i < len(lines):
            line = lines[i]

            # 空行跳过。
            if not line:
                i += 1
                continue

            # 分页标记。
            if line == "---pagebreak---":
                document.add_page_break()
                i += 1
                continue

            # Markdown 表格（以 | 开头的连续行）。
            if line.startswith("|") and "|" in line[1:]:
                rows, next_i = _collect_table_lines(lines, i)
                if rows:
                    _add_table(document, rows)
                i = next_i
                continue

            # 表标题（"表X-X ..." 格式）→ 居中小号。
            if re.match(r"^表\d+-\d+\s", line):
                p = document.add_paragraph(line)
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                if p.runs:
                    p.runs[0].font.size = Pt(10)
                    p.runs[0].font.name = "宋体"
                i += 1
                continue

            # 标题（按 ### > ## > # 顺序匹配）。
            if line.startswith("### "):
                document.add_heading(line[4:], level=3)
            elif line.startswith("## "):
                document.add_heading(line[3:], level=2)
            elif line.startswith("# "):
                document.add_heading(line[2:], level=1)

            # 代码块边界标识，跳过。
            elif line.startswith("```"):
                pass

            # 无序列表。
            elif line.startswith("- "):
                document.add_paragraph(line[2:], style="List Bullet")

            # 有序列表。
            elif re.match(r"^\d+\.\s+", line):
                text = re.sub(r"^\d+\.\s+", "", line)
                document.add_paragraph(text, style="List Number")

            # 普通段落。
            else:
                document.add_paragraph(line)

            i += 1

        # 插入图片占位符。
        if placeholder_idx >= len(placeholders):
            continue

        placeholder = placeholders[placeholder_idx]
        image_path = image_paths.get(placeholder["index"])
        has_image = bool(image_path and Path(image_path).exists())

        if has_image and image_path:
            document.add_picture(image_path, width=Inches(5.5))
            document.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER

        caption = placeholder.get("caption", f"图{placeholder_idx + 1}")
        if not has_image:
            caption += "（图片生成失败）"
        caption_paragraph = document.add_paragraph(caption)
        caption_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if caption_paragraph.runs:
            caption_paragraph.runs[0].font.size = Pt(10)

        placeholder_idx += 1

    document.save(output_path)
    return output_path
