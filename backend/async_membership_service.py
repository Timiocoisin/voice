"""异步会员与钻石相关的业务服务层。

本模块封装了与数据库交互的 VIP / 钻石业务逻辑，供 FastAPI 路由调用：
- 查询用户 VIP 信息与到期时间
- 查询/刷新钻石余额与用户基础信息
- 执行购买会员（扣减钻石并更新有效期）

所有方法都是异步的。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Tuple

from backend.database.async_database_manager import AsyncDatabaseManager

PERMANENT_VIP_YEAR = 2099


@dataclass
class VipInfo:
    """用户 VIP 信息的简单数据结构。"""

    is_vip: bool
    vip_expiry: Optional[datetime]
    diamonds: int


class AsyncMembershipService:
    """封装 VIP / 钻石相关业务逻辑的异步服务类。"""

    def __init__(self, db_manager: Optional[AsyncDatabaseManager] = None) -> None:
        self.db_manager = db_manager or AsyncDatabaseManager()

    # ---------- 基础查询 ----------

    async def get_vip_info(self, user_id: int) -> Optional[VipInfo]:
        """获取用户当前 VIP 信息（是否会员、到期时间、钻石数）。"""
        if not user_id:
            return None
        info = await self.db_manager.get_user_vip_info(user_id)
        if not info:
            return None

        vip_expiry = info.get("vip_expiry_date")
        if not isinstance(vip_expiry, datetime):
            vip_expiry = None

        try:
            diamonds = int(info.get("diamonds", 0))
        except Exception:
            diamonds = 0

        is_vip = bool(info.get("is_vip", False))

        return VipInfo(is_vip=is_vip, vip_expiry=vip_expiry, diamonds=diamonds)

    async def get_diamond_balance(self, user_id: int) -> int:
        """获取当前钻石余额。"""
        if not user_id:
            return 0
        info = await self.db_manager.get_user_vip_info(user_id)
        if not info:
            return 0
        try:
            return int(info.get("diamonds", 0))
        except Exception:
            return 0

    # ---------- 业务动作 ----------

    def calculate_new_vip_expiry(self, current_expiry: Optional[datetime], days: Optional[int]) -> datetime:
        """根据当前有效期和购买天数计算新的 VIP 到期时间。

        - days 为 None 表示购买永久 VIP，使用约定的远未来时间。
        - 若当前已是 VIP 且未过期，则在原有基础上叠加。
        - 若未开通或已过期，则从当前时间开始计算。
        """
        if days is None:
            return datetime(PERMANENT_VIP_YEAR, 12, 31, 23, 59, 59)

        now = datetime.utcnow()
        base = current_expiry if (current_expiry and current_expiry > now) else now
        return base + timedelta(days=int(days))

    async def purchase_membership(self, user_id: int, card_info: dict) -> Tuple[bool, Optional[datetime]]:
        """购买会员套餐：扣减钻石并更新 VIP，有足够钻石则返回 (True, new_expiry)。"""
        if not user_id:
            return False, None

        vip_info = await self.get_vip_info(user_id)
        current_expiry = vip_info.vip_expiry if vip_info else None

        cost = int(card_info.get("diamonds", 0))
        days = card_info.get("days", None)

        new_expiry = self.calculate_new_vip_expiry(current_expiry, days)

        success = await self.db_manager.consume_diamonds_and_update_vip(
            user_id=user_id,
            cost=cost,
            new_expiry=new_expiry,
        )
        if not success:
            return False, None

        return True, new_expiry

