"""
数据库操作层 - SQLite
三张表：orders（订单）、operators（操作员）、cancel_applies（撤单申请）
"""
import sqlite3
import time
from contextlib import contextmanager
from typing import Optional

import config


@contextmanager
def get_conn():
    """获取数据库连接（自动提交/关闭）"""
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """初始化数据库，建表"""
    with get_conn() as conn:
        # 订单表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_no TEXT UNIQUE NOT NULL,
                chat_id INTEGER NOT NULL,
                phone TEXT NOT NULL,
                operator TEXT DEFAULT '',
                amount REAL DEFAULT 0,
                name TEXT DEFAULT '',
                region TEXT DEFAULT '未知',
                balance REAL DEFAULT 0,
                completed_amount REAL DEFAULT 0,
                status TEXT DEFAULT 'pending',
                created_by INTEGER DEFAULT 0,
                created_by_name TEXT DEFAULT '',
                completed_by INTEGER DEFAULT 0,
                completed_by_name TEXT DEFAULT '',
                created_at INTEGER DEFAULT 0,
                completed_at INTEGER DEFAULT 0
            )
        """)
        # 操作员表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS operators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                username TEXT DEFAULT '',
                full_name TEXT DEFAULT '',
                role TEXT DEFAULT 'operator',
                created_at INTEGER DEFAULT 0
            )
        """)
        # 撤单申请表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cancel_applies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                apply_no TEXT UNIQUE NOT NULL,
                order_id INTEGER DEFAULT 0,
                order_no TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                applicant_id INTEGER DEFAULT 0,
                applicant_name TEXT DEFAULT '',
                chat_id INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                created_at INTEGER DEFAULT 0,
                reviewed_at INTEGER DEFAULT 0,
                reviewer_id INTEGER DEFAULT 0
            )
        """)
        # 余额查询记录表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS balance_queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT NOT NULL,
                operator TEXT DEFAULT '',
                balance REAL DEFAULT 0,
                points REAL DEFAULT 0,
                success INTEGER DEFAULT 1,
                error TEXT DEFAULT '',
                queried_by INTEGER DEFAULT 0,
                chat_id INTEGER DEFAULT 0,
                created_at INTEGER DEFAULT 0
            )
        """)
        # 索引
        conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_chat ON orders(chat_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_phone ON orders(phone)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cancel_status ON cancel_applies(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_balance_phone ON balance_queries(phone)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_balance_created ON balance_queries(created_at)")


# ============ 操作员相关 ============

def add_operator(user_id: int, username: str = "", full_name: str = "", role: str = "operator") -> bool:
    """添加操作员，已存在则更新信息"""
    now = int(time.time())
    with get_conn() as conn:
        existing = conn.execute("SELECT id FROM operators WHERE user_id=?", (user_id,)).fetchone()
        if existing:
            conn.execute("UPDATE operators SET username=?, full_name=?, role=? WHERE user_id=?",
                         (username, full_name, role, user_id))
        else:
            conn.execute("INSERT INTO operators (user_id, username, full_name, role, created_at) VALUES (?,?,?,?,?)",
                         (user_id, username, full_name, role, now))
    return True


def remove_operator(user_id: int) -> bool:
    """删除操作员"""
    with get_conn() as conn:
        conn.execute("DELETE FROM operators WHERE user_id=?", (user_id,))
    return True


def list_operators() -> list:
    """列出所有操作员"""
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM operators ORDER BY id").fetchall()
        return [dict(r) for r in rows]


def get_operator(user_id: int) -> Optional[dict]:
    """获取操作员信息"""
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM operators WHERE user_id=?", (user_id,)).fetchone()
        return dict(row) if row else None


def is_authorized(user_id: int) -> bool:
    """检查是否已授权（操作员或管理员）"""
    if user_id == config.SUPER_ADMIN_ID:
        return True
    op = get_operator(user_id)
    return op is not None


def is_admin(user_id: int) -> bool:
    """检查是否是管理员（超级管理员或 role=admin）"""
    if user_id == config.SUPER_ADMIN_ID:
        return True
    op = get_operator(user_id)
    return op is not None and op.get("role") == "admin"


# ============ 订单相关 ============

def create_order(chat_id: int, phone: str, operator: str, amount: float,
                 name: str, region: str, created_by: int, created_by_name: str) -> dict:
    """创建新订单，返回订单信息"""
    now = int(time.time())
    with get_conn() as conn:
        # 先插入获取自增ID
        cursor = conn.execute(
            "INSERT INTO orders (order_no, chat_id, phone, operator, amount, name, region, "
            "created_by, created_by_name, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            ("", chat_id, phone, operator, amount, name, region, created_by, created_by_name, now)
        )
        order_id = cursor.lastrowid
        order_no = f"{config.ORDER_PREFIX}{order_id}"
        conn.execute("UPDATE orders SET order_no=? WHERE id=?", (order_no, order_id))
        row = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        return dict(row)


def get_order_by_id(order_id: int) -> Optional[dict]:
    """按ID获取订单"""
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        return dict(row) if row else None


def get_active_order_by_phone(chat_id: int, phone: str) -> Optional[dict]:
    """按手机号获取群内进行中的订单"""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM orders WHERE chat_id=? AND phone=? AND status='pending' ORDER BY id DESC LIMIT 1",
            (chat_id, phone)
        ).fetchone()
        return dict(row) if row else None


def get_orders_by_chat(chat_id: int, status: Optional[str] = None) -> list:
    """获取群内订单，可按状态过滤"""
    with get_conn() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM orders WHERE chat_id=? AND status=? ORDER BY id",
                (chat_id, status)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM orders WHERE chat_id=? AND status!='cancelled' ORDER BY id",
                (chat_id,)
            ).fetchall()
        return [dict(r) for r in rows]


