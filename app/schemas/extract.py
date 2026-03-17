from pydantic import BaseModel, Field


class ExtractRequest(BaseModel):
    """提取接口请求体。"""

    # 待处理原文，至少 1 个字符。
    text: str = Field(..., min_length=1, description="待提取核心内容的原始文本")
    # 可选输出上限，用于控制返回文本长度。
    max_length: int | None = Field(
        default=None,
        gt=0,
        description="可选。期望返回结果的最大字符数",
    )


class ExtractResponse(BaseModel):
    """提取接口响应体。"""

    # 模型提取后的核心文本。
    core_content: str = Field(..., description="提取后的核心内容")
    # 原文字符长度。
    original_length: int = Field(..., ge=0, description="原始文本长度")
    # 提取后字符长度（可能受 max_length 影响）。
    extracted_length: int = Field(..., ge=0, description="提取结果长度")
