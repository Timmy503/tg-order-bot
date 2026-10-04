"""
TG 靓号订单管理机器人 - 配置文件
所有敏感配置建议通过环境变量传入，也可直接修改下方默认值。
"""
import os

# ===== 必须配置 =====
# 机器人 Token，从 @BotFather 获取
BOT_TOKEN = os.getenv("BOT_TOKEN", "在这里填入你的BotToken")

# 超级管理员 TG ID（数字ID），首次使用可先随便填，启动后私聊 /start 查看自己的 ID 再改
SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID", "0"))

# ===== 数据库 =====
DATABASE_PATH = os.getenv("DATABASE_PATH", "orders.db")

# ===== 运行模式 =====
# polling: 长轮询（VPS 上推荐，无需域名和证书）
# webhook: Webhook 模式（需要公网域名 + SSL）
RUN_MODE = os.getenv("RUN_MODE", "polling")

# Webhook 相关（仅 RUN_MODE=webhook 时需要配置）
# Render/Koyeb 等平台会自动设置 RENDER_EXTERNAL_URL，优先使用，无需手动填
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", os.getenv("RENDER_EXTERNAL_URL", ""))
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8443"))

# 监听端口（Render/Koyeb 等平台会自动设置 PORT 环境变量，优先使用）
PORT = int(os.getenv("PORT", str(WEBHOOK_PORT)))

# ===== 业务配置 =====
# 订单编号前缀
ORDER_PREFIX = "cmt"

# 撤单申请编号前缀
CANCEL_PREFIX = "#"

# ===== 话费余额查询 API =====
# 配置后自动使用真实 API，未配置则使用 mock 模拟数据（方便测试）
# 注意：不同服务商 API 格式不同，需在 balance_api.py 中修改 _build_request 和 _parse_response
BALANCE_API_URL = os.getenv("BALANCE_API_URL", "")
BALANCE_API_KEY = os.getenv("BALANCE_API_KEY", "")
BALANCE_API_TIMEOUT = int(os.getenv("BALANCE_API_TIMEOUT", "15"))

# ===== 付款链接 =====
# 付款链接模板，{phone} 会被替换为实际手机号
# 例如："https://your-pay.com/pay?phone={phone}"
# 留空则点击按钮提示未配置
PAYMENT_URL_TEMPLATE = os.getenv("PAYMENT_URL_TEMPLATE", "")
