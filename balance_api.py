"""
话费余额查询 API 客户端
========================
使用前请在 config.py 中配置 BALANCE_API_URL 和 BALANCE_API_KEY。

【重要】不同服务商的 API 请求/返回格式不同，你需要根据自己的接口
实际情况修改下方 `_build_request` 和 `_parse_response` 两个方法。
代码中已用 ⚠️ 标注需要修改的位置。

未配置 API 时自动进入 mock 模式，返回模拟数据方便测试。
"""
import logging
import time
from typing import Optional

import config

logger = logging.getLogger(__name__)


class BalanceResult:
    """余额查询结果"""
    def __init__(self, phone: str, operator: str = "", balance: float = 0,
                 points: float = 0, success: bool = True, error: str = ""):
        self.phone = phone
        self.operator = operator
        self.balance = balance
        self.points = points
        self.success = success
        self.error = error
        self.query_time = int(time.time())

    def to_dict(self) -> dict:
        return {
            "phone": self.phone,
            "operator": self.operator,
            "balance": self.balance,
            "points": self.points,
            "success": self.success,
            "error": self.error,
            "query_time": self.query_time,
        }


class BalanceAPI:
    """话费余额查询 API 客户端"""

    def __init__(self):
        self.api_url = getattr(config, "BALANCE_API_URL", "")
        self.api_key = getattr(config, "BALANCE_API_KEY", "")
        self.timeout = getattr(config, "BALANCE_API_TIMEOUT", 15)
        self.mock_mode = not bool(self.api_url)
        if self.mock_mode:
            logger.info("余额查询 API 未配置，使用 mock 模式")

    async def query(self, phone: str) -> BalanceResult:
        """
        查询话费余额
        :param phone: 11位手机号
        :return: BalanceResult
        """
        if self.mock_mode:
            return self._mock_query(phone)

        try:
            import aiohttp
            url, headers, params = self._build_request(phone)
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, headers=headers, params=params, timeout=self.timeout
                ) as resp:
                    if resp.status != 200:
                        return BalanceResult(phone, success=False,
                                              error=f"API 返回状态码 {resp.status}")
                    data = await resp.json(content_type=None)
                    return self._parse_response(phone, data)
        except Exception as e:
            logger.error(f"余额查询失败: {e}")
            return BalanceResult(phone, success=False, error=f"查询失败: {str(e)}")

    # ⚠️ ========== 根据你的 API 修改以下两个方法 ==========

    def _build_request(self, phone: str) -> tuple:
        """
        构建 API 请求
        ⚠️ 根据你的 API 实际格式修改：URL、请求头、参数
        返回 (url, headers, params)

        以下是一个通用示例（GET 请求，手机号作为参数，API Key 放请求头）：
        """
        url = self.api_url
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        params = {"phone": phone}
        return url, headers, params

    def _parse_response(self, phone: str, data: dict) -> BalanceResult:
        """
        解析 API 返回数据
        ⚠️ 根据你的 API 实际返回格式修改字段映射

        假设 API 返回格式示例：
        {
            "code": 0,
            "msg": "success",
            "data": {
                "phone": "13212801772",
                "operator": "黑龙江联通",
                "balance": 398.27,
                "points": 1962.5632
            }
        }
        """
        # ⚠️ 修改以下字段映射以匹配你的 API
        if data.get("code") != 0 and data.get("code") != "0":
            return BalanceResult(
                phone, success=False,
                error=data.get("msg") or data.get("message") or "查询失败"
            )

        result_data = data.get("data", data)
        return BalanceResult(
            phone=phone,
            operator=result_data.get("operator", result_data.get("carrier", "")),
            balance=float(result_data.get("balance", 0)),
            points=float(result_data.get("points", result_data.get("score", 0))),
            success=True,
        )

    # ⚠️ ========== mock 模式（无需修改） ==========

    def _mock_query(self, phone: str) -> BalanceResult:
        """模拟查询（未配置 API 时使用）"""
        # 根据手机号生成稳定的模拟数据
        seed = sum(int(c) for c in phone)
        balance = round(100 + (seed % 500) + (seed % 100) / 100, 2)
        points = round(500 + (seed % 2000) + (seed % 1000) / 10000, 4)

        # 简单的运营商判断（前3位）
        prefix3 = phone[:3]
        if prefix3 in ("134", "135", "136", "137", "138", "139", "147", "150",
                       "151", "152", "157", "158", "159", "172", "178", "182",
                       "183", "184", "187", "188", "195", "198"):
            operator = "中国移动"
        elif prefix3 in ("130", "131", "132", "145", "155", "156", "166",
                         "171", "175", "176", "185", "186", "196"):
            operator = "中国联通"
        elif prefix3 in ("133", "149", "153", "173", "177", "180", "181",
                         "189", "190", "191", "193", "199"):
            operator = "中国电信"
        else:
            operator = "未知运营商"

        # 模拟网络延迟
        time.sleep(0.5)

        return BalanceResult(
            phone=phone,
            operator=operator,
            balance=balance,
            points=points,
            success=True,
        )


# 全局单例
_balance_api: Optional[BalanceAPI] = None


def get_balance_api() -> BalanceAPI:
    """获取余额查询 API 单例"""
    global _balance_api
    if _balance_api is None:
        _balance_api = BalanceAPI()
    return _balance_api
