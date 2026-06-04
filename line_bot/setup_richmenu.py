"""
執行一次即可建立 LINE 富選單（買/賣/查詢）
用法：python setup_richmenu.py
"""
import requests, os, io, sys

ACCESS_TOKEN = os.environ.get('LINE_ACCESS_TOKEN',
    'brcndl2dk1OmPOmUl3xm0L0xXVwLg8TeGbbRenHdnOTuiO1RKHxZxE7qs96wT2g2SVVotGgfDDVYTa7YvALkoz3Wy7cysmp/xllK7D+OZisjO0M6SpU9h+37ZQnzR+fnth+DJQxMTEM0wLytDdbvDAdB04t89/1O/w1cDnyilFU=')

HDR = {'Authorization': f'Bearer {ACCESS_TOKEN}', 'Content-Type': 'application/json'}

# ── 1. 建立選單結構 ───────────────────────────────────────
menu = {
    "size": {"width": 2500, "height": 843},
    "selected": True,
    "name": "寶萌選單",
    "chatBarText": "💰買  💸賣  🔍查詢",
    "areas": [
        {"bounds": {"x": 0,    "y": 0, "width": 833,  "height": 843},
         "action": {"type": "message", "text": "買"}},
        {"bounds": {"x": 833,  "y": 0, "width": 834,  "height": 843},
         "action": {"type": "message", "text": "賣"}},
        {"bounds": {"x": 1667, "y": 0, "width": 833,  "height": 843},
         "action": {"type": "message", "text": "查詢"}}
    ]
}

r = requests.post('https://api.line.me/v2/bot/richmenu', headers=HDR, json=menu)
if not r.ok:
    print(f'❌ 建立選單失敗：{r.text}'); sys.exit(1)

menu_id = r.json()['richMenuId']
print(f'✅ 選單建立：{menu_id}')

# ── 2. 產生選單圖片（三色色塊 + 文字）───────────────────
try:
    from PIL import Image, ImageDraw, ImageFont
    W, H = 2500, 843
    img  = Image.new('RGB', (W, H), '#FFFFFF')
    draw = ImageDraw.Draw(img)

    # 三個色塊
    draw.rectangle([0,    0, 832,  H-1], fill='#27AE60')  # 綠 買
    draw.rectangle([833,  0, 1666, H-1], fill='#E74C3C')  # 紅 賣
    draw.rectangle([1667, 0, W-1,  H-1], fill='#2980B9')  # 藍 查詢

    # 分隔線
    draw.line([(833, 0), (833, H)],  fill='white', width=6)
    draw.line([(1667, 0), (1667, H)], fill='white', width=6)

    # 嘗試載入字型
    font = None
    for path in [
        '/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',
        '/System/Library/Fonts/PingFang.ttc',
        'C:/Windows/Fonts/msjhbd.ttc',
        'C:/Windows/Fonts/mingliu.ttc',
    ]:
        try:
            font = ImageFont.truetype(path, 240)
            break
        except Exception:
            pass

    labels = [('買', 416), ('賣', 1250), ('查詢', 2083)]
    for label, x in labels:
        if font:
            draw.text((x, H//2), label, fill='white', font=font, anchor='mm')
        else:
            # 無字型時畫白色圓圈代替
            r2 = 120
            draw.ellipse([x-r2, H//2-r2, x+r2, H//2+r2], outline='white', width=8)

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    img_bytes = buf.getvalue()
    print('✅ 圖片產生成功')

except ImportError:
    # PIL 未安裝，使用純色 PNG（不含文字）
    print('⚠️  Pillow 未安裝，使用純色圖片（無文字）')
    import struct, zlib

    def make_png(w, h, colors):
        """產生 w×h 三色橫條 PNG"""
        section_w = w // 3
        rows = []
        for y in range(h):
            row = b'\x00'
            for x in range(w):
                c = colors[min(x // section_w, 2)]
                row += bytes(c)
            rows.append(row)
        raw = b''.join(rows)
        compressed = zlib.compress(raw)
        def chunk(name, data):
            c = name + data
            return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xFFFFFFFF)
        ihdr = struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)
        png  = b'\x89PNG\r\n\x1a\n'
        png += chunk(b'IHDR', ihdr)
        png += chunk(b'IDAT', compressed)
        png += chunk(b'IEND', b'')
        return png

    img_bytes = make_png(2500, 843, [
        [39, 174, 96],   # 綠
        [231, 76, 60],   # 紅
        [41, 128, 185],  # 藍
    ])

# ── 3. 上傳圖片 ───────────────────────────────────────────
img_hdr = {'Authorization': f'Bearer {ACCESS_TOKEN}', 'Content-Type': 'image/png'}
r2 = requests.post(
    f'https://api-data.line.me/v2/bot/richmenu/{menu_id}/content',
    headers=img_hdr, data=img_bytes)

if not r2.ok:
    print(f'❌ 圖片上傳失敗：{r2.text}'); sys.exit(1)
print('✅ 圖片上傳成功')

# ── 4. 設為預設選單（所有用戶） ───────────────────────────
r3 = requests.post(
    f'https://api.line.me/v2/bot/user/all/richmenu/{menu_id}',
    headers={'Authorization': f'Bearer {ACCESS_TOKEN}'})
print('✅ 已設為預設選單' if r3.ok else f'⚠️  設定預設失敗：{r3.text}')
print(f'\n完成！Rich Menu ID：{menu_id}')
