"""
TG 靓号订单管理机器人 - 主程序
功能：群内自然语言下单、订单查询、按钮完成、撤单申请与审核、操作员管理
运行：python3 bot.py
"""
import asyncio
import logging
import time
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import config
import db
from phone_utils import get_region, extract_phone, is_valid_phone
from parser import (
    parse_orders_from_text, parse_cancel_message,
    detect_query_type, is_order_input,
)
from balance_api import get_balance_api

# ===== 日志 =====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ===== Bot 初始化 =====
bot = Bot(
    token=config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()


# ============ 工具函数 ============

def format_amount(amount: float) -> str:
    """格式化金额：整数不带小数，小数保留两位"""
    if amount == int(amount):
        return str(int(amount))
    return f"{amount:.2f}"


def format_time(ts: int) -> str:
    """时间戳转字符串"""
    if not ts:
        return "-"
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def get_user_display(user: types.User) -> str:
    """获取用户显示名"""
    if user.username:
        return f"@{user.username}"
    return user.full_name or str(user.id)


def get_user_name(user: types.User) -> str:
    """获取用户姓名（用于数据库存储）"""
    return user.full_name or user.username or str(user.id)


def build_order_detail_line(order: dict) -> str:
    """构建订单明细行（截图格式）"""
    status_text = "进行中" if order["status"] == "pending" else (
        "已完成" if order["status"] == "completed" else "已撤单"
    )
    return (
        f"{order['order_no']}. {order['phone']} {order['region']} "
        f"{order['name']} {order['operator']} 充值 {format_amount(order['amount'])} 元 "
        f"余额 {format_amount(order['balance'])} 状态 {status_text}"
    )


def build_complete_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """构建订单完成按钮"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ 充值完成", callback_data=f"complete:{order_id}")]
    ])


def build_cancel_review_keyboard(apply_id: int) -> InlineKeyboardMarkup:
    """构建撤单审核按钮"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ 同意撤单", callback_data=f"cancel_approve:{apply_id}"),
            InlineKeyboardButton(text="❌ 拒绝", callback_data=f"cancel_reject:{apply_id}"),
        ]
    ])


