"""
指令處理模組
解析使用者在 LINE 輸入的文字，分派到對應的資料庫操作
"""

from db import search_customer, add_customer, search_orders, add_order, check_blacklist

HELP_TEXT = """📖 寶萌管理系統 指令說明

━━━━━━━━━━━━━━━━
🔍 查客戶（暱稱或電話）
  查客戶 爆爆龍王
  查客戶 0912345678

➕ 新增客戶
  新客戶 暱稱 電話 帳號 戶名
  ★ 帳號戶名可省略

📋 查訂單（最近10筆）
  查訂單 爆爆龍王

📝 新增買鑽訂單
  買鑽 暱稱 數量
  買鑽 爆爆龍王 10000

📝 新增賣鑽訂單
  賣鑽 暱稱 數量
  賣鑽 爆爆龍王 5000

🚫 黑名單查詢
  黑名單 暱稱或電話

━━━━━━━━━━━━━━━━
輸入「說明」可再次查看此說明"""


def handle_command(text: str) -> str:
    """解析指令並回傳結果"""
    parts = text.split()
    if not parts:
        return HELP_TEXT

    cmd = parts[0]

    # ── 說明 ──────────────────────────────────
    if cmd in ('說明', '幫助', 'help', 'Help', '?', '？'):
        return HELP_TEXT

    # ── 查客戶 ────────────────────────────────
    if cmd in ('查客戶', '查會員', '搜尋', '查'):
        if len(parts) < 2:
            return '請輸入要查詢的暱稱或電話\n例：查客戶 爆爆龍王'
        query = parts[1]
        return search_customer(query)

    # ── 新增客戶 ──────────────────────────────
    if cmd in ('新客戶', '新增客戶', '加客戶', '建客戶'):
        if len(parts) < 3:
            return (
                '格式：新客戶 暱稱 電話 [帳號] [戶名]\n'
                '例：新客戶 爆爆龍王 0912345678 007-12345678 王大明\n'
                '（帳號與戶名可省略）'
            )
        nickname = parts[1]
        phone    = parts[2]
        account  = parts[3] if len(parts) > 3 else ''
        holder   = parts[4] if len(parts) > 4 else ''
        return add_customer(nickname, phone, account, holder)

    # ── 查訂單 ────────────────────────────────
    if cmd in ('查訂單', '訂單查詢', '查單'):
        if len(parts) < 2:
            return '請輸入要查詢的暱稱\n例：查訂單 爆爆龍王'
        nickname = parts[1]
        return search_orders(nickname)

    # ── 買鑽（客戶買入紅鑽）──────────────────
    if cmd in ('買鑽', '買入', '進鑽'):
        if len(parts) < 3:
            return '格式：買鑽 暱稱 數量\n例：買鑽 爆爆龍王 10000'
        nickname = parts[1]
        try:
            amount = float(parts[2].replace(',', ''))
        except ValueError:
            return '❌ 數量格式錯誤，請輸入數字\n例：買鑽 爆爆龍王 10000'
        order_no = parts[3] if len(parts) > 3 else ''
        notes    = ' '.join(parts[4:]) if len(parts) > 4 else ''
        return add_order(nickname, 'buy', amount, order_no, notes)

    # ── 賣鑽（客戶賣出紅鑽）──────────────────
    if cmd in ('賣鑽', '賣出', '出鑽'):
        if len(parts) < 3:
            return '格式：賣鑽 暱稱 數量\n例：賣鑽 爆爆龍王 5000'
        nickname = parts[1]
        try:
            amount = float(parts[2].replace(',', ''))
        except ValueError:
            return '❌ 數量格式錯誤，請輸入數字\n例：賣鑽 爆爆龍王 5000'
        order_no = parts[3] if len(parts) > 3 else ''
        notes    = ' '.join(parts[4:]) if len(parts) > 4 else ''
        return add_order(nickname, 'sell', amount, order_no, notes)

    # ── 黑名單 ────────────────────────────────
    if cmd in ('黑名單', '黑單', '查黑名單'):
        if len(parts) < 2:
            return '請輸入要查詢的暱稱或電話\n例：黑名單 爆爆龍王'
        query = parts[1]
        return check_blacklist(query)

    # ── 未知指令 ──────────────────────────────
    return (
        f'❓ 不認識指令「{cmd}」\n\n'
        '輸入「說明」查看所有可用指令'
    )
