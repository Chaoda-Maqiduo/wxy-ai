import json
import logging
import uuid
from collections.abc import Awaitable, Callable
from importlib import import_module
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse

from app.schemas.thesis import (
    GenerateRequest,
    GenerateSubmitResponse,
    OutlineRequest,
    OutlineResponse,
    TaskStatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/thesis", tags=["论文生成"])
OUTPUT_ROOT = Path("app/output")


def _status_path(task_id: str) -> Path:
    return OUTPUT_ROOT / task_id / "status.json"


def _write_status(task_id: str, status: str, **extra: Any) -> None:
    path = _status_path(task_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"task_id": task_id, "status": status, **extra}
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _read_status(task_id: str) -> dict[str, Any] | None:
    path = _status_path(task_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _load_generate_outline() -> Callable[[str], Awaitable[str]]:
    try:
        module = import_module("app.services.thesis.outline_service")
        return getattr(module, "generate_outline")
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("论文大纲服务未就绪") from exc


def _load_generate_document() -> Callable[..., Awaitable[Any]]:
    try:
        module = import_module("app.services.thesis")
        return getattr(module, "generate_thesis_document")
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("论文生成服务未就绪") from exc


def _result_value(result: Any, key: str, default: Any) -> Any:
    if isinstance(result, dict):
        return result.get(key, default)
    return getattr(result, key, default)


async def _run_generate(
    task_id: str,
    title: str,
    outline: str,
    cover_kwargs: dict[str, Any] | None = None,
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
            chart_count=_result_value(result, "chart_count", 0),
            ai_image_count=_result_value(result, "ai_image_count", 0),
            fallback_count=_result_value(result, "fallback_count", 0),
            fulltext_char_count=_result_value(result, "fulltext_char_count", 0),
            truncation_warning=_result_value(result, "truncation_warning", False),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("论文生成失败")
        _write_status(task_id, "failed", message=f"生成失败: {exc}")


@router.post("/outline", response_model=OutlineResponse)
async def create_outline(req: OutlineRequest) -> OutlineResponse:
    """根据标题生成论文大纲。"""

    try:
        generate_outline = _load_generate_outline()
        outline = await generate_outline(req.title, getattr(req, "target_word_count", 8000))
    except Exception as exc:  # noqa: BLE001
        logger.exception("大纲生成失败")
        raise HTTPException(status_code=500, detail=f"大纲生成失败: {exc}") from exc

    return OutlineResponse(title=req.title, outline=outline)


@router.post("/generate", response_model=GenerateSubmitResponse)
async def generate_document(
    req: GenerateRequest,
    background_tasks: BackgroundTasks,
) -> GenerateSubmitResponse:
    """提交论文生成任务并立即返回 task_id。"""

    task_id = uuid.uuid4().hex[:12]
    _write_status(task_id, "pending", message="正在生成论文...")
    cover_kwargs = {
        "target_word_count": req.target_word_count,
        "author": req.author,
        "advisor": req.advisor,
        "degree_type": req.degree_type,
        "major": req.major,
        "school": req.school,
        "year_month": req.year_month,
    }
    background_tasks.add_task(_run_generate, task_id, req.title, req.outline, cover_kwargs)
    return GenerateSubmitResponse(task_id=task_id)


@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str) -> TaskStatusResponse:
    """查询任务状态。"""

    data = _read_status(task_id)
    if data is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return TaskStatusResponse(**data)


@router.get("/download/{task_id}")
async def download_document(task_id: str) -> FileResponse:
    """下载生成的 Word 文档。"""

    data = _read_status(task_id)
    if data is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    if data["status"] != "completed":
        raise HTTPException(
            status_code=409,
            detail=f"任务状态为 {data['status']}，无法下载",
        )

    docx_path = data.get("docx_path", "")
    if not docx_path:
        raise HTTPException(status_code=404, detail="文档文件不存在")
    path_obj = Path(docx_path)
    if not path_obj.exists():
        raise HTTPException(status_code=404, detail="文档文件不存在")

    return FileResponse(
        path=str(path_obj),
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        filename=path_obj.name,
    )
