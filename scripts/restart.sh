#!/bin/bash
# ============================================================
# 重启机器人（修改代码后执行）
# 用法：./restart.sh
# ============================================================

SERVICE_NAME="tg-order-bot"

echo "🔄 正在重启机器人..."

# 重启服务
sudo systemctl restart "$SERVICE_NAME"

# 等待启动
sleep 2

# 检查状态
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "✅ 机器人已重启成功"
    echo ""
    echo "最近日志："
    journalctl -u "$SERVICE_NAME" -n 10 --no-pager
else
    echo "❌ 重启失败，请检查日志："
    journalctl -u "$SERVICE_NAME" -n 30 --no-pager
    exit 1
fi
