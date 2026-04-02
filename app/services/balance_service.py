import httpx

from app.config import get_settings
from app.schemas.balance import BalanceResponse


class BalanceQueryError(RuntimeError):
    """余额查询业务异常。"""


def _normalize_balance_base_url(base_url: str) -> str:
    """标准化 DeepSeek 基础地址，避免 /v1 影响余额路径。"""

    normalized = base_url.rstrip("/")
    if normalized.endswith("/v1"):
        normalized = normalized[:-3]
    return normalized


async def query_deepseek_balance() -> BalanceResponse:
    """通过 HTTP 请求 DeepSeek 余额接口并返回结构化结果。"""

    settings = get_settings()
    if not settings.deepseek_api_key:
        raise BalanceQueryError("DEEPSEEK_API_KEY is not configured")

    base_url = _normalize_balance_base_url(settings.deepseek_base_url)
    headers = {"Authorization": f"Bearer {settings.deepseek_api_key}"}

    try:
        async with httpx.AsyncClient(base_url=base_url, timeout=10) as client:
            response = await client.get("/user/balance", headers=headers)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise BalanceQueryError(
            f"DeepSeek 余额查询失败，HTTP {exc.response.status_code}"
        ) from exc
    except httpx.HTTPError as exc:
        raise BalanceQueryError(f"DeepSeek 余额查询网络异常: {exc}") from exc

    try:
        data = response.json()
        return BalanceResponse.model_validate(data)
    except Exception as exc:  # noqa: BLE001
        raise BalanceQueryError(f"余额响应解析失败: {exc}") from exc
