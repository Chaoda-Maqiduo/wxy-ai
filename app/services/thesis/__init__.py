import logging
from dataclasses import dataclass

from app.services.thesis.docx_builder import build_word_document
from app.services.thesis.fulltext_service import generate_fulltext
from app.services.thesis.image_renderer import (
    PlaceholderImageGenerator,
    render_all_figures,
)
from app.services.thesis.outline_service import generate_outline
from app.services.thesis.placeholder import (
    extract_figure_placeholders,
    split_by_render_method,
)
from app.services.thesis.utils import sanitize_filename

logger = logging.getLogger(__name__)


@dataclass
class ThesisResult:
    """论文生成结果摘要。"""

    task_id: str
    docx_path: str
    figure_count: int = 0
    mermaid_count: int = 0
    ai_image_count: int = 0
    fallback_count: int = 0
    fulltext_char_count: int = 0
    truncation_warning: bool = False


async def generate_thesis_document(
    task_id: str,
    title: str,
    outline: str,
) -> ThesisResult:
    """
    论文生成主流程（阶段② + ②.5 + ②.7 + ③）。

    task_id 由 API 层传入，确保状态文件和产物目录一致。
    """

    output_dir = f"app/output/{task_id}"
    safe_title = sanitize_filename(title)

    full_text = await generate_fulltext(outline)

    char_count = len(full_text)
    truncation_warning = False
    if char_count < 7000:
        logger.warning("全文仅 %d 字，可能存在截断", char_count)
        truncation_warning = True

    placeholders = extract_figure_placeholders(full_text)
    mermaid_list, ai_image_list, fallback_list = split_by_render_method(placeholders)

    image_generator = PlaceholderImageGenerator()
    image_paths = await render_all_figures(
        placeholders=placeholders,
        image_generator=image_generator,
        output_dir=f"{output_dir}/images",
    )

    docx_path = build_word_document(
        full_text=full_text,
        placeholders=placeholders,
        image_paths=image_paths,
        output_path=f"{output_dir}/论文_{safe_title}.docx",
    )

    return ThesisResult(
        task_id=task_id,
        docx_path=docx_path,
        figure_count=len(placeholders),
        mermaid_count=len(mermaid_list),
        ai_image_count=len(ai_image_list),
        fallback_count=len(fallback_list),
        fulltext_char_count=char_count,
        truncation_warning=truncation_warning,
    )


__all__ = [
    "ThesisResult",
    "build_word_document",
    "extract_figure_placeholders",
    "generate_fulltext",
    "generate_outline",
    "generate_thesis_document",
    "render_all_figures",
    "sanitize_filename",
    "split_by_render_method",
]
