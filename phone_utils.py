"""
手机号工具：格式校验、地区识别、运营商标准化
地区识别优先使用 `phone` 库（内置号段数据库），不可用时返回"未知"
"""
import re

# 手机号正则：1开头，第二位3-9，共11位
PHONE_PATTERN = re.compile(r"1[3-9]\d{9}")

# 运营商关键词映射
OPERATOR_MAP = {
    "移动": "移动", "中国移动": "移动", "移": "移动", "yd": "移动", "YD": "移动",
    "联通": "联通", "中国联通": "联通", "联": "联通", "lt": "联通", "LT": "联通",
    "电信": "电信", "中国电信": "电信", "电": "电信", "dx": "电信", "DX": "电信",
}

# 尝试导入 phone 库
try:
    from phone import Phone
    _phone_instance = Phone()
    _PHONE_AVAILABLE = True
except Exception:
    _phone_instance = None
    _PHONE_AVAILABLE = False


def is_valid_phone(phone: str) -> bool:
    """校验是否为合法手机号"""
    return bool(PHONE_PATTERN.fullmatch(phone.strip()))


def extract_phone(text: str) -> str | None:
    """从文本中提取第一个手机号"""
    m = PHONE_PATTERN.search(text)
    return m.group(0) if m else None


def extract_all_phones(text: str) -> list[str]:
    """从文本中提取所有手机号"""
    return PHONE_PATTERN.findall(text)


def normalize_operator(raw: str) -> str:
    """标准化运营商名称"""
    raw = raw.strip()
    if raw in OPERATOR_MAP:
        return OPERATOR_MAP[raw]
    # 模糊匹配
    for key, val in OPERATOR_MAP.items():
        if key in raw or raw in key:
            return val
    return raw if raw else "未知"


def get_region(phone: str) -> str:
    """
    根据手机号识别归属地
    返回格式：省份 或 省份城市（如"北京"、"广东广州"）
    识别失败返回"未知"
    """
    if not _PHONE_AVAILABLE or not is_valid_phone(phone):
        return "未知"
    try:
        result = _phone_instance.find(phone)
        if not result:
            return "未知"
        province = result.get("province", "")
        city = result.get("city", "")
        if province and city and province != city:
            return f"{province}{city}"
        return province or city or "未知"
    except Exception:
        return "未知"


def get_phone_info(phone: str) -> dict:
    """获取手机号完整信息（地区+运营商）"""
    info = {"phone": phone, "region": "未知", "operator": "未知"}
    if not _PHONE_AVAILABLE or not is_valid_phone(phone):
        return info
    try:
        result = _phone_instance.find(phone)
        if result:
            province = result.get("province", "")
            city = result.get("city", "")
            if province and city and province != city:
                info["region"] = f"{province}{city}"
            else:
                info["region"] = province or city or "未知"
            info["operator"] = result.get("phone_type", "未知")
    except Exception:
        pass
    return info
