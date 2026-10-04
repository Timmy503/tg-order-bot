#!/bin/bash
# ============================================================
# 一键部署脚本
# 用法：chmod +x setup.sh && sudo ./setup.sh
# ============================================================

set -e

# ===== 配置区（根据实际情况修改）=====
PROJECT_DIR="/home/ubuntu/tg-order-bot"
SERVICE_NAME="tg-order-bot"
PYTHON_BIN="python3"

# 机器人配置（必填）
BOT_TOKEN="你的BotToken"
SUPER_ADMIN_ID="你的TG数字ID"

# ===== 开始部署 =====
echo "========================================"
echo "  TG 订单机器人 - 一键部署"
echo "========================================"

# 1. 检查是否在项目目录
if [ ! -f "$PROJECT_DIR/bot.py" ]; then
    echo "❌ 未找到 $PROJECT_DIR/bot.py"
    echo "   请先将项目文件上传到 $PROJECT_DIR"
    exit 1
fi

cd "$PROJECT_DIR"

# 2. 安装系统依赖
echo ""
echo "[1/5] 安装系统依赖..."
apt update -qq
apt install -y -qq python3 python3-pip python3-venv > /dev/null 2>&1
echo "  ✅ Python 环境就绪"

# 3. 创建虚拟环境并安装依赖
echo ""
echo "[2/5] 创建虚拟环境并安装依赖..."
if [ ! -d "venv" ]; then
    $PYTHON_BIN -m venv venv
fi
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "  ✅ 依赖安装完成"

# 4. 写入配置
echo ""
echo "[3/5] 写入配置..."
cat > config.py << 'PYEOF'
"""
TG 靓号订单管理机器人 - 配置文件
"""
import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "BOT_TOKEN_PLACEHOLDER")
SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID", "0"))
DATABASE_PATH = os.getenv("DATABASE_PATH", "orders.db")
RUN_MODE = os.getenv("RUN_MODE", "polling")
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8443"))
ORDER_PREFIX = "cmt"
CANCEL_PREFIX = "#"
PYEOF

# 用 sed 替换占位符（避免 heredoc 变量展开问题）
sed -i "s/BOT_TOKEN_PLACEHOLDER/$BOT_TOKEN/" config.py
sed -i "s/\"SUPER_ADMIN_ID\", \"0\"/\"SUPER_ADMIN_ID\", \"$SUPER_ADMIN_ID\"/" config.py
echo "  ✅ 配置已写入"

# 5. 配置 systemd 服务
echo ""
echo "[4/5] 配置 systemd 服务..."
cat > /etc/systemd/system/${SERVICE_NAME}.service << EOF
[Unit]
Description=TG 靓号订单管理机器人
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=${PROJECT_DIR}
Environment="BOT_TOKEN=${BOT_TOKEN}"
Environment="SUPER_ADMIN_ID=${SUPER_ADMIN_ID}"
Environment="RUN_MODE=polling"
ExecStart=${PROJECT_DIR}/venv/bin/python ${PROJECT_DIR}/bot.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable ${SERVICE_NAME}
echo "  ✅ systemd 服务已配置"

# 6. 启动服务
echo ""
echo "[5/5] 启动机器人..."
systemctl start ${SERVICE_NAME}
sleep 2

if systemctl is-active --quiet ${SERVICE_NAME}; then
    echo "  ✅ 机器人启动成功！"
    echo ""
    echo "========================================"
    echo "  部署完成！"
    echo "========================================"
    echo ""
    echo "常用命令："
    echo "  查看状态: systemctl status ${SERVICE_NAME}"
    echo "  查看日志: journalctl -u ${SERVICE_NAME} -f"
    echo "  重启:     systemctl restart ${SERVICE_NAME}"
    echo "  停止:     systemctl stop ${SERVICE_NAME}"
    echo ""
    echo "下一步：去 Telegram 私聊机器人发 /start 验证"
else
    echo "  ❌ 启动失败，请检查日志：journalctl -u ${SERVICE_NAME} -n 50"
    exit 1
fi
