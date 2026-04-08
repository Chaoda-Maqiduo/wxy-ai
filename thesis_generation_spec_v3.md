# 论文生成系统 —— 完整改进规格说明书 v3

> 本文档是 v2 的落地修正版。
> 已补齐剩余问题：前置页分页、正文页码从 1 开始、TOC 标题被收录、`_run_generate` 兼容性、`logging` import、参考文献空态提示。
> 供 Claude Code 直接阅读并实现。所有改动均基于现有项目结构，不得重构已有逻辑。

---

## 一、v2 遗留问题修复结论

| 编号 | v2 遗留问题 | v3 修复方式 |
|------|-------------|-------------|
| R1 | 封面/中摘/英摘之间未稳定分页 | 封面页、中文摘要页函数结尾显式 `page_break`；英文摘要页后通过新 section 自动换页 |
| R2 | 致谢、参考文献未稳定分页 | 在 `build_word_document()` 中显式 `document.add_page_break()` 后再追加对应页面 |
| R3 | 正文 section 页码未从 1 开始 | 新增 `_restart_page_numbering(section, start=1)`，为正文 section 写入 `w:pgNumType` |
| R4 | 目录标题可能进入 TOC | `_add_toc_page()` 不再使用 `Heading 1`，改为普通居中标题段落 |
| R5 | `_run_generate` 所谓“三参兼容”不成立 | `_run_generate(task_id, title, outline, cover_kwargs=None)`，第 4 参可选，兼容旧测试调用 |
| R6 | `_refresh_toc_with_libreoffice()` 缺少 `logging` import | `docx_builder.py` 顶部补 `import logging` |
| R7 | 参考文献空态文案误导 | 空态统一改为通用文案，不再暗示一定是 `SERPAPI_KEY` 缺失 |

---

## 二、涉及文件

| 操作 | 文件路径 |
|------|----------|
| 修改 | `Dockerfile` |
| 修改 | `app/config.py` |
| 修改 | `.env.example` |
| 修改 | `app/schemas/thesis.py` |
| 修改 | `app/api/v1/thesis.py` |
| 修改 | `app/services/thesis/__init__.py` |
| 新增 | `app/services/thesis/abstract_service.py` |
| 新增 | `app/services/thesis/reference_service.py` |
| 修改 | `app/services/thesis/docx_builder.py` |
| 新增 | `app/llm/prompts/thesis_abstract_prompt.py` |
| 新增 | `app/llm/prompts/thesis_reference_prompt.py` |

---

## 三、总原则

1. 正文生成仍是主流程，摘要、致谢、参考文献全部属于 `best effort`，失败不能拖垮整篇论文。
2. 不重构现有服务边界，只在现有链路上追加参数和步骤。
3. 参考文献绝不补造字段，只格式化实际拿到的元数据。
4. Word 的页眉、页脚、页码按 `section` 隔离，不靠普通分页符模拟。

---

## 四、Docker 与配置

### 4.1 `Dockerfile`

