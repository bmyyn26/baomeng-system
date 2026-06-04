import os, json, hashlib, hmac, base64, re
from datetime import datetime
from flask import Flask, request, abort
import requests

app = Flask(__name__)

# ── 環境變數 ──────────────────────────────────────────────
CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET', '')
ACCESS_TOKEN   = os.environ.get('LINE_ACCESS_TOKEN', '')
SUPABASE_URL   = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY   = os.environ.get('SUPABASE_KEY', '')

LINE_REPLY = 'https://api.line.me/v2/bot/message/reply'

def SUPA_HDR():
    return {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation'
    }

def LINE_HDR():
    return {
        'Authorization': f'Bearer {ACCESS_TOKEN}',
        'Content-Type': 'application/json'
    }

# ── 對話狀態（in-memory） ──────────────────────────────────
user_state = {}

# ── 簽名驗證 ──────────────────────────────────────────────
def verify(body, sig):
    h = hmac.new(CHANNEL_SECRET.encode(), body, hashlib.sha256).digest()
    return base64.b64encode(h).decode() == sig

# ── LINE 訊息工具 ──────────────────────────────────────────
def reply(token, messages):
    r = requests.post(LINE_REPLY, headers=LINE_HDR(),
                      json={'replyToken': token, 'messages': messages})
    print(f'[REPLY] status={r.status_code} body={r.text[:200]}', flush=True)

def txt(text):
    return {'type': 'text', 'text': text}

def qr(text, items):
    return {
        'type': 'text', 'text': text,
        'quickReply': {'items': [
            {'type': 'action',
             'action': {'type': 'message', 'label': lb, 'text': lb}}
            for lb in items
        ]}
    }

# ── Supabase 查詢 ──────────────────────────────────────────
def supa_get(table, params=''):
    r = requests.get(f'{SUPABASE_URL}/rest/v1/{table}?{params}',
                     headers=SUPA_HDR())
    return r.json() if r.ok else []

def supa_post(table, data):
    r = requests.post(f'{SUPABASE_URL}/rest/v1/{table}',
                      headers=SUPA_HDR(), json=data)
    return r.ok

def search_member(q):
    rows = supa_get('members', f'nickname=ilike.*{q}*&select=*&limit=5')
    return rows if isinstance(rows, list) else []

def search_blacklist(q):
    PAGE, page, all_rows = 1000, 0, []
    while True:
        rows = supa_get('blacklist',
            f'nickname=ilike.*{q}*&select=*&limit={PAGE}&offset={page*PAGE}')
        if not isinstance(rows, list) or not rows:
            break
        all_rows += rows
        if len(rows) < PAGE:
            break
        page += 1
    return all_rows

def create_order(order_type, nickname, amount, bank):
    now      = datetime.now()
    label    = '買方' if order_type == 'buy' else '賣方'
    rate     = 1.3 if order_type == 'buy' else 1.44
    diamonds = round(amount * rate)
    prefix   = 'B' if order_type == 'buy' else 'S'
    order_no = f"{prefix}{now.strftime('%y%m%d%H%M')}001"
    ok = supa_post('transactions', {
        'order_no':         order_no,
        'date':             now.strftime('%Y-%m-%d'),
        'label':            label,
        'nickname':         nickname,
        'amount':           amount,
        'diamonds':         diamonds,
        'bank':             bank,
        'transaction_time': now.strftime('%H:%M')
    })
    return ok, diamonds

