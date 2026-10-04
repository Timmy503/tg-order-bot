#!/bin/bash
# ============================================================
# 数据库备份脚本
# 用法：./backup.sh [备份目录]
# 建议加入 crontab 定时执行：0 3 * * * /home/ubuntu/tg-order-bot/scripts/backup.sh
# ============================================================

PROJECT_DIR="/home/ubuntu/tg-order-bot"
DB_FILE="${PROJECT_DIR}/orders.db"
BACKUP_DIR="${1:-${PROJECT_DIR}/backups}"
KEEP_DAYS=30  # 保留最近30天的备份

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 检查数据库文件是否存在
if [ ! -f "$DB_FILE" ]; then
    echo "❌ 数据库文件不存在: $DB_FILE"
    exit 1
fi

# 生成备份文件名
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/orders_${TIMESTAMP}.db"

# 使用 SQLite 在线备份（安全，不影响运行中的机器人）
if command -v sqlite3 &> /dev/null; then
    sqlite3 "$DB_FILE" ".backup '$BACKUP_FILE'"
else
    # 没有 sqlite3 命令就直接复制（短暂锁定可接受）
    cp "$DB_FILE" "$BACKUP_FILE"
fi

# 验证备份
if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "✅ 备份成功: $BACKUP_FILE ($SIZE)"
else
    echo "❌ 备份失败"
    exit 1
fi

# 清理过期备份
if [ -d "$BACKUP_DIR" ]; then
    find "$BACKUP_DIR" -name "orders_*.db" -mtime +${KEEP_DAYS} -delete
    echo "🗑️  已清理 ${KEEP_DAYS} 天前的旧备份"
fi

# 列出最近5个备份
echo ""
echo "📦 最近备份："
ls -lhS "$BACKUP_DIR"/orders_*.db 2>/dev/null | head -5 | awk '{print "  " $9 " (" $5 ")"}'
