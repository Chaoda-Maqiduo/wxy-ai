from fastapi import APIRouter, HTTPException

from app.schemas.extract import ExtractRequest, ExtractResponse
from app.services.extract_service import extract_core_content

# v1 版本 API 路由集合。
router = APIRouter()


@router.post("/extract", response_model=ExtractResponse)
async def extract_content(payload: ExtractRequest) -> ExtractResponse:
    """接收原文并返回提取结果。"""

    try:
        # 调用服务层执行核心提取逻辑。
        core_content = await extract_core_content(payload.text)
    except Exception as exc:
        # 统一转为 500，避免底层异常直接暴露给客户端。
        raise HTTPException(status_code=500, detail=f"模型调用失败: {exc}") from exc

    if payload.max_length is not None:
        # 若用户指定最大长度，则做截断控制。
        core_content = core_content[: payload.max_length]

    # 组装标准化响应，包含长度统计信息。
    return ExtractResponse(
        core_content=core_content,
        original_length=len(payload.text),
        extracted_length=len(core_content),
    )