def build_payment_keyboard(phone: str) -> InlineKeyboardMarkup:
    """构建生成付款链接按钮"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 生成付款链接", callback_data=f"pay:{phone}")]
    ])


def _is_pure_phone(text: str) -> bool:
    """判断文本是否为纯手机号（去除空白后正好11位合法手机号）"""
    cleaned = text.strip().replace(" ", "").replace("-", "")
    return is_valid_phone(cleaned) and len(cleaned) == 11


async def send_notification_to_user(user_id: int, text: str):
    """向用户发送私聊通知（失败不报错）"""
    try:
        await bot.send_message(chat_id=user_id, text=text)
    except Exception as e:
        logger.warning(f"向用户 {user_id} 发送通知失败: {e}")


# ============ 权限检查 ============

def check_auth(user_id: int) -> bool:
    """检查是否已授权"""
    return db.is_authorized(user_id)


def check_admin(user_id: int) -> bool:
    """检查是否是管理员"""
    return db.is_admin(user_id)


# ============ 私聊命令 ============

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """/start 查看ID和授权状态"""
    user_id = message.from_user.id
    text = f"👋 欢迎！\n\n您的 ID：<code>{user_id}</code>\n\n"

    if check_auth(user_id):
        op = db.get_operator(user_id)
        role_text = "管理员" if (user_id == config.SUPER_ADMIN_ID or (op and op["role"] == "admin")) else "操作员"
        text += (
            f"🎉 您已获【话费车】权限（{role_text}）\n\n"
            f"现在可在业务群上单。\n"
            f"请发送 /start 刷新菜单；在业务群内可发送 /groupinfo 刷新群状态。\n\n"
            f"📋 <b>可用命令：</b>\n"
            f"群内直接发：手机号 运营商 金额 姓名（下单）\n"
            f"群内发：撤单 手机号1 手机号2（申请撤单）\n"
            f"群内发：本群订单 / 本群话费订单（查单）\n"
            f"/recharge 手机号 金额（部分充值回填）\n"
            f"/search 手机号（模糊搜索订单）"
        )
        if check_admin(user_id):
            text += (
                f"\n\n<b>管理员命令：</b>\n"
                f"/addop TG_ID 添加操作员\n"
                f"/delop TG_ID 删除操作员\n"
                f"/listop 列出操作员\n"
                f"/cancellist 查看撤单申请\n"
                f"/cancelok 申请编号 同意撤单\n"
                f"/del 手机号 直接删除订单"
            )
    else:
        text += "您尚未获得授权，请联系管理员提供您的 ID 进行授权。"

    await message.answer(text)


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """帮助"""
    await cmd_start(message)


@dp.message(Command("groupinfo"))
async def cmd_groupinfo(message: types.Message):
    """群状态（群绑定功能预留，目前返回默认信息）"""
    if message.chat.type in ("group", "supergroup"):
        await message.answer(
            f"📱 本群为话费群\n"
            f"🆔 群ID：<code>{message.chat.id}</code>\n"
            f"群绑定功能将在后续版本开放。"
        )
    else:
        await message.answer("此命令请在业务群内使用。")


# ----- 管理员：操作员管理 -----

@dp.message(Command("addop"))
async def cmd_addop(message: types.Message, command: CommandObject):
    """添加操作员 /addop TG_ID"""
    if not check_admin(message.from_user.id):
        await message.answer("❌ 仅管理员可使用此命令。")
        return
    args = command.args.strip() if command.args else ""
    if not args or not args.isdigit():
        await message.answer("⚠️ 用法：/addop TG_ID\n例如：/addop 6559370827")
        return
    user_id = int(args)
    db.add_operator(user_id, role="operator")
    await message.answer(f"✅ 已添加操作员：<code>{user_id}</code>")
    # 通知对方
    await send_notification_to_user(
        user_id,
        f"🎉 您已获【话费车】权限\n\n现在可在业务群上单。\n请发送 /start 刷新菜单。"
    )


@dp.message(Command("delop"))
async def cmd_delop(message: types.Message, command: CommandObject):
    """删除操作员 /delop TG_ID"""
    if not check_admin(message.from_user.id):
        await message.answer("❌ 仅管理员可使用此命令。")
        return
    args = command.args.strip() if command.args else ""
    if not args or not args.isdigit():
        await message.answer("⚠️ 用法：/delop TG_ID")
        return
    user_id = int(args)
    if user_id == config.SUPER_ADMIN_ID:
        await message.answer("❌ 不能删除超级管理员。")
        return
    db.remove_operator(user_id)
    await message.answer(f"✅ 已删除操作员：<code>{user_id}</code>")


@dp.message(Command("listop"))
async def cmd_listop(message: types.Message):
    """列出所有操作员"""
    if not check_admin(message.from_user.id):
        await message.answer("❌ 仅管理员可使用此命令。")
        return
    ops = db.list_operators()
    if not ops:
        await message.answer("📋 操作员列表为空。")
        return
    lines = ["📋 <b>操作员列表：</b>\n"]
    for op in ops:
        role = "👑 管理员" if op["role"] == "admin" else "👤 操作员"
        name = op["full_name"] or op["username"] or "-"
        lines.append(f"{role} <code>{op['user_id']}</code> ({name})")
    # 超级管理员
    lines.append(f"\n👑 超级管理员：<code>{config.SUPER_ADMIN_ID}</code>")
    await message.answer("\n".join(lines))


# ----- 管理员：撤单审核 -----

@dp.message(Command("cancellist"))
async def cmd_cancellist(message: types.Message):
    """查看待审核撤单申请"""
    if not check_admin(message.from_user.id):
        await message.answer("❌ 仅管理员可使用此命令。")
        return
    applies = db.list_pending_cancel_applies()
    if not applies:
        await message.answer("📋 当前没有待审核的撤单申请。")
        return
    for apply in applies:
        order = db.get_order_by_id(apply["order_id"]) if apply["order_id"] else None
        text = (
            f"📝 <b>撤单申请 #{apply['apply_no']}</b>\n"
            f"手机号：<code>{apply['phone']}</code>\n"
            f"申请人：{apply['applicant_name']} (<code>{apply['applicant_id']}</code>)\n"
            f"申请时间：{format_time(apply['created_at'])}\n"
        )
        if order:
            text += (
                f"订单编号：{order['order_no']}\n"
                f"原始金额：{format_amount(order['amount'])}元\n"
                f"累计已完成：{format_amount(order['completed_amount'])}元\n"
                f"撤销剩余：{format_amount(order['amount'] - order['completed_amount'])}元"
            )
        else:
            text += "⚠️ 关联订单已不存在"
        await message.answer(text, reply_markup=build_cancel_review_keyboard(apply["id"]))


@dp.message(Command("cancelok"))
async def cmd_cancelok(message: types.Message, command: CommandObject):
    """同意撤单 /cancelok 申请编号"""
    if not check_admin(message.from_user.id):
        await message.answer("❌ 仅管理员可使用此命令。")
        return
    args = command.args.strip() if command.args else ""
    if not args or not args.isdigit():
        await message.answer("⚠️ 用法：/cancelok 申请编号\n例如：/cancelok 112")
        return
    apply_id = int(args)
    result = db.approve_cancel_apply(apply_id, message.from_user.id)
    if not result:
        await message.answer("❌ 撤单申请不存在或已处理。")
        return
    await message.answer(f"✅ 撤单申请 #{apply_id} 已同意。")
    await _notify_cancel_result(result["apply"], result["order"])


@dp.message(Command("del"))
async def cmd_del(message: types.Message, command: CommandObject):
    """管理员直接删除订单 /del 手机号"""
    if not check_admin(message.from_user.id):
        await message.answer("❌ 仅管理员可使用此命令。")
        return
    args = command.args.strip() if command.args else ""
    phone = extract_phone(args)
    if not phone:
        await message.answer("⚠️ 用法：/del 手机号\n例如：/del 13810295470")
        return
    chat_id = message.chat.id if message.chat.type in ("group", "supergroup") else None
    if chat_id:
        order = db.delete_order_by_phone(chat_id, phone)
    else:
        # 私聊中删除，搜索所有群的该手机号订单
        orders = db.search_orders(phone)
        order = orders[0] if orders else None
        if order:
            db.delete_order(order["id"])
    if order:
        await message.answer(
            f"✅ 已删除订单 {order['order_no']}\n"
            f"手机号：<code>{phone}</code>\n"
            f"金额：{format_amount(order['amount'])}元"
        )
    else:
        await message.answer(f"❌ 未找到手机号 <code>{phone}</code> 的进行中订单。")


# ----- 通用：搜索订单 -----

@dp.message(Command("search"))
async def cmd_search(message: types.Message, command: CommandObject):
    """模糊搜索订单 /search 手机号"""
    if not check_auth(message.from_user.id):
        await message.answer("❌ 你不是操作员，无法使用本机器人")
        return
    args = command.args.strip() if command.args else ""
    if not args:
        await message.answer("⚠️ 用法：/search 手机号\n支持部分手机号模糊搜索")
        return
    orders = db.search_orders(args)
    if not orders:
        await message.answer(f"🔍 未找到包含 \"{args}\" 的订单。")
        return
    lines = [f"🔍 搜索结果（共 {len(orders)} 条）：\n"]
    for order in orders:
        lines.append(build_order_detail_line(order))
    await message.answer("\n".join(lines))


# ----- 部分充值回填 -----

@dp.message(Command("recharge"))
async def cmd_recharge(message: types.Message, command: CommandObject):
    """部分充值回填 /recharge 手机号 金额"""
    if not check_auth(message.from_user.id):
        await message.answer("❌ 你不是操作员，无法使用本机器人")
        return
    args = command.args.strip() if command.args else ""
    parts = args.split()
    phone = extract_phone(args)
    if not phone or len(parts) < 2:
        await message.answer("⚠️ 用法：/recharge 手机号 充值金额\n例如：/recharge 13810295470 100")
        return
    # 提取金额
    amount_str = parts[-1].replace("元", "")
    try:
        amount = float(amount_str)
    except ValueError:
        await message.answer("⚠️ 金额格式不正确。")
        return

    chat_id = message.chat.id if message.chat.type in ("group", "supergroup") else None
    if chat_id:
        order = db.get_active_order_by_phone(chat_id, phone)
    else:
        orders = db.search_orders(phone)
        order = orders[0] if orders else None

    if not order:
        await message.answer(f"❌ 未找到手机号 <code>{phone}</code> 的进行中订单。")
        return

    remaining = order["amount"] - order["completed_amount"]
    if amount > remaining + 0.001:
        await message.answer(
            f"⚠️ 充值金额超过剩余未完成金额。\n"
            f"原始金额：{format_amount(order['amount'])}元\n"
            f"已完成：{format_amount(order['completed_amount'])}元\n"
            f"剩余：{format_amount(remaining)}元"
        )
        return

    updated = db.complete_order(
        order["id"], message.from_user.id, get_user_name(message.from_user), amount=amount
    )
    if not updated:
        await message.answer("❌ 订单状态异常，无法充值。")
        return

    if updated["status"] == "completed":
        await message.answer(
            f"✅ 充值完成\n"
            f"手机号：<code>{phone}</code>\n"
            f"本次充值：{format_amount(amount)}元\n"
            f"订单已全部完成！"
        )
        # 发送完成通知
        await _send_complete_notification(updated, message.from_user, message.chat.id)
    else:
        await message.answer(
            f"✅ 部分充值成功\n"
            f"手机号：<code>{phone}</code>\n"
            f"本次充值：{format_amount(amount)}元\n"
            f"累计已完成：{format_amount(updated['completed_amount'])}元\n"
            f"剩余：{format_amount(updated['amount'] - updated['completed_amount'])}元"
        )


# ============ 群内消息处理 ============

@dp.message(F.chat.type.in_({"group", "supergroup"}), F.text)
async def handle_group_text(message: types.Message):
    """处理群内文本消息：下单 / 撤单 / 查询"""
    user_id = message.from_user.id
    text = message.text.strip()

    # 跳过斜杠命令（由专门的 handler 处理）
    if text.startswith("/"):
        return

    # 权限检查
    if not check_auth(user_id):
        # 未授权用户如果发了下单/撤单/查询/余额查询相关内容，提示一下
        if (is_order_input(text) or text.startswith("撤单")
                or detect_query_type(text) or _is_pure_phone(text)):
            await message.answer("❌ 你不是操作员，无法使用本机器人")
        return

    # 1. 撤单
    cancel_phones = parse_cancel_message(text)
    if cancel_phones is not None:
        await _handle_cancel(message, cancel_phones)
        return

    # 2. 订单查询
    query_type = detect_query_type(text)
    if query_type == "summary":
        await _handle_order_summary(message)
        return
    if query_type == "detail":
        await _handle_order_detail(message)
        return

    # 3. 纯手机号 → 余额查询
    if _is_pure_phone(text):
        await _handle_balance_query(message, text)
        return

    # 4. 下单
    if is_order_input(text):
        await _handle_new_orders(message, text)
        return


async def _handle_new_orders(message: types.Message, text: str):
    """处理下单"""
    orders, failed = parse_orders_from_text(text)
    if not orders and not failed:
        return  # 不是下单消息，忽略

    chat_id = message.chat.id
    user = message.from_user
    user_name = get_user_name(user)

    success_lines = []
    fail_lines = []

    for parsed in orders:
        # 检查是否已有进行中的同手机号订单
        existing = db.get_active_order_by_phone(chat_id, parsed.phone)
        if existing:
            fail_lines.append(f"⚠️ {parsed.phone} 已存在进行中订单 {existing['order_no']}")
            continue

        region = get_region(parsed.phone)
        order = db.create_order(
            chat_id=chat_id,
            phone=parsed.phone,
            operator=parsed.operator,
            amount=parsed.amount,
            name=parsed.name,
            region=region,
            created_by=user.id,
            created_by_name=user_name,
        )
        success_lines.append(f"✅ {parsed.phone} 新增成功")

    for line in failed:
        fail_lines.append(f"❌ 解析失败：{line}")

    # 发送结果
    result_text = ""
    if success_lines:
        result_text += "\n".join(success_lines)
    if fail_lines:
        if result_text:
            result_text += "\n\n"
        result_text += "\n".join(fail_lines)
    if result_text:
        await message.answer(result_text)


async def _handle_cancel(message: types.Message, phones: list[str]):
    """处理撤单申请"""
    if not phones:
        await message.answer("⚠️ 请在\"撤单\"后跟上手机号，例如：撤单 13810295470")
        return

    chat_id = message.chat.id
    user = message.from_user
    user_name = get_user_name(user)

    result_lines = ["撤单结果：\n"]

    for phone in phones:
        order = db.get_active_order_by_phone(chat_id, phone)
        if not order:
            result_lines.append(f"❌ 话费号码 {phone}：未找到进行中订单")
            continue

        apply = db.create_cancel_apply(
            order_id=order["id"],
            order_no=order["order_no"],
            phone=phone,
            applicant_id=user.id,
            applicant_name=user_name,
            chat_id=chat_id,
        )
        result_lines.append(
            f"⏳ 话费号码 {phone}：已提交管理员审核（申请 #{apply['apply_no']}）\n"
            f"管理员同意前订单不会自动撤销。"
        )

    await message.answer("\n".join(result_lines))


async def _handle_order_summary(message: types.Message):
    """本群订单统计"""
    chat_id = message.chat.id
    orders = db.get_orders_by_chat(chat_id)
    pending = [o for o in orders if o["status"] == "pending"]
    completed = [o for o in orders if o["status"] == "completed"]

    total_amount = sum(o["amount"] for o in orders)
    pending_amount = sum(o["amount"] for o in pending)
    completed_amount = sum(o["amount"] for o in completed)

    text = (
        f"📱 本群为话费群\n\n"
        f"📋 本群订单（共 {len(orders)} 单 | 总计 {format_amount(total_amount)} 元）\n"
        f"📱 话费 {len(orders)} 单（{format_amount(total_amount)} 元）| ⚡ 电费 0 单（0 元）\n\n"
        f"⏳ 进行中：{len(pending)} 单（{format_amount(pending_amount)} 元）\n"
        f"✅ 已完成：{len(completed)} 单（{format_amount(completed_amount)} 元）"
    )
    await message.answer(text)


async def _handle_order_detail(message: types.Message):
    """本群话费订单明细（带完成按钮）"""
    chat_id = message.chat.id
    pending = db.get_orders_by_chat(chat_id, status="pending")

    if not pending:
        await message.answer("📋 本群暂无进行中的话费订单。")
        return

    # 每条订单单独发一条消息，带完成按钮
    for order in pending:
        line = build_order_detail_line(order)
        await message.answer(line, reply_markup=build_complete_keyboard(order["id"]))


async def _handle_balance_query(message: types.Message, phone: str):
    """处理话费余额查询（纯手机号触发）"""
    user = message.from_user
    phone = phone.strip().replace(" ", "").replace("-", "")

    # 先回复"正在查询"
    status_msg = await message.answer(f"{get_user_name(user)}\n{phone}\n\n正在为您查询...")

    # 调用 API 查询
    api = get_balance_api()
    result = await api.query(phone)

    # 保存查询记录
    db.save_balance_query(
        phone=phone,
        operator=result.operator,
        balance=result.balance,
        points=result.points,
        success=result.success,
        error=result.error,
        queried_by=user.id,
        chat_id=message.chat.id,
    )

    if not result.success:
        await status_msg.edit_text(
            f"{get_user_name(user)}\n{phone}\n\n"
            f"❌ 查询失败：{result.error}"
        )
        return

    # 获取最近5条查询记录（不含本次，因为本次刚保存，取前5条就是历史）
    # 实际上取最近5条，包含本次也可以，截图里显示的是历史记录
    recent = db.get_recent_balance_queries(phone, limit=5)

    # 构建消息（截图格式）
    text = f"{get_user_name(user)}\n{phone}\n\n"
    text += f"号码：{phone}\n"
    text += f"运营商：{result.operator}\n"
    text += f"话费余额：{format_amount(result.balance)}\n"
    text += f"剩余积分：{format_amount(result.points)}\n\n"

    if recent:
        text += f"该号码最近{len(recent)}条查询记录：\n"
        for record in recent:
            time_str = datetime.fromtimestamp(record["created_at"]).strftime("%m-%d %H:%M:%S")
            text += f"余额: {format_amount(record['balance'])}, 时间: {time_str}\n"

    # 编辑原消息，带付款链接按钮
    await status_msg.edit_text(text, reply_markup=build_payment_keyboard(phone))


# ============ 按钮回调处理 ============

@dp.callback_query(F.data.startswith("complete:"))
async def callback_complete(callback: types.CallbackQuery):
    """完成订单按钮"""
    user = callback.from_user
    if not check_auth(user.id):
        await callback.answer("❌ 你不是操作员，无法使用本机器人", show_alert=True)
        return

    order_id = int(callback.data.split(":")[1])
    order = db.get_order_by_id(order_id)
    if not order:
        await callback.answer("❌ 订单不存在", show_alert=True)
        await callback.message.edit_reply_markup(reply_markup=None)
        return
    if order["status"] != "pending":
        await callback.answer("❌ 订单已处理", show_alert=True)
        await callback.message.edit_reply_markup(reply_markup=None)
        return

    # 全部完成
    updated = db.complete_order(order_id, user.id, get_user_name(user))
    if not updated:
        await callback.answer("❌ 完成失败", show_alert=True)
        return

    # 编辑原消息，移除按钮
    new_line = build_order_detail_line(updated)
    await callback.message.edit_text(new_line, reply_markup=None)
    await callback.answer("✅ 订单已完成")

    # 发送完成通知到群
    await _send_complete_notification(updated, user, callback.message.chat.id)


async def _send_complete_notification(order: dict, user: types.User, chat_id: int):
    """发送订单完成通知（截图格式）"""
    display = get_user_display(user)
    text = (
        f"✅ 完成订单（1单 | 共{format_amount(order['amount'])}元）\n"
        f"车队：{display}\n\n"
        f"✅ {order['phone']} | 完成 {format_amount(order['amount'])} 元"
    )
    await bot.send_message(chat_id=chat_id, text=text)


@dp.callback_query(F.data.startswith("cancel_approve:"))
async def callback_cancel_approve(callback: types.CallbackQuery):
    """同意撤单按钮"""
    if not check_admin(callback.from_user.id):
        await callback.answer("❌ 仅管理员可操作", show_alert=True)
        return
    apply_id = int(callback.data.split(":")[1])
    result = db.approve_cancel_apply(apply_id, callback.from_user.id)
    if not result:
        await callback.answer("❌ 申请不存在或已处理", show_alert=True)
        await callback.message.edit_reply_markup(reply_markup=None)
        return
    await callback.answer("✅ 已同意撤单")
    await callback.message.edit_reply_markup(reply_markup=None)
    await _notify_cancel_result(result["apply"], result["order"])


@dp.callback_query(F.data.startswith("cancel_reject:"))
async def callback_cancel_reject(callback: types.CallbackQuery):
    """拒绝撤单按钮"""
    if not check_admin(callback.from_user.id):
        await callback.answer("❌ 仅管理员可操作", show_alert=True)
        return
    apply_id = int(callback.data.split(":")[1])
    result = db.reject_cancel_apply(apply_id, callback.from_user.id)
    if not result:
        await callback.answer("❌ 申请不存在或已处理", show_alert=True)
        return
    await callback.answer("❌ 已拒绝撤单")
    await callback.message.edit_text(
        callback.message.text + "\n\n❌ 管理员已拒绝此撤单申请。",
        reply_markup=None,
    )
    # 通知申请人
    if result["applicant_id"]:
        await send_notification_to_user(
            result["applicant_id"],
            f"❌ 您的撤单申请 #{result['apply_no']}（手机号 {result['phone']}）已被管理员拒绝。"
        )


@dp.callback_query(F.data.startswith("pay:"))
async def callback_payment(callback: types.CallbackQuery):
    """生成付款链接按钮"""
    user = callback.from_user
    if not check_auth(user.id):
        await callback.answer("❌ 你不是操作员，无法使用本机器人", show_alert=True)
        return

    phone = callback.data.split(":", 1)[1]

    # ⚠️ 付款链接生成逻辑需要根据你的实际业务配置
    # 目前使用配置中的模板，如果没有配置则提示
    payment_url_template = getattr(config, "PAYMENT_URL_TEMPLATE", "")
    if payment_url_template:
        payment_url = payment_url_template.replace("{phone}", phone)
        text = (
            f"💳 付款链接已生成\n"
            f"手机号：<code>{phone}</code>\n"
            f"链接：{payment_url}\n\n"
            f"请在浏览器中打开完成支付。"
        )
    else:
        text = (
            f"💳 付款链接功能尚未配置\n\n"
            f"请在 config.py 中设置 PAYMENT_URL_TEMPLATE，例如：\n"
            f'<code>PAYMENT_URL_TEMPLATE = "https://your-pay.com/pay?phone={"{phone}"}"</code>'
        )

    await callback.answer("已生成付款链接")
    await callback.message.answer(text)


async def _notify_cancel_result(apply: dict, order: dict | None):
    """撤单审核通过通知（群内详细通知 + 私聊申请人简洁通知）"""
    phone = apply["phone"]
    apply_no = apply["apply_no"]
    reviewed_at = apply.get("reviewed_at") or int(time.time())

    # 从订单快照提取金额信息
    if order:
        region = order.get("region", "未知")
        balance = order.get("balance", 0)
        original_amount = order.get("amount", 0)
        completed_amount = order.get("completed_amount", 0)
        remaining = original_amount - completed_amount
    else:
        region = "未知"
        balance = 0
        original_amount = 0
        completed_amount = 0
        remaining = 0

    # 群内详细通知（截图格式）
    group_text = (
        f"✅ 撤单成功\n"
        f"户号：<code>{phone}</code>\n"
        f"地区：{region}\n"
        f"余额：{format_amount(balance)}\n"
        f"原始金额：{format_amount(original_amount)}元\n"
        f"累计已完成：{format_amount(completed_amount)}元\n"
        f"本次撤销剩余：{format_amount(remaining)}元\n"
        f"订单已清空，审核时间：{format_time(reviewed_at)}"
    )
    if apply["chat_id"]:
        await bot.send_message(chat_id=apply["chat_id"], text=group_text)

    # 私聊申请人简洁通知（截图格式）
    private_text = (
        f"✅ 户号 {phone} 的撤单申请已通过，订单已清空。\n"
        f"原始金额：{format_amount(original_amount)}元\n"
        f"累计已完成：{format_amount(completed_amount)}元\n"
        f"本次撤销剩余：{format_amount(remaining)}元"
    )
    if apply["applicant_id"]:
        await send_notification_to_user(apply["applicant_id"], private_text)


# ============ 未授权用户拦截（私聊） ============

@dp.message(F.chat.type == "private")
async def handle_private_fallback(message: types.Message):
    """私聊兜底：未授权用户拦截 + 已授权用户纯手机号查余额"""
    user_id = message.from_user.id

    # 未授权用户
    if not check_auth(user_id):
        if not message.text or not message.text.startswith("/"):
            await message.answer(
                f"❌ 你不是操作员，无法使用本机器人\n\n"
                f"您的 ID：<code>{user_id}</code>\n"
                f"请联系管理员提供您的 ID 进行授权。"
            )
        return

    # 已授权用户：纯手机号 → 余额查询
    if message.text and _is_pure_phone(message.text):
        await _handle_balance_query(message, message.text)
        return

    # 其他非命令文本不回复


# ============ 启动 ============

async def on_startup():
    """启动时初始化"""
    db.init_db()
    logger.info("数据库初始化完成")
    logger.info(f"超级管理员 ID: {config.SUPER_ADMIN_ID}")
    logger.info(f"运行模式: {config.RUN_MODE}")

    if config.RUN_MODE == "webhook" and config.WEBHOOK_HOST:
        webhook_url = f"{config.WEBHOOK_HOST}{config.WEBHOOK_PATH}"
        await bot.set_webhook(url=webhook_url)
        logger.info(f"Webhook 设置成功: {webhook_url}")
    else:
        logger.info("使用长轮询模式 (polling)")


async def main():
    """主入口"""
    await on_startup()

    if config.RUN_MODE == "webhook" and config.WEBHOOK_HOST:
        # Webhook 模式需要 aiohttp
        from aiohttp import web
        from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

        app = web.Application()

        # 健康检查路由（Render/Koyeb 等平台需要）
        async def health_check(request):
            return web.Response(text="OK", status=200)
        app.router.add_get("/", health_check)
        app.router.add_get("/health", health_check)

        # Telegram webhook 路由
        SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=config.WEBHOOK_PATH)
        setup_application(app, dp, bot=bot)

        runner = web.AppRunner(app)
        await runner.setup()
        # 使用 PORT 环境变量（Render 自动分配），没有则用 WEBHOOK_PORT
        site = web.TCPSite(runner, "0.0.0.0", config.PORT)
        await site.start()
        logger.info(f"Webhook 服务启动，监听端口 {config.PORT}")
        logger.info(f"健康检查: http://0.0.0.0:{config.PORT}/")
        logger.info(f"Webhook URL: {config.WEBHOOK_HOST}{config.WEBHOOK_PATH}")

        # 保持运行
        while True:
            await asyncio.sleep(3600)
    else:
        # Polling 模式
        await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("机器人已停止")
