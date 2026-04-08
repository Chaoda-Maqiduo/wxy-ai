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
            "2048",
            "-s",
            "4",
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

        # 纯白底色，避免蓝紫色方块显得突兀
        image = Image.new("RGB", (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(image)
        
        # 绘制浅灰色修饰外框
        border_color = (220, 220, 220)
        draw.rectangle([10, 10, width - 10, height - 10], outline=border_color, width=2)

        # 绘制占位提示文本
        text_content = (
            "[ 文科/概念图占位 ]\n\n"
            f"建议风格: {style}\n\n"
            f"提示词: {description[:150]}...\n\n"
            "(后期可在 Word 中直接替换此图)"
        )

        draw.text(
            (40, height // 3),
            text_content,
            fill=(150, 150, 150),
        )
        image.save(output_path)
        return output_path


# class OpenRouterImageGenerator(ImageGenerator):
#     """通过 OpenRouter 调用文生图能力进行图像渲染。"""
# 
#     def __init__(self, api_key: str, model: str):
#         self.api_key = api_key
#         self.model = model
# 
#     async def generate(
#         self,
#         description: str,
#         style: str,
#         aspect_ratio: str,
#         output_path: str,
#     ) -> str:
#         style_map = {
#             "concept_illustration": "clean flat design, minimalist concept illustration, soft muted colors, white background",
#             "data_visualization": "clean infographic style, flat design data chart, professional color palette, white background",
#             "process_flow": "clean flat illustration of a process flow, minimalist icons, soft pastel colors, white background",
#             "architecture": "clean system architecture diagram, flat design, professional blue-gray palette, white background",
#             "comparison": "clean side-by-side comparison infographic, flat minimalist style, white background",
#         }
#         style_desc = style_map.get(
#             style,
#             "clean flat design illustration, minimalist academic style, muted professional colors, white background"
#         )
# 
#         prompt = (
#             f"Generate a professional academic illustration for a research paper.\n\n"
#             f"Description: {description}\n\n"
#             f"Visual Style: {style_desc}\n\n"
#             f"Aspect Ratio: {aspect_ratio}\n\n"
#             f"CRITICAL RULES:\n"
#             f"- If any text labels appear in the image, they MUST be in Simplified Chinese (简体中文). "
#             f"NEVER use Traditional Chinese characters.\n"
#             f"- Use clean, flat design with generous white space.\n"
#             f"- Avoid dark backgrounds, neon colors, or sci-fi aesthetics.\n"
#             f"- The illustration should look suitable for an academic paper.\n"
#             f"- Use soft, professional colors (light blue, light gray, white, pastel tones)."
#         )
#         
#         import httpx
#         import base64
#         
#         async with httpx.AsyncClient(timeout=60.0) as client:
#             resp = await client.post(
#                 "https://openrouter.ai/api/v1/chat/completions",
#                 headers={
#                     "Authorization": f"Bearer {self.api_key}",
#                     "Content-Type": "application/json",
#                 },
#                 json={
#                     "model": self.model,
#                     "messages": [{"role": "user", "content": prompt}],
#                     "modalities": ["image"]
#                 }
#             )
#             resp.raise_for_status()
#             data = resp.json()
#             
#             images = data.get("choices", [{}])[0].get("message", {}).get("images", [])
#             if not images:
#                 raise RuntimeError(f"OpenRouter returned no images: {data}")
#             
#             url_value = images[0].get("image_url", {}).get("url", "")
#             if not url_value:
#                 raise RuntimeError("OpenRouter returned empty image uniform resource locator.")
#                 
#             if url_value.startswith("data:image"):
#                 _, encoded = url_value.split(",", 1)
#                 image_data = base64.b64decode(encoded)
#                 with open(output_path, "wb") as f:
#                     f.write(image_data)
#             else:
#                 img_resp = await client.get(url_value)
#                 img_resp.raise_for_status()
#                 with open(output_path, "wb") as f:
#                     f.write(img_resp.content)
#                     
#         return output_path

class TwelveAIGenerator(ImageGenerator):
    """通过 12AI API (Google Gemini) 调用文生图能力进行渲染。"""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    async def generate(
        self,
        description: str,
        style: str,
        aspect_ratio: str,
        output_path: str,
    ) -> str:
        style_map = {
            "concept_illustration": "clean flat design, minimalist concept illustration, soft muted colors, white background",
            "data_visualization": "clean infographic style, flat design data chart, professional color palette, white background",
            "process_flow": "clean flat illustration of a process flow, minimalist icons, soft pastel colors, white background",
            "architecture": "clean system architecture diagram, flat design, professional blue-gray palette, white background",
            "comparison": "clean side-by-side comparison infographic, flat minimalist style, white background",
        }
        style_desc = style_map.get(
            style,
            "clean flat design illustration, minimalist academic style, muted professional colors, white background"
        )

        prompt = (
            f"Generate a professional academic illustration for a research paper.\n\n"
            f"Description: {description}\n\n"
            f"Visual Style: {style_desc}\n\n"
            f"CRITICAL RULES:\n"
            f"- If any text labels appear in the image, they MUST be in Simplified Chinese (简体中文). "
            f"NEVER use Traditional Chinese characters.\n"
            f"- Use clean, flat design with generous white space.\n"
            f"- Avoid dark backgrounds, neon colors, or sci-fi aesthetics.\n"
            f"- The illustration should look suitable for an academic paper.\n"
            f"- Use soft, professional colors (light blue, light gray, white, pastel tones)."
        )
        
        # 12AI 明确对 16:9 做了支持，如果遇到特殊或者无法识别的，可以通过 model 参数传入。
        real_aspect = aspect_ratio if aspect_ratio in ["1:1", "3:4", "4:3", "9:16", "16:9"] else "16:9"

        import httpx
        import base64
        
        url = f"https://api.12ai.org/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseModalities": ["IMAGE"],
                "imageConfig": {
                    "aspectRatio": real_aspect,
                    "imageSize": "4K"
                }
            }
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            
            candidates = data.get("candidates", [])
            if not candidates:
                raise RuntimeError(f"12AI API returned no candidates. Full response: {data}")
                
            parts = candidates[0].get("content", {}).get("parts", [])
            base64_data = None
            for part in parts:
                if "inlineData" in part:
                    base64_data = part["inlineData"].get("data")
                    break
            
            if not base64_data:
                raise RuntimeError(f"12AI API returned no image section in parts: {parts}")
                
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(base64_data))
                    
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

        max_retries = 5
        for attempt in range(max_retries):
            try:
                if method == "mermaid":
                    rendered_path = await render_mermaid(
                        placeholder["mermaid_code"], output_path
                    )
                    return index, rendered_path
                elif method == "ai_image":
                    rendered_path = await image_generator.generate(
                        description=placeholder["description"],
                        style=placeholder.get("style", "concept_illustration"),
                        aspect_ratio=placeholder.get("aspect_ratio", "16:9"),
                        output_path=output_path,
                    )
                    return index, rendered_path
                elif method == "fallback":
                    logger.warning("占位符 #%d 为 fallback，跳过渲染", index)
                    return index, None
                else:
                    logger.warning("占位符 #%d 的 render_method 非法: %s", index, method)
                    return index, None

            except Exception as exc:
                if method == "mermaid":
                    # Mermaid 语法错误如果重试也是错的，所以发生异常后直接转交给高智商大模型（ai_image）兜底！
                    logger.warning("占位符 #%d Mermaid 生成代码存在语法错误，自动转大模型生图兜底: %s", index, exc)
                    method = "ai_image"
                    # 这里故意不 return，让循环继续走 ai_image 分支
                else:
                    if attempt < max_retries - 1:
                        logger.warning("占位符 #%d ai_image 出错，重试 %d/%d: %s", index, attempt + 1, max_retries, exc)
                        await asyncio.sleep(2)
                    else:
                        logger.exception("占位符 #%d 彻底失败 (已抢救 %d 次): %s", index, max_retries, exc)
                        return index, None
        return index, None

    pairs = await asyncio.gather(*[_render_one(item) for item in placeholders])
    return dict(pairs)
