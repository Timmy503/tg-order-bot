#!/bin/bash
# ============================================================
# 查看机器人日志
# 用法：
#   ./logs.sh          # 实时跟踪日志
#   ./logs.sh 50       # 查看最近50行
#   ./logs.sh 50 error # 查看最近50行中的错误
# ============================================================

SERVICE_NAME="tg-order-bot"
LINES="${1:-100}"
FILTER="${2:-}"

if [ "$FILTER" = "error" ] || [ "$FILTER" = "err" ]; then
    echo "📋 最近 ${LINES} 行错误日志："
    journalctl -u "$SERVICE_NAME" -n "$LINES" --no-pager | grep -iE "error|exception|traceback|fail"
elif [ -n "$1" ] && [ "$1" = "-f" ]; then
    echo "📋 实时日志（Ctrl+C 退出）："
    journalctl -u "$SERVICE_NAME" -f
else
    echo "📋 最近 ${LINES} 行日志："
    journalctl -u "$SERVICE_NAME" -n "$LINES" --no-pager
fi

echo ""
echo "💡 提示："
echo "  实时跟踪: ./logs.sh -f"
echo "  查看错误: ./logs.sh 100 error"
echo "  完整日志: journalctl -u ${SERVICE_NAME} --no-pager | less"
