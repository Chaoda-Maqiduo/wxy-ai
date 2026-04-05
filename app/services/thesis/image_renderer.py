import asyncio
import logging
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

logger = logging.getLogger(__name__)


async def render_mermaid(mermaid_code: str, output_path: str) -> str:
    """将 Mermaid 代码渲染为 PNG。"""

    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".mmd", delete=False
    ) as temp_file:
        temp_file.write(mermaid_code)
        mmd_path = temp_file.name

    try:
        proc = await asyncio.create_subprocess_exec(
            "mmdc",
            "-i",
            mmd_path,
            "-o",
            output_path,
            "-b",
            "white",
            "-w",
            "1024",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
    finally:
        Path(mmd_path).unlink(missing_ok=True)

    if proc.returncode != 0:
        raise RuntimeError(
            f"Mermaid 渲染失败 (exit {proc.returncode}): {stderr.decode().strip()}"
        )

    return output_path


class ImageGenerator(ABC):
    """AI 生图模型抽象接口。"""

    @abstractmethod
    async def generate(
        self,
        description: str,
        style: str,
        aspect_ratio: str,
        output_path: str,
    ) -> str:
        """生成图片并保存到 output_path，返回实际路径。"""


class PlaceholderImageGenerator(ImageGenerator):
    """占位实现：生成包含描述文字的本地占位图。"""

    async def generate(
        self,
        description: str,
        style: str,
        aspect_ratio: str,
        output_path: str,
    ) -> str:
        from PIL import Image, ImageDraw

        ratios = {
            "16:9": (1024, 576),
            "4:3": (1024, 768),
            "1:1": (1024, 1024),
        }
        width, height = ratios.get(aspect_ratio, (1024, 576))

        image = Image.new("RGB", (width, height), color=(230, 240, 250))
        draw = ImageDraw.Draw(image)
        draw.text(
            (40, height // 3),
            (
                "[AI Image Placeholder]\n\n"
                f"Style: {style}\n\n"
                f"{description[:120]}..."
            ),
            fill=(80, 80, 80),
        )
        image.save(output_path)
        return output_path


async def render_all_figures(
    placeholders: list[dict],
    image_generator: ImageGenerator,
    output_dir: str = "app/output/images",
) -> dict[int, str | None]:
    """并发渲染所有占位符，返回 {index: path_or_none}。"""

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    async def _render_one(placeholder: dict) -> tuple[int, str | None]:
        index = placeholder["index"]
        output_path = f"{output_dir}/fig_{index}.png"
        method = placeholder.get("render_method")

        try:
            if method == "mermaid":
                rendered_path = await render_mermaid(
                    placeholder["mermaid_code"], output_path
                )
                return index, rendered_path
            if method == "ai_image":
                rendered_path = await image_generator.generate(
                    description=placeholder["description"],
                    style=placeholder.get("style", "concept_illustration"),
                    aspect_ratio=placeholder.get("aspect_ratio", "16:9"),
                    output_path=output_path,
                )
                return index, rendered_path
            if method == "fallback":
                logger.warning("占位符 #%d 为 fallback，跳过渲染", index)
                return index, None

            logger.warning("占位符 #%d 的 render_method 非法: %s", index, method)
            return index, None
        except Exception as exc:
            # 单图失败不影响整篇论文输出。
            logger.exception("占位符 #%d 渲染失败: %s", index, exc)
            return index, None

    pairs = await asyncio.gather(*[_render_one(item) for item in placeholders])
    return dict(pairs)
