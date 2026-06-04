"""
資料庫操作模組
使用 Supabase (PostgreSQL) 雲端資料庫
所有讀寫操作集中在這裡
"""

import os
from supabase import create_client, Client
from datetime import datetime, date

# 初始化 Supabase 連線
_url = os.environ.get('SUPABASE_URL', '')
_key = os.environ.get('SUPABASE_KEY', '')
supabase: Client = create_client(_url, _key)


# ─────────────────────────────────────────────
#  客戶查詢
# ─────────────────────────────────────────────

def search_customer(query: str) -> str:
    """依暱稱或電話查詢客戶（模糊搜尋）"""
    try:
        results = supabase.table('customers').select('*').or_(
            f'nickname.ilike.%{query}%,phone.ilike.%{query}%'
        ).limit(5).execute()

        if not results.data:
            return f'🔍 找不到「{query}」的客戶資料\n\n輸入「說明」查看所有指令'

        lines = [f'🔍 找到 {len(results.data)} 筆結果：\n']
        for c in results.data:
            status = '🚫【黑名單】' if c.get('is_blacklist') else '✅ 正常'
            lines.append(f'▸ {c.get("nickname", "（無暱稱）")}  {status}')
            if c.get('id_9188'):
                lines.append(f'  9188編號：{c["id_9188"]}')
            if c.get('phone'):
                lines.append(f'  電話：{c["phone"]}')
            if c.get('bank_account'):
                lines.append(f'  帳號：{c["bank_account"]}')
            if c.get('account_holder'):
                lines.append(f'  戶名：{c["account_holder"]}')
            if c.get('notes'):
                lines.append(f'  備註：{c["notes"]}')
            lines.append('')

        return '\n'.join(lines).rstrip()

    except Exception as e:
        return f'❌ 查詢失敗：{str(e)}'


# ─────────────────────────────────────────────
#  新增客戶
# ─────────────────────────────────────────────

def add_customer(nickname: str, phone: str,
                 account: str = '', holder: str = '',
                 id_9188: str = '') -> str:
    """新增客戶資料"""
    try:
        # 檢查暱稱是否已存在
        existing = supabase.table('customers').select('id, nickname').eq(
            'nickname', nickname
        ).execute()

        if existing.data:
            return (
                f'⚠️ 客戶「{nickname}」已存在\n'
                f'輸入「查客戶 {nickname}」查看詳細資料'
            )

        data = {
            'nickname': nickname,
            'phone': phone,
            'bank_account': account,
            'account_holder': holder,
            'id_9188': int(id_9188) if id_9188.isdigit() else None,
            'is_blacklist': False,
        }

        result = supabase.table('customers').insert(data).execute()

        if result.data:
            msg = f'✅ 新增客戶成功！\n暱稱：{nickname}'
            if phone:
                msg += f'\n電話：{phone}'
            if account:
                msg += f'\n帳號：{account}'
            if holder:
                msg += f'\n戶名：{holder}'
            return msg
        else:
            return '❌ 新增失敗，請稍後再試'

    except Exception as e:
        return f'❌ 新增失敗：{str(e)}'


# ─────────────────────────────────────────────
#  訂單查詢
# ─────────────────────────────────────────────

def search_orders(nickname: str) -> str:
    """查詢某客戶的最近訂單"""
    try:
        results = supabase.table('orders').select('*').ilike(
            'customer_nickname', f'%{nickname}%'
        ).order('date', desc=True).limit(10).execute()

        if not results.data:
            return f'📋 找不到「{nickname}」的訂單記錄'

        lines = [f'📋 {nickname} 的最近訂單（最多10筆）：\n']
        for o in results.data:
            d = o.get('date', '')[:10] if o.get('date') else '日期未知'
            t = o.get('time_note', '')

            if o.get('buy_diamonds') and float(o['buy_diamonds']) > 0:
                action = f'買鑽 {float(o["buy_diamonds"]):,.0f} 個'
            elif o.get('sell_diamonds') and float(o['sell_diamonds']) > 0:
                action = f'賣鑽 {float(o["sell_diamonds"]):,.0f} 個'
            else:
                action = '其他交易'

            lines.append(f'▸ {d} {t}  {action}')

            if o.get('transfer_in') and float(o['transfer_in']) > 0:
                lines.append(f'  轉入：${float(o["transfer_in"]):,.0f}')
            if o.get('transfer_out') and float(o['transfer_out']) > 0:
                lines.append(f'  轉出：${float(o["transfer_out"]):,.0f}')
            if o.get('fee') and float(o['fee']) > 0:
                lines.append(f'  手續費：${float(o["fee"]):,.0f}')
            if o.get('order_no_start'):
                lines.append(f'  訂單編號：{o["order_no_start"]}')
            if o.get('notes'):
                lines.append(f'  備註：{o["notes"]}')
            lines.append('')

        return '\n'.join(lines).rstrip()

    except Exception as e:
        return f'❌ 查詢失敗：{str(e)}'


