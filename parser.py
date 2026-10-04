"""
群内消息解析器
识别三种消息类型：下单、撤单、查询，并提取参数
"""
import re
from typing import Optional

from phone_utils import (
    extract_phone, extract_all_phones, is_valid_phone,
    normalize_operator, PHONE_PATTERN,
)

# 金额正则：整数或小数，可带"元"字
AMOUNT_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*元?")

# 运营商关键词（用于从行中提取）
OPERATOR_KEYWORDS = [
    "中国移动", "中国联通", "中国电信",
    "移动", "联通", "电信",
]


class ParsedOrder:
    """解析后的单条订单"""
    def __init__(self, phone: str, operator: str, amount: float, name: str, raw_line: str):
        self.phone = phone
        self.operator = operator
        self.amount = amount
        self.name = name
        self.raw_line = raw_line

    def __repr__(self):
        return f"ParsedOrder(phone={self.phone}, op={self.operator}, amount={self.amount}, name={self.name})"


def parse_order_line(line: str) -> Optional[ParsedOrder]:
    """
    解析一行下单文本，格式：手机号 运营商 金额 姓名
    支持变体：
      - 15502245331 联通 200 张丹丹
      - 15502245331 联通 200元 张丹丹
      - 15502245331 中国联通 200.5 张三
    解析失败返回 None
    """
    line = line.strip()
    if not line:
        return None

    # 提取手机号
    phone = extract_phone(line)
    if not phone:
        return None

    # 去掉手机号后剩余文本
    remaining = line.replace(phone, " ", 1).strip()

    # 提取运营商
    operator_raw = ""
    for kw in OPERATOR_KEYWORDS:
        if kw in remaining:
            operator_raw = kw
            remaining = remaining.replace(kw, " ", 1).strip()
            break

    # 提取金额
    amount_match = AMOUNT_PATTERN.search(remaining)
    amount = 0.0
    if amount_match:
        amount = float(amount_match.group(1))
        remaining = remaining[:amount_match.start()] + remaining[amount_match.end():]
        remaining = remaining.strip()

    # 剩余的就是姓名（清理多余空格和"元"字残留）
    name = remaining.replace("元", " ").strip()
    name = re.sub(r"\s+", " ", name)

    # 必须有手机号和金额，运营商和姓名可以为空但尽量要有
    if amount <= 0:
        return None

    operator = normalize_operator(operator_raw) if operator_raw else "未知"

    return ParsedOrder(
        phone=phone,
        operator=operator,
        amount=amount,
        name=name if name else "未填写",
        raw_line=line,
    )


def parse_orders_from_text(text: str) -> tuple[list[ParsedOrder], list[str]]:
    """
    从多行文本中解析所有订单
    返回 (成功解析的订单列表, 失败的行列表)
    """
    orders = []
    failed = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        # 跳过明显的命令行
        if line.startswith("/") or line.startswith("撤单") or line in ("本群订单", "本群话费订单"):
            continue
        parsed = parse_order_line(line)
        if parsed:
            orders.append(parsed)
        else:
            # 如果行里包含手机号但解析失败，记入失败；否则忽略（可能是闲聊）
            if extract_phone(line):
                failed.append(line)
    return orders, failed


def parse_cancel_message(text: str) -> Optional[list[str]]:
    """
    解析撤单消息，格式：撤单 手机号1 手机号2 ...
    返回手机号列表，不是撤单消息返回 None
    """
    text = text.strip()
    if not text.startswith("撤单"):
        return None
    # 去掉"撤单"前缀
    remaining = text[2:].strip()
    phones = extract_all_phones(remaining)
    return phones if phones else []


def detect_query_type(text: str) -> Optional[str]:
    """
    检测查询消息类型
    返回 "summary"（本群订单统计）、"detail"（本群话费订单明细）、None（不是查询）
    """
    text = text.strip()
    if text in ("本群订单", "群订单", "订单统计", "/orders", "/order"):
        return "summary"
    if text in ("本群话费订单", "话费订单", "订单明细", "订单列表", "/orders detail", "/list"):
        return "detail"
    return None


def is_order_input(text: str) -> bool:
    """
    判断文本是否可能是下单输入（包含手机号且不是已知命令）
    """
    text = text.strip()
    if not text or text.startswith("/"):
        return False
    if text.startswith("撤单"):
        return False
    if detect_query_type(text):
        return False
    return bool(extract_phone(text))
