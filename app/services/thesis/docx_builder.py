import re
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, Cm
from docx.oxml import OxmlElement
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


def _add_markdown_text_to_paragraph(paragraph, text: str, is_header: bool = False, is_table: bool = False):
    """解析 Markdown 内联加粗并添加到段落中"""
    # 移除转码过程或大模型常常加上的 '~' 约等于号或误标的点
    text = text.replace("~", "")
    
    parts = re.split(r'(\*\*.*?\*\*)', text)
    for part in parts:
        if not part:
            continue
        if part.startswith('**') and part.endswith('**') and len(part) >= 4:
            run = paragraph.add_run(part[2:-2])
            run.bold = True
        else:
            run = paragraph.add_run(part)
            if is_header:
                run.bold = True
        
        # 强制指定中文字体，确保不发生回退
        run.font.name = "宋体"
        run._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
        # 如果是表格内容，强行缩小为五号字
        if is_table:
            run.font.size = Pt(10.5)


def _add_table(document: Document, rows: list[list[str]]) -> None:
    """将二维数据写入 Word 表格，处理内联加粗，首行作为表头加粗。"""
    if not rows:
        return

    num_cols = max(len(r) for r in rows)
    table = document.add_table(rows=len(rows), cols=num_cols, style="Table Grid")

    for i, row_data in enumerate(rows):
        for j, cell_text in enumerate(row_data):
            if j >= num_cols:
                continue
            cell = table.rows[i].cells[j]
            # Word 新建单元格默认自带一个空段落
            p = cell.paragraphs[0] if cell.paragraphs else cell.add_paragraph()
            _add_markdown_text_to_paragraph(p, cell_text, is_header=(i == 0), is_table=True)


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
    """设置 A4 页面、页边距、页脚页码。"""
    section = document.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(3)
    section.right_margin = Cm(2.5)

    # 页脚：居中页码。
    footer = section.footer
    footer.is_linked_to_previous = False
    paragraph = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # 插入 PAGE 域代码：Word 会自动替换为当前页码。
    run = paragraph.add_run()
    r = run._element

    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    r.append(fld_begin)

    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    r.append(instr)

    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    r.append(fld_sep)

    # 占位文本（Word 打开后自动替换为真实页码）。
    num_run = paragraph.add_run("1")
    num_run.font.size = Pt(10)
    num_run.font.name = "Times New Roman"

    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    r2 = paragraph.add_run()._element
    r2.append(fld_end)


# ---------- 主构建函数 ----------


def _add_toc_page(document: Document) -> None:
    """
    在文档中插入目录页（Table of Contents）。

    通过 Word 域代码（Field Code）插入 TOC 指令。
    用户在 Word 中打开文档后，右键目录选择"更新域"即可
    生成带页码的完整目录；也可按 Ctrl+A, F9 全文刷新。
    """
    # 目录标题。
    toc_title = document.add_heading("目  录", level=1)
    toc_title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # 创建段落放置 TOC 域代码。
    paragraph = document.add_paragraph()
    run = paragraph.add_run()
    r_element = run._element

    # <w:fldChar w:fldCharType="begin" w:dirty="true"/>
    # 设置 dirty="true" 可以让这部分域代码在文件打开时强制重算（部分 Word 版本会静默更新）
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    fld_begin.set(qn("w:dirty"), "true")
    r_element.append(fld_begin)

    # <w:instrText> TOC \o "1-3" \h \z \u </w:instrText>
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = ' TOC \\o "1-3" \\h \\z \\u '
    r_element.append(instr)

    # <w:fldChar w:fldCharType="separate"/>
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    r_element.append(fld_sep)

    # 占位文本：对部分无法自动刷新目录的软件（如WPS）进行提示
    hint = paragraph.add_run(" （目录正在底层生成中，请在此处右键并选择“更新域”即可获取最新排版目录） ")
    hint.font.size = Pt(10)
    from docx.shared import RGBColor
    hint.font.color.rgb = RGBColor(128, 128, 128)

    # <w:fldChar w:fldCharType="end"/>
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    r_end = paragraph.add_run()._element
    r_end.append(fld_end)

    # 注入文档级别的全局设置：强制在打开时询问是否更新所有域
    settings = document.settings.element
    update_fields = OxmlElement('w:updateFields')
    update_fields.set(qn('w:val'), 'true')
    settings.append(update_fields)

    # 目录后分页。
    document.add_page_break()





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

    # 在正文之前插入目录页。
    _add_toc_page(document)

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
                p = document.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                _add_markdown_text_to_paragraph(p, line)
                for run in p.runs:
                    run.font.size = Pt(10)
                    run.font.name = "宋体"
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
                p = document.add_paragraph(style="List Bullet")
                _add_markdown_text_to_paragraph(p, line[2:])

            # 有序列表。
            elif re.match(r"^\d+\.\s+", line):
                text = re.sub(r"^\d+\.\s+", "", line)
                p = document.add_paragraph(style="List Number")
                _add_markdown_text_to_paragraph(p, text)

            # 普通段落。
            else:
                p = document.add_paragraph()
                _add_markdown_text_to_paragraph(p, line)

            i += 1

        # 插入图片占位符。
        if placeholder_idx >= len(placeholders):
            continue

        placeholder = placeholders[placeholder_idx]
        image_path = image_paths.get(placeholder["index"])
        has_image = bool(image_path and Path(image_path).exists())

        if has_image and image_path:
            # 页面可用宽度 = 21cm - 3cm左 - 2.5cm右 = 15.5cm
            document.add_picture(image_path, width=Cm(15.5))
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