# ─────────────────────────────────────────────
#  新增訂單
# ─────────────────────────────────────────────

def add_order(nickname: str, order_type: str, amount: float,
              order_no: str = '', notes: str = '') -> str:
    """
    新增訂單
    order_type: 'buy'（買鑽） 或 'sell'（賣鑽）
    """
    try:
        # 確認客戶存在
        customer = supabase.table('customers').select(
            'nickname, is_blacklist, id_9188'
        ).ilike('nickname', f'%{nickname}%').limit(1).execute()

        if not customer.data:
            return (
                f'⚠️ 找不到客戶「{nickname}」\n'
                f'請先輸入「新客戶 {nickname} 電話 帳號 戶名」新增客戶'
            )

        c = customer.data[0]
        actual_nickname = c['nickname']

        if c.get('is_blacklist'):
            return f'🚫 警告！{actual_nickname} 在黑名單中，無法建立訂單'

        today = date.today().isoformat()
        now = datetime.now().strftime('%H:%M')

        data = {
            'date': today,
            'customer_nickname': actual_nickname,
            'buy_diamonds': amount if order_type == 'buy' else 0,
            'sell_diamonds': amount if order_type == 'sell' else 0,
            'order_no_start': order_no if order_no else None,
            'time_note': now,
            'notes': notes if notes else None,
        }

        result = supabase.table('orders').insert(data).execute()

        action = '買鑽' if order_type == 'buy' else '賣鑽'
        if result.data:
            msg = (
                f'✅ 訂單建立成功！\n'
                f'客戶：{actual_nickname}\n'
                f'類型：{action}\n'
                f'數量：{amount:,.0f} 個\n'
                f'時間：{today} {now}'
            )
            if order_no:
                msg += f'\n訂單編號：{order_no}'
            return msg
        else:
            return '❌ 訂單建立失敗，請稍後再試'

    except Exception as e:
        return f'❌ 建立失敗：{str(e)}'


# ─────────────────────────────────────────────
#  黑名單查詢
# ─────────────────────────────────────────────

def check_blacklist(query: str) -> str:
    """查詢某人是否在黑名單"""
    try:
        results = supabase.table('customers').select(
            'nickname, phone, notes, is_blacklist'
        ).or_(
            f'nickname.ilike.%{query}%,phone.ilike.%{query}%'
        ).execute()

        if not results.data:
            return f'🔍 找不到「{query}」的資料'

        blacklisted = [r for r in results.data if r.get('is_blacklist')]
        normal = [r for r in results.data if not r.get('is_blacklist')]

        lines = []

        if blacklisted:
            lines.append('🚫 黑名單警告！\n')
            for c in blacklisted:
                lines.append(f'▸ {c.get("nickname", "")}')
                if c.get('phone'):
                    lines.append(f'  電話：{c["phone"]}')
                if c.get('notes'):
                    lines.append(f'  備註：{c["notes"]}')
            lines.append('')

        if normal:
            lines.append('✅ 以下名單不在黑名單中：')
            for c in normal:
                lines.append(f'▸ {c.get("nickname", "")}')

        return '\n'.join(lines).rstrip()

    except Exception as e:
        return f'❌ 查詢失敗：{str(e)}'