def search_orders(phone_part: str) -> list:
    """按手机号模糊搜索"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM orders WHERE phone LIKE ? AND status!='cancelled' ORDER BY id DESC LIMIT 20",
            (f"%{phone_part}%",)
        ).fetchall()
        return [dict(r) for r in rows]


def complete_order(order_id: int, completed_by: int, completed_by_name: str,
                   amount: Optional[float] = None) -> Optional[dict]:
    """
    完成订单（全部或部分）
    amount=None 表示完成全部剩余金额
    返回更新后的订单，若订单不存在或已完成返回 None
    """
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        if not row:
            return None
        order = dict(row)
        if order["status"] != "pending":
            return None

        remaining = order["amount"] - order["completed_amount"]
        if amount is None:
            add_amount = remaining
        else:
            add_amount = min(amount, remaining)

        new_completed = order["completed_amount"] + add_amount
        now = int(time.time())

        if new_completed >= order["amount"] - 0.001:
            # 全部完成
            conn.execute(
                "UPDATE orders SET completed_amount=?, status='completed', completed_by=?, "
                "completed_by_name=?, completed_at=? WHERE id=?",
                (order["amount"], completed_by, completed_by_name, now, order_id)
            )
        else:
            # 部分完成
            conn.execute(
                "UPDATE orders SET completed_amount=? WHERE id=?",
                (new_completed, order_id)
            )

        row = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        return dict(row)


def delete_order(order_id: int) -> bool:
    """删除订单（撤单审核通过后调用，或管理员直接删除）"""
    with get_conn() as conn:
        conn.execute("DELETE FROM orders WHERE id=?", (order_id,))
    return True


def delete_order_by_phone(chat_id: int, phone: str) -> Optional[dict]:
    """按手机号删除群内进行中的订单"""
    order = get_active_order_by_phone(chat_id, phone)
    if order:
        delete_order(order["id"])
    return order


# ============ 撤单申请相关 ============

def create_cancel_apply(order_id: int, order_no: str, phone: str,
                        applicant_id: int, applicant_name: str, chat_id: int) -> dict:
    """创建撤单申请"""
    now = int(time.time())
    with get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO cancel_applies (apply_no, order_id, order_no, phone, applicant_id, "
            "applicant_name, chat_id, created_at) VALUES (?,?,?,?,?,?,?,?)",
            ("", order_id, order_no, phone, applicant_id, applicant_name, chat_id, now)
        )
        apply_id = cursor.lastrowid
        apply_no = f"{apply_id}"
        conn.execute("UPDATE cancel_applies SET apply_no=? WHERE id=?", (apply_no, apply_id))
        row = conn.execute("SELECT * FROM cancel_applies WHERE id=?", (apply_id,)).fetchone()
        return dict(row)


def get_cancel_apply(apply_id: int) -> Optional[dict]:
    """按ID获取撤单申请"""
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM cancel_applies WHERE id=?", (apply_id,)).fetchone()
        return dict(row) if row else None


def list_pending_cancel_applies() -> list:
    """列出所有待审核的撤单申请"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM cancel_applies WHERE status='pending' ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]


