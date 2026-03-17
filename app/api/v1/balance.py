from fastapi import APIRouter, HTTPException

from app.schemas.balance import BalanceResponse
from app.services.balance_service import BalanceQueryError, query_deepseek_balance

# v1 余额查询路由。
router = APIRouter()


@router.get("/balance", response_model=BalanceResponse)
async def get_balance() -> BalanceResponse:
    """查询 DeepSeek 账户余额。"""

    try:
        return await query_deepseek_balance()
    except BalanceQueryError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"余额查询失败: {exc}") from exc

