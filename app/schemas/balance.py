from pydantic import BaseModel, Field


class BalanceInfo(BaseModel):
    """DeepSeek 余额明细。"""

    # 货币类型（例如 CNY）。
    currency: str = Field(..., description="币种")
    # 总余额。
    total_balance: str = Field(..., description="总余额")
    # 赠送余额。
    granted_balance: str = Field(..., description="赠送余额")
    # 充值余额。
    topped_up_balance: str = Field(..., description="充值余额")


class BalanceResponse(BaseModel):
    """余额查询响应体。"""

    # 是否余额查询成功。
    is_available: bool = Field(..., description="余额接口可用状态")
    # 余额明细列表。
    balance_infos: list[BalanceInfo] = Field(default_factory=list, description="余额明细")