在现有安装 `nodejs npm` 的 `apt-get` 中追加 `libreoffice-writer`：

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs npm \
    libreoffice-writer \
    && npm install -g @mermaid-js/mermaid-cli \
    && apt-get clean && rm -rf /var/lib/apt/lists/* \
    && addgroup --system app && adduser --system --ingroup app app
```

### 4.2 `.env.example`

保留现有内容，确认存在以下变量：

```env
SERPAPI_KEY=
```

### 4.3 `app/config.py`

1. 在 `_ENV_KEYS` 中追加：

```python
"SERPAPI_KEY",
```

2. 在 `Settings` 中追加：

```python
serpapi_key: str = Field(default="", validation_alias="SERPAPI_KEY")
```

---

## 五、Schema 与 API

### 5.1 `app/schemas/thesis.py`

`GenerateRequest` 新增封面字段，全部给默认值：

```python
class GenerateRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=200, description="论文标题")
    outline: str = Field(..., min_length=50, description="用户确认/修改后的论文大纲")
    author: str = Field(default="作者姓名", description="作者姓名")
    advisor: str = Field(default="指导教师（姓名、职称、单位）", description="指导教师")
    degree_type: str = Field(default="学士", description="学位类别")
    major: str = Field(default="专业名称", description="专业")
    school: str = Field(default="XX大学XX学院", description="学院（系）")
    year_month: str = Field(default="", description="留空则自动填当前年月")
```

`TaskStatusResponse` 新增：

```python
docx_path: str = Field(default="")
```

### 5.2 `app/api/v1/thesis.py`

#### `_run_generate`

为了兼容旧调用和旧 monkeypatch，改成：

```python
async def _run_generate(
    task_id: str,
    title: str,
    outline: str,
    cover_kwargs: dict | None = None,
) -> None:
    """后台执行论文生成流程并更新任务状态。"""
    cover_kwargs = cover_kwargs or {}
    try:
        generate_document = _load_generate_document()
        result = await generate_document(
            task_id=task_id,
            title=title,
            outline=outline,
            **cover_kwargs,
        )
        _write_status(
            task_id,
            "completed",
            message="论文生成完成",
            docx_path=_result_value(result, "docx_path", ""),
            figure_count=_result_value(result, "figure_count", 0),
            mermaid_count=_result_value(result, "mermaid_count", 0),
            ai_image_count=_result_value(result, "ai_image_count", 0),
            fallback_count=_result_value(result, "fallback_count", 0),
            fulltext_char_count=_result_value(result, "fulltext_char_count", 0),
            truncation_warning=_result_value(result, "truncation_warning", False),
        )
    except Exception as exc:
        logger.exception("论文生成失败")
        _write_status(task_id, "failed", message=f"生成失败: {exc}")
```

#### `/generate`

```python
@router.post("/generate", response_model=GenerateSubmitResponse)
async def generate_document(
    req: GenerateRequest,
    background_tasks: BackgroundTasks,
) -> GenerateSubmitResponse:
    task_id = uuid.uuid4().hex[:12]
    _write_status(task_id, "pending", message="正在生成论文...")
    cover_kwargs = {
        "author": req.author,
        "advisor": req.advisor,
        "degree_type": req.degree_type,
        "major": req.major,
        "school": req.school,
        "year_month": req.year_month,
    }
    background_tasks.add_task(_run_generate, task_id, req.title, req.outline, cover_kwargs)
    return GenerateSubmitResponse(task_id=task_id)
```

#### `/download`

下载接口不再 `glob("*.docx")`，改为按 `status.json` 中的 `docx_path` 读取：

```python
@router.get("/download/{task_id}")
async def download_document(task_id: str) -> FileResponse:
    data = _read_status(task_id)
    if data is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    if data["status"] != "completed":
        raise HTTPException(status_code=409, detail=f"任务状态为 {data['status']}，无法下载")

    docx_path = data.get("docx_path", "")
    if not docx_path or not Path(docx_path).exists():
        raise HTTPException(status_code=404, detail="文档文件不存在")

    return FileResponse(
        path=docx_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=Path(docx_path).name,
    )
```

---

## 六、主流程服务

### 6.1 `app/services/thesis/__init__.py`

顶部新增：

```python
import asyncio
import logging
```

保留 `ThesisResult` 不变。

新增 `best effort` 包装：

```python
_logger = logging.getLogger(__name__)


async def _best_effort(coro, default, label: str):
    try:
        return await coro
    except Exception as exc:
        _logger.warning("[best_effort] %s 失败，使用默认值。原因: %s", label, exc)
        return default
```

主流程签名改为：

```python
async def generate_thesis_document(
    task_id: str,
    title: str,
    outline: str,
    author: str = "作者姓名",
    advisor: str = "指导教师",
    degree_type: str = "学士",
    major: str = "专业名称",
    school: str = "XX大学XX学院",
    year_month: str = "",
) -> ThesisResult:
```

正文生成之后，新增：

```python
_default_abstract = {
    "abstract_zh": "",
    "keywords_zh": "",
    "abstract_en": "",
    "keywords_en": "",
}
abstract_data, acknowledgment, references = await asyncio.gather(
    _best_effort(generate_abstracts(full_text), _default_abstract, "摘要生成"),
    _best_effort(generate_acknowledgment(title, advisor), "", "致谢生成"),
    _best_effort(generate_references(title, outline), "", "参考文献生成"),
)
```

调用 `build_word_document()` 时透传：

```python
docx_path = build_word_document(
    full_text=full_text,
    placeholders=placeholders,
    image_paths=image_paths,
    output_path=f"{output_dir}/论文_{safe_title}.docx",
    title=title,
    author=author,
    advisor=advisor,
    degree_type=degree_type,
    major=major,
    school=school,
    year_month=year_month,
    abstract_zh=abstract_data.get("abstract_zh", ""),
    keywords_zh=abstract_data.get("keywords_zh", ""),
    abstract_en=abstract_data.get("abstract_en", ""),
    keywords_en=abstract_data.get("keywords_en", ""),
    acknowledgment=acknowledgment,
    references=references,
)
```

---

## 七、摘要与致谢服务

### 7.1 `app/llm/prompts/thesis_abstract_prompt.py`

新增三个 prompt：

- `ABSTRACT_ZH_PROMPT`
- `ABSTRACT_EN_PROMPT`
- `ACKNOWLEDGMENT_PROMPT`

要求与 v2 一致，不再展开。

### 7.2 `app/services/thesis/abstract_service.py`

关键约束如下：

1. 采样策略必须是：

```python
head = full_text[:3000]
tail = full_text[-2000:] if len(full_text) > 5000 else ""
sample = head + "\n\n[...（中间内容省略）...]\n\n" + tail if tail else head
```

2. 中文摘要关键词解析用 `"关键词："`。
3. 英文摘要关键词解析用 `"Keywords:"`。
4. 致谢生成独立函数：

```python
async def generate_acknowledgment(title: str, advisor: str) -> str: ...
```

---

## 八、参考文献服务

### 8.1 `app/llm/prompts/thesis_reference_prompt.py`

新增：

- `REFERENCE_KEYWORD_PROMPT`
- `REFERENCE_FILTER_PROMPT`

只输出 JSON，不输出 Markdown 代码块。

### 8.2 `app/services/thesis/reference_service.py`

新增主入口：

```python
async def generate_references(title: str, outline: str) -> str:
    """
    SERPAPI_KEY 未配置时返回空字符串。
    失败时返回空字符串，不抛异常给主链路。
    """
```

规则：

1. SerpAPI 只取真实字段：`title`、`link`、`publication_info.summary`、`publication_info.authors`。
2. 不补卷、期、页码。
3. 中英文分开筛选后合并。
4. 最终返回编号后的多行字符串，每行一条。

参考格式允许为“GB/T 7714 近似格式”，例如：

```text
[1] 王某某, 李某某. 论文标题[J]. 刊名. 2023.
[2] Smith J, Brown T. Paper Title[J]. Journal Name. 2022.
```

缺字段则跳过，不得杜撰。

---

## 九、`docx_builder.py` 完整改动

### 9.1 顶部 import

在现有基础上追加：

```python
import datetime
import logging
import re
import shutil
import subprocess
from pathlib import Path
```

并新增：

```python
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt, RGBColor
```

### 9.2 统一 run 字体 helper

在所有函数之前新增：

```python
def _set_run_font(
    run,
    zh_font: str = "宋体",
    en_font: str = "Times New Roman",
    size_pt: float | None = None,
    bold: bool | None = None,
    underline: bool | None = None,
    color_rgb=None,
) -> None:
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.get_or_add_rFonts()
    rFonts.set(qn("w:eastAsia"), zh_font)
    rFonts.set(qn("w:ascii"), en_font)
    rFonts.set(qn("w:hAnsi"), en_font)
    if size_pt is not None:
        run.font.size = Pt(size_pt)
    if bold is not None:
        run.bold = bold
    if underline is not None:
        run.underline = underline
    if color_rgb is not None:
        run.font.color.rgb = color_rgb
```

后续所有 `run._element.rPr.rFonts.set(...)` 一律替换为 `_set_run_font(...)`。

### 9.3 行距 helper

新增：

```python
def _apply_fixed_line_spacing(pf, pt: float = 22) -> None:
    pPr = pf._element.get_or_add_pPr()
    for old in pPr.findall(qn("w:spacing")):
        pPr.remove(old)
    spacing = OxmlElement("w:spacing")
    spacing.set(qn("w:line"), str(int(pt * 20)))
    spacing.set(qn("w:lineRule"), "exact")
    pPr.append(spacing)
```

### 9.4 页码重置 helper

新增：

```python
def _restart_page_numbering(section, start: int = 1) -> None:
    """
    为 section 写入页码起始值。
    正文 section 必须调用一次，确保正文从 1 开始编号。
    """
    sectPr = section._sectPr
    for old in sectPr.findall(qn("w:pgNumType")):
        sectPr.remove(old)
    pg_num = OxmlElement("w:pgNumType")
    pg_num.set(qn("w:start"), str(start))
    sectPr.append(pg_num)
```

### 9.5 `_refresh_toc_with_libreoffice()`

新增函数：

```python
def _refresh_toc_with_libreoffice(docx_path: str) -> None:
    logger = logging.getLogger(__name__)
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        logger.warning("LibreOffice 未找到，TOC 需手动更新")
        return

    output_dir = str(Path(docx_path).parent)
    try:
        result = subprocess.run(
            [
                soffice,
                "--headless",
                "--convert-to", "docx",
                "--outdir", output_dir,
                docx_path,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            logger.warning("LibreOffice TOC 刷新失败: %s", result.stderr.strip())
        else:
            logger.info("LibreOffice TOC 刷新成功: %s", docx_path)
    except Exception as exc:
        logger.warning("LibreOffice 调用异常: %s", exc)
```

### 9.6 `_init_styles()`

`Normal` 样式改为：

```python
normal_style = document.styles["Normal"]
normal_style.font.name = "宋体"
normal_style.font.size = Pt(12)
normal_style.paragraph_format.first_line_indent = Cm(0.74)
normal_style.paragraph_format.space_before = Pt(0)
normal_style.paragraph_format.space_after = Pt(6)
_apply_fixed_line_spacing(normal_style.paragraph_format, pt=22)

rPr = normal_style.element.get_or_add_rPr()
rFonts = rPr.get_or_add_rFonts()
rFonts.set(qn("w:eastAsia"), "宋体")
rFonts.set(qn("w:ascii"), "Times New Roman")
rFonts.set(qn("w:hAnsi"), "Times New Roman")
```

标题样式：

```python
for level, size, bold in heading_config:
    style = document.styles[f"Heading {level}"]
    style.font.name = "黑体"
    style.font.size = Pt(size)
    style.font.bold = bold
    style.font.color.rgb = RGBColor(0, 0, 0)
    style.element.rPr.get_or_add_rFonts().set(qn("w:eastAsia"), "黑体")
    style.paragraph_format.space_before = Pt(12)
    style.paragraph_format.space_after = Pt(6)
    if level == 1:
        style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
```

### 9.7 section helper

新增：

```python
def _clear_header_footer(section) -> None:
    section.header.is_linked_to_previous = False
    section.footer.is_linked_to_previous = False
    for paragraph in section.header.paragraphs:
        paragraph.clear()
    for paragraph in section.footer.paragraphs:
        paragraph.clear()


def _copy_page_layout_from_first(document: Document, section) -> None:
    first = document.sections[0]
    section.page_width = first.page_width
    section.page_height = first.page_height
    section.top_margin = first.top_margin
    section.bottom_margin = first.bottom_margin
    section.left_margin = first.left_margin
    section.right_margin = first.right_margin


def _make_blank_section(document: Document):
    section = document.add_section(WD_SECTION.NEW_PAGE)
    _copy_page_layout_from_first(document, section)
    _clear_header_footer(section)
    return section


def _setup_body_section(document: Document, title: str) -> None:
    section = document.sections[-1]
    _copy_page_layout_from_first(document, section)
    _clear_header_footer(section)
    _restart_page_numbering(section, start=1)

    header = section.header
    p_h = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
    p_h.clear()
    p_h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_h = p_h.add_run(title)
    _set_run_font(run_h, size_pt=10)

    footer = section.footer
    p_f = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    p_f.clear()
    p_f.alignment = WD_ALIGN_PARAGRAPH.CENTER

    run_f = p_f.add_run()
    r = run_f._element

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

    num_run = p_f.add_run("1")
    _set_run_font(num_run, zh_font="Times New Roman", en_font="Times New Roman", size_pt=10)

    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    p_f.add_run()._element.append(fld_end)
```

### 9.8 `_setup_page()`

只负责第一个 section 的版芯：

```python
def _setup_page(document: Document) -> None:
    section = document.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(3)
    section.right_margin = Cm(2.5)
    _clear_header_footer(section)
```

### 9.9 `_add_toc_page()`

目录标题不能再用 `document.add_heading()`。

改为：

```python
def _add_toc_page(document: Document) -> None:
    p_title = document.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.first_line_indent = Pt(0)
    run_title = p_title.add_run("目  录")
    _set_run_font(run_title, zh_font="黑体", size_pt=16, bold=True)

    paragraph = document.add_paragraph()
    paragraph.paragraph_format.first_line_indent = Pt(0)
    run = paragraph.add_run()
    r_element = run._element

    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    fld_begin.set(qn("w:dirty"), "true")
    r_element.append(fld_begin)

    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = ' TOC \\\\o "1-3" \\\\h \\\\z \\\\u '
    r_element.append(instr)

    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    r_element.append(fld_sep)

    hint = paragraph.add_run(" （目录将自动刷新；如未刷新，可在 Word 中右键目录并选择“更新域”） ")
    _set_run_font(hint, size_pt=10, color_rgb=RGBColor(128, 128, 128))

    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    paragraph.add_run()._element.append(fld_end)

    settings = document.settings.element
    update_fields = OxmlElement("w:updateFields")
    update_fields.set(qn("w:val"), "true")
    settings.append(update_fields)
```

注意：这里不再在函数末尾 `add_page_break()`，因为 section 切换本身就是换页。

### 9.10 封面、摘要、致谢、参考文献页面

#### `_add_cover_page()`

保持 v2 的样式，但函数末尾必须追加：

```python
document.add_page_break()
```

原因：Section 1 内部需要把封面和中文摘要拆成两页。

#### `_add_abstract_zh_page()`

保持 v2 的排版，函数末尾必须追加：

```python
document.add_page_break()
```

原因：Section 1 内部需要把中文摘要和英文摘要拆成两页。

#### `_add_abstract_en_page()`

保持 v2 排版，但函数末尾不要加 `page_break()`，下一页由 `Section 2` 的 `add_section(WD_SECTION.NEW_PAGE)` 负责。

#### `_add_acknowledgment_page()`

只负责渲染内容，不负责分页。分页在主流程调用前处理。

#### `_add_references_page()`

只负责渲染内容，不负责分页。分页在主流程调用前处理。

参考文献空态文案统一改为：

```python
"（参考文献未生成，可能因未配置检索服务或检索结果不足）"
```

不要写死成“未配置 SERPAPI_KEY”。

### 9.11 普通正文渲染里的缩进修正

以下位置必须显式取消首行缩进：

1. 表格单元格段落
2. 表标题段落
3. 无序列表段落
4. 有序列表段落
5. 图片 caption 段落

示例：

```python
p.paragraph_format.first_line_indent = Pt(0)
```

### 9.12 `build_word_document()` 最终签名

```python
def build_word_document(
    full_text: str,
    placeholders: list[dict],
    image_paths: dict[int, str | None],
    output_path: str = "app/output/thesis.docx",
    title: str = "论文题目",
    author: str = "作者姓名",
    advisor: str = "指导教师",
    degree_type: str = "学士",
    major: str = "专业名称",
    school: str = "XX大学XX学院",
    year_month: str = "",
    abstract_zh: str = "",
    abstract_en: str = "",
    keywords_zh: str = "",
    keywords_en: str = "",
    acknowledgment: str = "",
    references: str = "",
) -> str:
```

### 9.13 `build_word_document()` 调用顺序

```python
Path(output_path).parent.mkdir(parents=True, exist_ok=True)
document = Document()

_setup_page(document)
_init_styles(document)

# Section 1：封面 + 中文摘要 + 英文摘要
_add_cover_page(document, title, author, advisor, degree_type, major, school, year_month)
_add_abstract_zh_page(document, abstract_zh, keywords_zh)
_add_abstract_en_page(document, abstract_en, keywords_en)

# Section 2：目录
_make_blank_section(document)
_add_toc_page(document)

# Section 3：正文 + 致谢 + 参考文献
_make_blank_section(document)
_setup_body_section(document, title)

# 现有正文 segments 渲染逻辑
...

# 文末页
document.add_page_break()
_add_acknowledgment_page(document, acknowledgment)

document.add_page_break()
_add_references_page(document, references)

document.save(output_path)
_refresh_toc_with_libreoffice(output_path)
return output_path
```

---

## 十、最终文档顺序

```text
Section 1（无页眉、无页脚、无页码）
1. 封面页
2. 中文摘要页
3. 英文摘要页

Section 2（无页眉、无页脚、无页码）
4. 目录页

Section 3（页眉=论文标题；页脚=页码；从 1 开始）
5. 正文各章
6. 致谢页
7. 参考文献页
```

---

## 十一、测试同步要求

### `tests/thesis/test_thesis_api.py`

#### `test_generate_and_status_flow`

为了兼容 `_run_generate(..., cover_kwargs=None)`，建议改成：

```python
async def fake_run_generate(
    task_id: str,
    title: str,
    outline: str,
    cover_kwargs: dict | None = None,
) -> None:
    assert task_id
    assert title
    assert outline
```

这样旧三参调用和新四参调用都兼容。

#### `test_download_completed_returns_docx`

`_write_status()` 时补上：

```python
docx_path=str(docx_path)
```

---

## 十二、实施顺序

1. `docx_builder.py` 先补 `_set_run_font()`、`_apply_fixed_line_spacing()`、`_restart_page_numbering()`。
2. 调整 `_setup_page()`、`_make_blank_section()`、`_setup_body_section()`。
3. 把 `_add_toc_page()` 改成普通标题，避免收录“目 录”。
4. 完成封面、摘要、致谢、参考文献页面函数，并把分页职责理顺。
5. 接入 `abstract_service.py`、`reference_service.py`。
6. 在 `__init__.py` 里接入 `best_effort`。
7. API 状态写入 `docx_path`，下载改按路径。
8. 跑 thesis 相关测试并修正。

---

## 十三、验收标准

1. 生成的 Word 文档中，封面、中摘、英摘、目录、正文、致谢、参考文献顺序稳定正确。
2. 封面、摘要、目录均不显示页眉、页脚、页码。
3. 正文第一页页码显示为 `1`。
4. 目录刷新后不包含“目 录”标题自身。
5. 摘要、致谢、参考文献任一生成失败时，文档仍能正常下载。
6. 参考文献不出现明显臆造的卷、期、页码。
7. 现有 API 路由测试和 schema 测试通过。