def approve_cancel_apply(apply_id: int, reviewer_id: int) -> Optional[dict]:
    """
    同意撤单：标记申请为已同意，并删除对应订单
    返回 {"apply": 撤单申请, "order": 被删订单快照}，失败返回 None
    """
    now = int(time.time())
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM cancel_applies WHERE id=?", (apply_id,)).fetchone()
        if not row:
            return None
        apply = dict(row)
        if apply["status"] != "pending":
            return None

        # 先保存订单快照（删除前）
        order_snapshot = None
        if apply["order_id"]:
            orow = conn.execute("SELECT * FROM orders WHERE id=?", (apply["order_id"],)).fetchone()
            if orow:
                order_snapshot = dict(orow)

        # 标记申请已同意
        conn.execute(
            "UPDATE cancel_applies SET status='approved', reviewed_at=?, reviewer_id=? WHERE id=?",
            (now, reviewer_id, apply_id)
        )

        # 删除对应订单
        if apply["order_id"]:
            conn.execute("DELETE FROM orders WHERE id=?", (apply["order_id"],))

        # 重新查询申请
        row = conn.execute("SELECT * FROM cancel_applies WHERE id=?", (apply_id,)).fetchone()
        return {"apply": dict(row), "order": order_snapshot}


def reject_cancel_apply(apply_id: int, reviewer_id: int) -> Optional[dict]:
    """拒绝撤单申请"""
    now = int(time.time())
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM cancel_applies WHERE id=?", (apply_id,)).fetchone()
        if not row:
            return None
        conn.execute(
            "UPDATE cancel_applies SET status='rejected', reviewed_at=?, reviewer_id=? WHERE id=?",
            (now, reviewer_id, apply_id)
        )
        row = conn.execute("SELECT * FROM cancel_applies WHERE id=?", (apply_id,)).fetchone()
        return dict(row)


# ============ 余额查询记录相关 ============

def save_balance_query(phone: str, operator: str, balance: float, points: float,
                        success: bool, error: str, queried_by: int = 0,
                        chat_id: int = 0) -> int:
    """保存一条余额查询记录，返回记录ID"""
    now = int(time.time())
    with get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO balance_queries (phone, operator, balance, points, success, "
            "error, queried_by, chat_id, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (phone, operator, balance, points, 1 if success else 0,
             error, queried_by, chat_id, now)
        )
        return cursor.lastrowid


def get_recent_balance_queries(phone: str, limit: int = 5) -> list:
    """获取某手机号最近的余额查询记录（成功的）"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM balance_queries WHERE phone=? AND success=1 "
            "ORDER BY id DESC LIMIT ?",
            (phone, limit)
        ).fetchall()
        return [dict(r) for r in rows]


def get_balance_query_stats(phone: str) -> dict:
    """获取某手机号的查询统计"""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as total, COUNT(CASE WHEN success=1 THEN 1 END) as success_count "
            "FROM balance_queries WHERE phone=?",
            (phone,)
        ).fetchone()
        return dict(row) if row else {"total": 0, "success_count": 0}