# ── 訊息處理 ──────────────────────────────────────────────
def handle(user_id, text, reply_token):
    state = user_state.get(user_id, {})
    step  = state.get('step', '')

    # 主選單
    if text == '買':
        user_state[user_id] = {'step': 'buy_bank'}
        reply(reply_token, [qr('請選擇收款銀行', ['合庫', '玉山', '超商', '其他'])])
        return

    if text == '賣':
        user_state[user_id] = {'step': 'sell_bank'}
        reply(reply_token, [qr('請選擇付款銀行', ['合庫', '國泰', '中信'])])
        return

    if text == '查詢':
        user_state[user_id] = {'step': 'query'}
        reply(reply_token, [txt('請輸入暱稱')])
        return

    # 買方：選銀行
    if step == 'buy_bank':
        if text in ['合庫', '玉山', '超商', '其他']:
            user_state[user_id] = {'step': 'buy_input', 'bank': text}
            reply(reply_token, [txt(f'銀行：{text}\n請輸入「暱稱 金額」\n例：企鵝肥肥 1000')])
        else:
            reply(reply_token, [qr('請點選銀行按鈕', ['合庫', '玉山', '超商', '其他'])])
        return

    # 買方：輸入
    if step == 'buy_input':
        m = re.match(r'^(\S+)\s+(\d+)$', text)
        if not m:
            reply(reply_token, [txt('格式錯誤\n請輸入「暱稱 金額」\n例：企鵝肥肥 1000')])
            return
        nickname, amount = m.group(1), int(m.group(2))
        bank = state.get('bank', '合庫')
        if search_blacklist(nickname):
            user_state.pop(user_id, None)
            reply(reply_token, [txt(f'⚠️ 警告\n「{nickname}」在黑名單中！\n請確認後重新操作。')])
            return
        ok, diamonds = create_order('buy', nickname, amount, bank)
        user_state.pop(user_id, None)
        msg = (f'✅ 買方開單成功\n━━━━━━━━━━━━\n'
               f'暱稱：{nickname}\n金額：{amount} 元\n'
               f'紅鑽：{diamonds} 顆\n銀行：{bank}')
        reply(reply_token, [txt(msg if ok else '❌ 開單失敗，請稍後再試')])
        return

    # 賣方：選銀行
    if step == 'sell_bank':
        if text in ['合庫', '國泰', '中信']:
            user_state[user_id] = {'step': 'sell_input', 'bank': text}
            reply(reply_token, [txt(f'銀行：{text}\n請輸入「暱稱 金額」\n例：企鵝肥肥 1000')])
        else:
            reply(reply_token, [qr('請點選銀行按鈕', ['合庫', '國泰', '中信'])])
        return

    # 賣方：輸入
    if step == 'sell_input':
        m = re.match(r'^(\S+)\s+(\d+)$', text)
        if not m:
            reply(reply_token, [txt('格式錯誤\n請輸入「暱稱 金額」\n例：企鵝肥肥 1000')])
            return
        nickname, amount = m.group(1), int(m.group(2))
        bank = state.get('bank', '合庫')
        ok, diamonds = create_order('sell', nickname, amount, bank)
        user_state.pop(user_id, None)
        msg = (f'✅ 賣方開單成功\n━━━━━━━━━━━━\n'
               f'暱稱：{nickname}\n金額：{amount} 元\n'
               f'紅鑽：{diamonds} 顆\n銀行：{bank}')
        reply(reply_token, [txt(msg if ok else '❌ 開單失敗，請稍後再試')])
        return

    # 查詢
    if step == 'query':
        members = search_member(text)
        bl      = search_blacklist(text)
        user_state.pop(user_id, None)
        if not members and not bl:
            reply(reply_token, [txt(f'查無「{text}」相關資料')])
            return
        lines = []
        if bl:
            lines.append('🚫 黑名單')
            seen = set()
            for row in bl[:5]:
                n = row.get('nickname', '')
                if n and n not in seen:
                    lines.append(f'  {n}')
                    seen.add(n)
            if bl[0].get('note'):
                lines.append(f'原因：{bl[0]["note"]}')
        if members:
            grouped = {}
            for row in members:
                k = row.get('id_9188', '無')
                if k not in grouped:
                    grouped[k] = {'nicks': [], 'phone': row.get('phone',''), 'bank': row.get('bank_account','')}
                n = row.get('nickname','')
                if n and n not in grouped[k]['nicks']:
                    grouped[k]['nicks'].append(n)
            for k, v in grouped.items():
                lines.append(f'\n✅ 會員')
                lines.append(f'暱稱：{"、".join(v["nicks"])}')
                if v['phone']: lines.append(f'電話：{v["phone"]}')
                if v['bank']:  lines.append(f'帳號：{v["bank"]}')
        reply(reply_token, [txt('\n'.join(lines))])
        return

    # 未知
    reply(reply_token, [txt('請點選下方選單操作\n💰 買  💸 賣  🔍 查詢')])

# ── Webhook ────────────────────────────────────────────────
@app.route('/webhook', methods=['POST'])
def webhook():
    body = request.get_data()
    sig  = request.headers.get('X-Line-Signature', '')
    if not verify(body, sig):
        abort(400)
    for event in json.loads(body).get('events', []):
        if event.get('type') != 'message':
            continue
        msg = event.get('message', {})
        if msg.get('type') != 'text':
            continue
        handle(event['source']['userId'], msg['text'].strip(), event['replyToken'])
    return 'OK'

@app.route('/')
def health():
    return '寶萌 LINE Bot 運作中'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
